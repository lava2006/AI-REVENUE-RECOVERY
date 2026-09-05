"""
Stages 1–8: Rebound Recovery Pipeline Coordinator
Orchestrates Detect → Diagnose → Rank → Gate (Sentinel) → Execute → Observe & Fallback → Audit → Report.
Strictly separates AI strategy selection from deterministic policy gating.
"""

import time
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional

from backend.models.schemas import (
    PaymentRecord,
    DiagnosisResult,
    RankingResult,
    StrategyCandidate,
    PolicyRequest,
    SentinelDecision,
    ExecutionOutcome,
    FallbackStep,
    CounterfactualMetric,
    RecoveryDecisionCardData,
    AuditLogEntry,
    CalibrationBucket,
    RecoveryAction,
    FailureCause,
)
from backend.core.diagnose import diagnosis_engine
from backend.core.rank import ranking_engine
from backend.core.sentinel import the_sentinel, SentinelPolicyCodes
from backend.core.executor import razorpay_executor
from backend.core.db import db_manager


def compute_calibration_buckets(cards: List[RecoveryDecisionCardData]) -> List[CalibrationBucket]:
    """
    Computes bucketed calibration table (predicted vs actual recovery rate)
    for model audit and pre-submission validation.
    """
    buckets_def = [
        ("0-20%", 0.0, 0.20),
        ("20-40%", 0.20, 0.40),
        ("40-60%", 0.40, 0.60),
        ("60-80%", 0.60, 0.80),
        ("80-100%", 0.80, 1.00),
    ]
    results = []
    for label, b_min, b_max in buckets_def:
        count = 0
        actual_rec = 0
        for card in cards:
            top_cand = card.ranked_candidates[0] if card.ranked_candidates else None
            if not top_cand:
                continue
            prob = top_cand.success_probability
            if (b_min <= prob < b_max) or (b_max == 1.0 and prob == 1.0):
                count += 1
                if card.recovered:
                    actual_rec += 1
        rate = round((actual_rec / count * 100.0), 1) if count > 0 else 0.0
        results.append(CalibrationBucket(
            bucket_range=label,
            predicted_min=b_min,
            predicted_max=b_max,
            predictions_count=count,
            actual_recovered_count=actual_rec,
            actual_recovery_rate=rate,
        ))
    return results


