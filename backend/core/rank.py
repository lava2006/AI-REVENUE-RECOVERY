"""
Stage 3: AI Playbook Ranking Engine
Scores the fixed 5-action recovery playbook against the payment context and AI diagnosis.
Calculates Expected Value (₹) = (P_success * Amount) - ActionCost.
Sorts actions by Expected Value.
When GEMINI_API_KEY is configured:
  Calls Google Gemini to obtain genuine context-specific probabilities and rationales.
When unconfigured:
  Computes probabilities from calibrated domain heuristics, clearly flagged as is_llm_derived=False.
"""

import logging
from typing import List, Dict, Any, Optional

from backend.models.schemas import (
    PaymentRecord,
    DiagnosisResult,
    FailureCause,
    RecoveryAction,
    StrategyCandidate,
    RankingResult,
    CustomerTier,
)
from backend.core.llm_client import llm_client

logger = logging.getLogger("rebound.rank")


class PlaybookRankingEngine:
    """
    Ranks the 5 fixed recovery playbook actions:
    1. RETRY_NOW
    2. RETRY_LATER
    3. NOTIFY_CUSTOMER
    4. OFFER_ALTERNATE_PAYMENT_METHOD
    5. PROMPT_CARD_UPDATE
    """

    ACTION_COSTS: Dict[RecoveryAction, float] = {
        RecoveryAction.RETRY_NOW: 2.50,
        RecoveryAction.RETRY_LATER: 2.50,
        RecoveryAction.NOTIFY_CUSTOMER: 5.00,
        RecoveryAction.OFFER_ALTERNATE_PAYMENT_METHOD: 8.00,
        RecoveryAction.PROMPT_CARD_UPDATE: 6.00,
    }

    ACTION_DELAYS: Dict[RecoveryAction, int] = {
        RecoveryAction.RETRY_NOW: 0,
        RecoveryAction.RETRY_LATER: 24,
        RecoveryAction.NOTIFY_CUSTOMER: 0,
        RecoveryAction.OFFER_ALTERNATE_PAYMENT_METHOD: 0,
        RecoveryAction.PROMPT_CARD_UPDATE: 0,
    }

    def __init__(self):
        self.llm = llm_client

    def rank(self, payment: PaymentRecord, diagnosis: DiagnosisResult) -> RankingResult:
        amt = payment.amount

        # 1. Try real LLM strategy probability estimation if configured
        if self.llm.is_configured():
            try:
                llm_output = self.llm.estimate_strategy_probabilities(
                    payment_id=payment.payment_id,
                    amount=payment.amount,
                    diagnosed_cause=diagnosis.cause.value,
                    customer_tier=payment.customer_tier.value,
                    tenure_months=payment.tenure_months,
                    past_failed_retries=payment.past_failed_retries,
                    dunning_attempts=payment.dunning_attempts,
                )
                candidates = self._build_llm_candidates(payment, llm_output)
                if candidates:
                    candidates.sort(key=lambda c: c.expected_value, reverse=True)
                    return RankingResult(
                        payment_id=payment.payment_id,
                        candidates=candidates,
                        top_action=candidates[0].action,
                    )
            except Exception as e:
                logger.error(
                    "LLM strategy ranking failed for payment %s: %s. Falling back to heuristic formula.",
                    payment.payment_id,
                    e,
                    exc_info=True,
                )

        # 2. Calibrated heuristic baseline fallback (clearly flagged as is_llm_derived=False)
        return self._heuristic_rank(payment, diagnosis)

    def _build_llm_candidates(self, payment: PaymentRecord, llm_output: Dict[str, Any]) -> List[StrategyCandidate]:
        """Builds candidates using model-estimated probabilities while maintaining strict EV formula."""
        amt = payment.amount
        raw_response = llm_output.get("_raw_model_response")
        strategies_data = llm_output.get("strategies", [])
        strategy_map = {s["action"]: s for s in strategies_data if "action" in s and "probability" in s}

        candidates: List[StrategyCandidate] = []
        for action in RecoveryAction:
            item = strategy_map.get(action.value)
            if item:
                prob = round(float(item["probability"]), 3)
                rationale = item.get("rationale", f"Model evaluated strategy for {payment.customer_tier.value} tier.")
            else:
                prob = 0.05
                rationale = f"Default probability assigned by ranking engine."

            cost = self.ACTION_COSTS[action]
            ev = round((prob * amt) - cost, 2)
            delay = self.ACTION_DELAYS.get(action, 0)
            provider_tag = "Gemini" if self.llm.provider == "gemini" else "AI"

            candidates.append(StrategyCandidate(
                action=action,
                success_probability=prob,
                expected_value=ev,
                estimated_cost=cost,
                rationale=f"[AI {provider_tag}] {rationale}",
                recommended_delay_hours=delay,
                formula_applied=f"EV = ({prob:.2f} * INR {amt:,.2f}) - INR {cost:.2f} = INR {ev:,.2f}",
                is_llm_derived=True,
                raw_model_response=raw_response,
            ))
        return candidates

    def _heuristic_rank(self, payment: PaymentRecord, diagnosis: DiagnosisResult) -> RankingResult:
        """
        Calibrated domain heuristic ranking.
        Flags every candidate with is_llm_derived=False so the UI and audit trail
        never confuse rule baseline calculations with genuine LLM inferences.
        """
        candidates: List[StrategyCandidate] = []
        cause = diagnosis.cause
        amt = payment.amount
        tier_str = payment.customer_tier.value
        tenure = payment.tenure_months
        retries = payment.past_failed_retries
        dunning = payment.dunning_attempts

        tier_multiplier = 1.0
        if payment.customer_tier == CustomerTier.ENTERPRISE:
            tier_multiplier = 1.15
        elif payment.customer_tier == CustomerTier.GROWTH_SMB:
            tier_multiplier = 1.10
        elif payment.customer_tier == CustomerTier.FREE_TRIAL:
            tier_multiplier = 0.70

        retry_penalty = min(0.35, retries * 0.15)
        dunning_penalty = min(0.40, dunning * 0.20)

        # 1. RETRY_NOW
        delay_now = 0
        if cause == FailureCause.BANK_DOWNTIME:
            p_retry_now = max(0.20, 0.88 - retry_penalty)
            reason_now = f"Bank switch downtime is transient. For this {tenure}mo {tier_str} tier account ({retries} prior retries), immediate smart retry has high clearance probability ({p_retry_now*100:.0f}%)."
        elif cause == FailureCause.INSUFFICIENT_FUNDS:
            p_retry_now = max(0.01, 0.08 - retry_penalty)
            reason_now = f"Immediate retry on insufficient funds has minimal success ({p_retry_now*100:.0f}%) for {tier_str} tier account with {retries} prior retries; risks burning decline fees."
        elif cause == FailureCause.CARD_EXPIRED:
            p_retry_now = 0.0
            reason_now = f"Deterministic failure: Expired card token for {tier_str} tier customer ({tenure}mo tenure) cannot clear without card re-issuance."
        elif cause == FailureCause.RISK_BLOCK:
            p_retry_now = 0.0
            reason_now = f"Hard risk block: Retrying flagged suspicious transaction for {tier_str} tier account ({payment.customer_id}) invites immediate card network chargeback fines."
        else:  # ISSUER_DECLINE
            p_retry_now = max(0.02, 0.12 - retry_penalty)
            reason_now = f"Issuer policy decline for {tier_str} tier customer ({tenure}mo tenure) is unlikely to resolve spontaneously on immediate re-attempt ({p_retry_now*100:.0f}% yield)."

        p_retry_now = round(p_retry_now, 3)
        cost_now = self.ACTION_COSTS[RecoveryAction.RETRY_NOW]
        ev_now = round((p_retry_now * amt) - cost_now, 2)
        candidates.append(StrategyCandidate(
            action=RecoveryAction.RETRY_NOW,
            success_probability=p_retry_now,
            expected_value=ev_now,
            estimated_cost=cost_now,
            rationale=f"[Heuristic] {reason_now}",
            recommended_delay_hours=delay_now,
            formula_applied=f"EV = ({p_retry_now:.2f} * INR {amt:,.2f}) - INR {cost_now:.2f} = INR {ev_now:,.2f}",
            is_llm_derived=False,
            raw_model_response=None,
        ))

        # 2. RETRY_LATER
        delay_later = 24
        if cause == FailureCause.INSUFFICIENT_FUNDS:
            p_retry_later = max(0.10, min(0.85, (0.76 * tier_multiplier) - retry_penalty))
            delay_later = 48
            reason_later = f"Scheduling retry in 48h aligns with account replenishment cycles for {tenure}mo {tier_str} tier customer; expected recovery yield {p_retry_later*100:.0f}%."
        elif cause == FailureCause.BANK_DOWNTIME:
            p_retry_later = max(0.10, 0.82 - retry_penalty)
            delay_later = 4
            reason_later = f"Deferred retry after 4-hour CBS maintenance window allows issuer switch recovery ({p_retry_later*100:.0f}% yield for {tier_str} tier account)."
        elif cause == FailureCause.CARD_EXPIRED:
            p_retry_later = 0.0
            reason_later = f"Expired card credential for {tier_str} tier account ({payment.customer_id}) will not heal with time; deferred retry will still fail."
        elif cause == FailureCause.RISK_BLOCK:
            p_retry_later = 0.0
            reason_later = f"Risk block remains active on {tier_str} tier account; scheduled retry without risk clearance is futile."
        else:  # ISSUER_DECLINE
            p_retry_later = max(0.05, 0.20 - retry_penalty)
            delay_later = 24
            reason_later = f"Issuer restriction for {tier_str} tier customer may reset at daily batch cutoff, but probability is low ({p_retry_later*100:.0f}%) without rail change."

        p_retry_later = round(p_retry_later, 3)
        cost_later = self.ACTION_COSTS[RecoveryAction.RETRY_LATER]
        ev_later = round((p_retry_later * amt) - cost_later, 2)
        candidates.append(StrategyCandidate(
            action=RecoveryAction.RETRY_LATER,
            success_probability=p_retry_later,
            expected_value=ev_later,
            estimated_cost=cost_later,
            rationale=f"[Heuristic] {reason_later}",
            recommended_delay_hours=delay_later,
            formula_applied=f"EV = ({p_retry_later:.2f} * INR {amt:,.2f}) - INR {cost_later:.2f} = INR {ev_later:,.2f}",
            is_llm_derived=False,
            raw_model_response=None,
        ))

        # 3. NOTIFY_CUSTOMER
        if cause == FailureCause.INSUFFICIENT_FUNDS:
            p_notify = max(0.10, min(0.80, (0.68 * tier_multiplier) - dunning_penalty))
            reason_notify = f"Dunning alert with 1-click UPI link sent to {tier_str} tier customer ({tenure}mo relationship, {dunning} prior notifications); {p_notify*100:.0f}% response expected."
        elif cause == FailureCause.ISSUER_DECLINE:
            p_notify = max(0.10, min(0.75, (0.62 * tier_multiplier) - dunning_penalty))
            reason_notify = f"Alerts {tier_str} tier customer of bank e-mandate limit or 3DS requirement so they can approve in netbanking ({p_notify*100:.0f}% yield)."
        elif cause == FailureCause.CARD_EXPIRED:
            p_notify = max(0.10, min(0.65, (0.50 * tier_multiplier) - dunning_penalty))
            reason_notify = f"Notifies {tier_str} tier customer that subscription is interrupted due to expired card on record ({p_notify*100:.0f}% conversion)."
        elif cause == FailureCause.BANK_DOWNTIME:
            p_notify = 0.25
            reason_notify = f"Customer notification unnecessary for short bank glitch on {tier_str} tier account, but provides manual backup payment link."
        else:  # RISK_BLOCK
            p_notify = 0.05
            reason_notify = f"Low probability: Flagged risk {tier_str} tier accounts rarely respond favorably to automated dunning."

        p_notify = round(p_notify, 3)
        cost_notify = self.ACTION_COSTS[RecoveryAction.NOTIFY_CUSTOMER]
        ev_notify = round((p_notify * amt) - cost_notify, 2)
        candidates.append(StrategyCandidate(
            action=RecoveryAction.NOTIFY_CUSTOMER,
            success_probability=p_notify,
            expected_value=ev_notify,
            estimated_cost=cost_notify,
            rationale=f"[Heuristic] {reason_notify}",
            recommended_delay_hours=0,
            formula_applied=f"EV = ({p_notify:.2f} * INR {amt:,.2f}) - INR {cost_notify:.2f} = INR {ev_notify:,.2f}",
            is_llm_derived=False,
            raw_model_response=None,
        ))

        # 4. OFFER_ALTERNATE_PAYMENT_METHOD
        if cause == FailureCause.ISSUER_DECLINE:
            p_alternate = max(0.15, min(0.92, (0.84 * tier_multiplier) - dunning_penalty))
            reason_alt = f"Optimal for bank declines on {tier_str} tier accounts ({tenure}mo tenure): Bypasses restrictive card mandate via UPI AutoPay or NetBanking e-NACH link ({p_alternate*100:.0f}% clearance)."
        elif cause == FailureCause.INSUFFICIENT_FUNDS:
            p_alternate = max(0.10, min(0.70, (0.55 * tier_multiplier) - dunning_penalty))
            reason_alt = f"Allows {tier_str} tier customer to charge a secondary corporate card or primary salary account ({p_alternate*100:.0f}% probability)."
        elif cause == FailureCause.CARD_EXPIRED:
            p_alternate = max(0.10, min(0.75, (0.60 * tier_multiplier) - dunning_penalty))
            reason_alt = f"Offers immediate switch for {tier_str} tier customer to active UPI AutoPay mandate rather than waiting for new physical card delivery."
        elif cause == FailureCause.BANK_DOWNTIME:
            p_alternate = 0.30
            reason_alt = f"Customer can pay from an alternate bank, though introduces unnecessary friction during brief bank downtime on {tier_str} tier account."
        else:  # RISK_BLOCK
            p_alternate = 0.02
            reason_alt = f"Prohibited: Risk-flagged {tier_str} tier entities may not rotate payment rails without manual compliance KYC review."

        p_alternate = round(p_alternate, 3)
        cost_alt = self.ACTION_COSTS[RecoveryAction.OFFER_ALTERNATE_PAYMENT_METHOD]
        ev_alt = round((p_alternate * amt) - cost_alt, 2)
        candidates.append(StrategyCandidate(
            action=RecoveryAction.OFFER_ALTERNATE_PAYMENT_METHOD,
            success_probability=p_alternate,
            expected_value=ev_alt,
            estimated_cost=cost_alt,
            rationale=f"[Heuristic] {reason_alt}",
            recommended_delay_hours=0,
            formula_applied=f"EV = ({p_alternate:.2f} * INR {amt:,.2f}) - INR {cost_alt:.2f} = INR {ev_alt:,.2f}",
            is_llm_derived=False,
            raw_model_response=None,
        ))

        # 5. PROMPT_CARD_UPDATE
        if cause == FailureCause.CARD_EXPIRED:
            p_card_update = max(0.15, min(0.92, (0.86 * tier_multiplier) - dunning_penalty))
            reason_card = f"Targeted solution for {tenure}mo {tier_str} tier subscriber: Delivers secure RBI tokenization flow for renewed card details ({p_card_update*100:.0f}% expected renewal)."
        elif cause == FailureCause.ISSUER_DECLINE:
            p_card_update = max(0.10, min(0.55, (0.45 * tier_multiplier) - dunning_penalty))
            reason_card = f"Re-entering card details for {tier_str} tier account re-triggers mandate authorization if customer updated limits ({p_card_update*100:.0f}% yield)."
        elif cause == FailureCause.INSUFFICIENT_FUNDS:
            p_card_update = 0.15
            reason_card = f"Prompting card update is ineffective for {tier_str} tier customer when underlying problem is bank account balance."
        elif cause == FailureCause.BANK_DOWNTIME:
            p_card_update = 0.05
            reason_card = f"Unwarranted for {tier_str} tier account: Existing card credentials are valid; bank downtime is temporary."
        else:  # RISK_BLOCK
            p_card_update = 0.0
            reason_card = f"Blocked: Cannot prompt card update on high-risk suspicious {tier_str} tier accounts."

        p_card_update = round(p_card_update, 3)
        cost_card = self.ACTION_COSTS[RecoveryAction.PROMPT_CARD_UPDATE]
        ev_card = round((p_card_update * amt) - cost_card, 2)
        candidates.append(StrategyCandidate(
            action=RecoveryAction.PROMPT_CARD_UPDATE,
            success_probability=p_card_update,
            expected_value=ev_card,
            estimated_cost=cost_card,
            rationale=f"[Heuristic] {reason_card}",
            recommended_delay_hours=0,
            formula_applied=f"EV = ({p_card_update:.2f} * INR {amt:,.2f}) - INR {cost_card:.2f} = INR {ev_card:,.2f}",
            is_llm_derived=False,
            raw_model_response=None,
        ))

        # Sort candidates strictly descending by Expected Value (₹)
        candidates.sort(key=lambda c: c.expected_value, reverse=True)
        top_action = candidates[0].action

        return RankingResult(
            payment_id=payment.payment_id,
            candidates=candidates,
            top_action=top_action,
        )


ranking_engine = PlaybookRankingEngine()