class ReboundPipeline:
    """
    Main orchestrator for Rebound.
    Executes the 8-stage revenue recovery process with compliant fallback and full auditability.
    """

    def __init__(self):
        self.sentinel = the_sentinel
        self.diagnostician = diagnosis_engine
        self.ranker = ranking_engine
        self.executor = razorpay_executor

    def process_payment(self, payment: PaymentRecord) -> Tuple[RecoveryDecisionCardData, List[AuditLogEntry]]:
        """
        Runs a single failed subscription payment through the complete 8-stage pipeline.
        Returns the Recovery Decision Card data and its chronological audit entries.
        """
        start_time = time.time()
        audit_trail: List[AuditLogEntry] = []

        def log_audit(stage: str, action: str, status: str, reasoning: str = "", decision: Optional[str] = None, details: Dict[str, Any] = None):
            entry = AuditLogEntry(
                entry_id=f"audit_{uuid.uuid4().hex[:10]}",
                payment_id=payment.payment_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                stage=stage,
                action=action,
                status=status,
                reasoning=reasoning,
                decision=decision,
                details=details or {},
            )
            audit_trail.append(entry)
            db_manager.save_audit_log({
                "event_id": entry.entry_id,
                "payment_id": entry.payment_id,
                "stage": entry.stage,
                "action": entry.action,
                "status": entry.status,
                "human_readable_reasoning": entry.reasoning,
                "decision": entry.decision,
                "details": entry.details,
                "timestamp": entry.timestamp,
            })

        # Persist Ingested Payment Record
        db_manager.save_payment({
            "payment_id": payment.payment_id,
            "subscription_id": payment.subscription_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "timestamp": payment.timestamp,
            "decline_code": payment.decline_code,
            "raw_signal": payment.raw_signal,
            "customer_id": payment.customer_id,
            "customer_name": payment.customer_name,
            "customer_tier": payment.customer_tier.value,
            "tenure_months": payment.tenure_months,
            "past_failed_retries": payment.past_failed_retries,
            "dunning_attempts": payment.dunning_attempts,
            "last_attempt_at": payment.last_attempt_at,
            "preferred_payment_method": payment.preferred_payment_method,
            "true_cause": payment.true_cause.value if hasattr(payment.true_cause, "value") else str(payment.true_cause),
            "true_recoverable": payment.true_recoverable,
        })

        # ---------------- STAGE 1: DETECT ----------------
        detect_reason = f"Ingested {payment.currency} {payment.amount:,.2f} failure from {payment.customer_id} ({payment.customer_tier.value} tier). Decline code: {payment.decline_code}."
        log_audit("DETECT", "INGEST_FAILURE_SIGNAL", "INFO", reasoning=detect_reason, decision="INGESTED", details={
            "amount": payment.amount,
            "currency": payment.currency,
            "decline_code": payment.decline_code,
            "raw_signal": payment.raw_signal,
            "customer_tier": payment.customer_tier.value,
            "tenure_months": payment.tenure_months,
            "past_failed_retries": payment.past_failed_retries,
            "dunning_attempts": payment.dunning_attempts,
        })

        # ---------------- STAGE 2: DIAGNOSE [AI] ----------------
        diagnosis: DiagnosisResult = self.diagnostician.diagnose(payment)
        db_manager.save_diagnosis({
            "payment_id": payment.payment_id,
            "diagnosed_cause": diagnosis.cause.value,
            "confidence": diagnosis.confidence,
            "reasoning": diagnosis.reasoning,
            "key_signals": diagnosis.key_signals,
            "provider": getattr(diagnosis, "provider", "gemini"),
            "model_name": getattr(diagnosis, "model_name", "gemini-3.5-flash-lite"),
            "is_llm_derived": getattr(diagnosis, "is_llm_derived", False),
            "raw_model_response": getattr(diagnosis, "raw_model_response", None),
        })

        diag_reason = f"Diagnosed {diagnosis.cause.value} with {diagnosis.confidence*100:.0f}% confidence based on '{payment.raw_signal}'."
        log_audit("DIAGNOSE", "AI_ROOT_CAUSE_CLASSIFICATION", "SUCCESS", reasoning=diag_reason, decision=diagnosis.cause.value, details={
            "diagnosed_cause": diagnosis.cause.value,
            "confidence_score": diagnosis.confidence,
            "reasoning": diagnosis.reasoning,
            "key_signals": diagnosis.key_signals,
            "is_llm_derived": diagnosis.is_llm_derived,
            "provider": diagnosis.provider,
        })

        # ---------------- STAGE 3: RANK [AI] ----------------
        ranking: RankingResult = self.ranker.rank(payment, diagnosis)
        for rank_idx, cand in enumerate(ranking.candidates, start=1):
            db_manager.save_strategy({
                "payment_id": payment.payment_id,
                "strategy_name": cand.action.value,
                "rank": rank_idx,
                "probability": cand.success_probability,
                "expected_value": cand.expected_value,
                "cost": cand.estimated_cost,
                "reasoning_text": cand.rationale,
                "recommended_delay_hours": cand.recommended_delay_hours,
                "formula_applied": cand.formula_applied,
            })

        rank_reason = f"Ranked 5 playbook strategies. Top candidate is {ranking.top_action.value} with EV ₹{ranking.candidates[0].expected_value:,.2f}."
        log_audit("RANK", "AI_PLAYBOOK_EV_SCORING", "SUCCESS", reasoning=rank_reason, decision=ranking.top_action.value, details={
            "top_recommended_action": ranking.top_action.value,
            "candidates_scored": [
                {
                    "action": c.action.value,
                    "expected_value": c.expected_value,
                    "success_probability": c.success_probability,
                    "cost": c.estimated_cost,
                    "rationale": c.rationale,
                    "is_llm_derived": c.is_llm_derived,
                }
                for c in ranking.candidates
            ],
        })

        # ---------------- STAGES 4–6: GATE [Sentinel] -> EXECUTE -> OBSERVE & FALLBACK ----------------
        fallback_steps: List[FallbackStep] = []
        final_outcome: Optional[ExecutionOutcome] = None
        executed_action: Optional[RecoveryAction] = None
        current_retries = payment.past_failed_retries
        current_dunning = payment.dunning_attempts
        last_attempt = payment.last_attempt_at

        # Risk score synthesis: High-risk diagnosis passes elevated risk score to Sentinel
        risk_score = 0.94 if diagnosis.cause == FailureCause.RISK_BLOCK else 0.10

        step_counter = 1
        for candidate in ranking.candidates:
            # Prepare generic action-agnostic PolicyRequest for the Sentinel
            # Uses active dynamic SentinelConfig values as defaults
            policy_req = PolicyRequest(
                subject_id=payment.payment_id,
                subject_type="payment_recovery",
                action_type=candidate.action.value,
                amount=payment.amount,
                current_attempt_count=current_retries,
                last_attempt_timestamp=last_attempt,
                escalation_count=current_dunning,
                expected_value=candidate.expected_value,
                confidence=diagnosis.confidence,
                granted_permissions=["payment.recovery.execute"],
                advisory_note=f"Advisory: {candidate.rationale[:60]}...",
                context={
                    "risk_score": risk_score,
                    "max_retries": self.sentinel.config.max_retries,
                    "max_escalations": self.sentinel.config.max_escalations,
                    "required_cooldown_hours": self.sentinel.config.cooldown_hours,
                    "min_ev_threshold": self.sentinel.config.min_ev,
                    "max_amount_bound": self.sentinel.config.max_recovery_amount,
                    "min_amount_bound": self.sentinel.config.min_amount,
                    "max_permissible_risk": self.sentinel.config.max_permissible_risk,
                },
            )

            # Pure deterministic gate: No AI inside this call
            sentinel_decision: SentinelDecision = self.sentinel.evaluate(policy_req)

            db_manager.save_gate_decision({
                "payment_id": payment.payment_id,
                "strategy_chosen": candidate.action.value,
                "approved": sentinel_decision.approved,
                "policy_code": sentinel_decision.policy_code,
                "reason": sentinel_decision.reason,
                "confidence": sentinel_decision.confidence,
                "expected_value": sentinel_decision.expected_value,
                "constraints_evaluated": sentinel_decision.constraints_evaluated,
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
            })

            gate_decision_str = "APPROVED" if sentinel_decision.approved else f"BLOCKED ({sentinel_decision.policy_code})"
            log_audit("SENTINEL_GATE", f"EVALUATE_{candidate.action.value}", "SUCCESS" if sentinel_decision.approved else "REJECTED",
                      reasoning=sentinel_decision.reason, decision=gate_decision_str, details={
                "candidate_action": candidate.action.value,
                "approved": sentinel_decision.approved,
                "policy_code": sentinel_decision.policy_code,
                "reason": sentinel_decision.reason,
                "constraints_evaluated": sentinel_decision.constraints_evaluated,
            })

            # Check if Sentinel rejected this candidate
            if not sentinel_decision.approved:
                fallback_step = FallbackStep(
                    step_number=step_counter,
                    candidate_action=candidate.action,
                    expected_value=candidate.expected_value,
                    sentinel_approved=False,
                    sentinel_decision=sentinel_decision,
                    execution_attempted=False,
                    notes=f"Blocked by Sentinel: {sentinel_decision.policy_code}. Falling back to next-ranked candidate.",
                )
                fallback_steps.append(fallback_step)
                log_audit("FALLBACK", f"SKIP_TO_NEXT_AFTER_{candidate.action.value}", "INFO",
                          reasoning=f"Sentinel blocked {candidate.action.value}. Stepping down to next viable candidate.",
                          decision="FALLBACK_NEXT", details={
                    "reason": f"Sentinel blocked {candidate.action.value} ({sentinel_decision.policy_code}). Stepping down playbook hierarchy.",
                })
                step_counter += 1
                continue

            # Sentinel Approved: Proceed to Stage 5 Execution
            executed_action = candidate.action
            outcome = self.executor.execute_action(payment, candidate.action)
            final_outcome = outcome

            db_manager.save_outcome({
                "payment_id": payment.payment_id,
                "action": candidate.action.value,
                "final_status": "SUCCESS" if outcome.success else "FAILED",
                "recovered_amount": outcome.recovered_amount,
                "transaction_id": outcome.transaction_id,
                "gateway_code": outcome.gateway_code,
                "gateway_message": outcome.gateway_message,
                "execution_backend": outcome.execution_backend,
                "executed_at": outcome.timestamp,
            })

            # Stage 6: Observe
            exec_reason = f"Gateway executed {candidate.action.value}: {'Cleared ₹' + str(outcome.recovered_amount) if outcome.success else outcome.gateway_message}"
            log_audit("EXECUTE", f"GATEWAY_EXECUTE_{candidate.action.value}", "SUCCESS" if outcome.success else "FAILED",
                      reasoning=exec_reason, decision="CLEARED" if outcome.success else "GATEWAY_DECLINE", details={
                "action": candidate.action.value,
                "success": outcome.success,
                "transaction_id": outcome.transaction_id,
                "gateway_code": outcome.gateway_code,
                "gateway_message": outcome.gateway_message,
                "execution_backend": outcome.execution_backend,
                "razorpay_order_id": outcome.razorpay_order_id,
                "razorpay_payment_link": outcome.razorpay_payment_link,
                "signature_verified": outcome.signature_verified,
                "test_instrument": outcome.test_instrument,
            })

            if outcome.success:
                fallback_step = FallbackStep(
                    step_number=step_counter,
                    candidate_action=candidate.action,
                    expected_value=candidate.expected_value,
                    sentinel_approved=True,
                    sentinel_decision=sentinel_decision,
                    execution_attempted=True,
                    execution_success=True,
                    execution_details=outcome,
                    notes=f"Successfully recovered ₹{outcome.recovered_amount:,.2f} via {candidate.action.value}.",
                )
                fallback_steps.append(fallback_step)
                log_audit("OBSERVE", "RECOVERY_CONFIRMED", "SUCCESS",
                          reasoning=f"Revenue recovery confirmed on {candidate.action.value}. Account standing preserved.",
                          decision="COMPLETED", details={
                    "recovered_amount": outcome.recovered_amount,
                    "action": candidate.action.value,
                    "transaction_id": outcome.transaction_id,
                })
                break  # Successful recovery; stop pipeline
            else:
                # Gateway execution failed: Increment attempts and fall back
                current_retries += 1
                if "NOTIFY" in candidate.action.value:
                    current_dunning += 1
                last_attempt = datetime.now(timezone.utc).isoformat()

                fallback_step = FallbackStep(
                    step_number=step_counter,
                    candidate_action=candidate.action,
                    expected_value=candidate.expected_value,
                    sentinel_approved=True,
                    sentinel_decision=sentinel_decision,
                    execution_attempted=True,
                    execution_success=False,
                    execution_details=outcome,
                    notes=f"Gateway execution failed ({outcome.gateway_code}). Falling back to next available strategy.",
                )
                fallback_steps.append(fallback_step)
                log_audit("FALLBACK", f"FALLBACK_AFTER_FAILED_{candidate.action.value}", "INFO",
                          reasoning=f"Gateway declined {candidate.action.value} ({outcome.gateway_message}). Fallback triggered.",
                          decision="FALLBACK_NEXT", details={
                    "gateway_error": outcome.gateway_message,
                    "next_step": "Testing next viable candidate in playbook hierarchy.",
                })
                step_counter += 1

        # If loop finished without successful recovery:
        if not final_outcome or not final_outcome.success:
            log_audit("STOP", "PIPELINE_HALTED", "INFO",
                      reasoning="All viable strategies exhausted or blocked by Sentinel governance. Halting to protect merchant & customer.",
                      decision="HALTED", details={
                "summary": "All viable strategies exhausted or blocked by Sentinel governance. Halting to protect merchant & customer.",
            })

        # ---------------- STAGE 7 & 8: AUDIT TRAIL & REPORT / COUNTERFACTUAL EV ----------------
        is_recovered = final_outcome.success if final_outcome else False
        recovered_amount = final_outcome.recovered_amount if is_recovered else 0.0
        
        # Calculate total execution costs incurred across attempted steps
        total_costs = sum(
            ranking_engine.ACTION_COSTS.get(step.candidate_action, 2.50)
            for step in fallback_steps
            if step.execution_attempted
        )
        net_revenue_impact = recovered_amount - total_costs if is_recovered else -total_costs

        # Synthesize honest counterfactual metrics
        counterfactuals: List[CounterfactualMetric] = []
        for candidate in ranking.candidates:
            if candidate.action == executed_action:
                status = "executed"
            elif any(s.candidate_action == candidate.action and not s.sentinel_approved for s in fallback_steps):
                status = "gated_by_sentinel"
            elif any(s.candidate_action == candidate.action and s.execution_attempted and not s.execution_success for s in fallback_steps):
                status = "rejected_by_gateway"
            else:
                status = "unreached_fallback"

            counterfactuals.append(CounterfactualMetric(
                action=candidate.action,
                expected_value=candidate.expected_value,
                success_probability=candidate.success_probability,
                status=status,
                rationale=candidate.rationale,
            ))

        duration_ms = round((time.time() - start_time) * 1000.0, 2)

        # Last Sentinel decision evaluated (or top action decision)
        last_sentinel_decision = fallback_steps[-1].sentinel_decision if fallback_steps else SentinelDecision(
            approved=False,
            policy_code=SentinelPolicyCodes.EV_NEGATIVE,
            reason="No strategies cleared threshold.",
            confidence=diagnosis.confidence,
            expected_value=0.0,
            constraints_evaluated={},
        )

        # Borderline flag for Review Queue triage
        is_borderline = (
            payment.past_failed_retries >= 2
            or payment.amount >= 20000.0
            or diagnosis.confidence < 0.88
            or diagnosis.cause in [FailureCause.ISSUER_DECLINE, FailureCause.RISK_BLOCK]
            or ranking.top_action in [RecoveryAction.OFFER_ALTERNATE_PAYMENT_METHOD, RecoveryAction.PROMPT_CARD_UPDATE]
        )

        card_data = RecoveryDecisionCardData(
            payment=payment,
            diagnosis=diagnosis,
            ranked_candidates=ranking.candidates,
            final_sentinel_decision=last_sentinel_decision,
            fallback_steps=fallback_steps,
            final_outcome=final_outcome,
            counterfactual_paths=counterfactuals,
            recovered=is_recovered,
            net_revenue_impact=round(net_revenue_impact, 2),
            pipeline_duration_ms=duration_ms,
            advisory_note=f"Advisory note for audit: Top candidate {ranking.top_action.value} rated EV ₹{ranking.candidates[0].expected_value:,.2f}",
            is_borderline=is_borderline,
        )

        return card_data, audit_trail


# Global pipeline coordinator
rebound_pipeline = ReboundPipeline()
