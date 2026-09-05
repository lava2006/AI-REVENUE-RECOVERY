"""
The Sentinel — Deterministic Governance & Policy Gate
Standalone, pure-rules policy engine. ZERO LLM dependencies.
This module is the sole gate allowed to touch money movement.
Designed to be action-agnostic: gates both recovery actions and autonomous buyer agents.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import dateutil.parser
import logging

logger = logging.getLogger("rebound.sentinel")

from backend.models.schemas import PolicyRequest, SentinelDecision, MerchantPolicyConfig


class SentinelPolicyCodes:
    OK = "SENTINEL_OK"
    MAX_RETRIES_EXCEEDED = "POLICY_MAX_RETRIES_EXCEEDED"
    AMOUNT_EXCEEDS_LIMIT = "POLICY_AMOUNT_EXCEEDS_LIMIT"
    AMOUNT_BELOW_MINIMUM = "POLICY_AMOUNT_BELOW_MINIMUM"
    COOLDOWN_ACTIVE = "POLICY_COOLDOWN_ACTIVE"
    ESCALATION_THROTTLED = "POLICY_ESCALATION_THROTTLED"
    EV_NEGATIVE = "POLICY_EV_NEGATIVE"
    PERMISSION_DENIED = "POLICY_PERMISSION_DENIED"
    RISK_THRESHOLD_EXCEEDED = "POLICY_RISK_THRESHOLD_EXCEEDED"
    BUDGET_EXCEEDED = "POLICY_BUDGET_EXCEEDED"
    CATALOG_ITEM_NOT_FOUND = "POLICY_CATALOG_ITEM_NOT_FOUND"
    OUT_OF_STOCK = "POLICY_OUT_OF_STOCK"
    PRICE_MISMATCH = "POLICY_PRICE_MISMATCH"


class Sentinel:
    """
    The Sentinel rules engine.
    Purely deterministic: No LLM calls, no heuristic drift, no hallucinations.
    Reusable across any action-authorizing context.
    """

    def __init__(self, config: Optional[MerchantPolicyConfig] = None):
        self.config: MerchantPolicyConfig = config or MerchantPolicyConfig()

    def update_config(self, new_config: MerchantPolicyConfig):
        """Dynamic runtime update of merchant policy thresholds."""
        self.config = new_config

    def evaluate(self, request: PolicyRequest) -> SentinelDecision:
        """
        Evaluate a generic policy request against strict deterministic rules.
        Returns a structured SentinelDecision with pass/fail, policy code, and diagnostic reason.

        NOTE ON ADVISORY NOTE:
        The PolicyRequest schema may contain an 'advisory_note' generated upstream by an AI or user.
        The Sentinel structurally ignores this field entirely. It cannot influence any rule check.
        """
        constraints_log: Dict[str, str] = {}

        # 1. Expected Value Cutoff
        # Money/friction movement is strictly prohibited if expected value is non-positive
        min_ev = request.context.get("min_ev_threshold", self.config.min_ev)
        if request.expected_value < min_ev:
            constraints_log["expected_value_check"] = f"FAIL (EV ₹{request.expected_value:.2f} < threshold ₹{min_ev:.2f})"
            return SentinelDecision(
                approved=False,
                policy_code=SentinelPolicyCodes.EV_NEGATIVE,
                reason=f"Rejected: Action expected value (₹{request.expected_value:.2f}) is below minimum threshold (₹{min_ev:.2f}).",
                confidence=request.confidence,
                expected_value=request.expected_value,
                constraints_evaluated=constraints_log,
            )
        constraints_log["expected_value_check"] = f"PASS (₹{request.expected_value:.2f})"

        # 2. Amount Bounds Check
        max_allowed_amount = request.context.get("max_amount_bound", self.config.max_recovery_amount)
        min_allowed_amount = request.context.get("min_amount_bound", self.config.min_amount)

        if request.amount < min_allowed_amount:
            constraints_log["amount_check"] = f"FAIL (Amount ₹{request.amount} < ₹{min_allowed_amount})"
            return SentinelDecision(
                approved=False,
                policy_code=SentinelPolicyCodes.AMOUNT_BELOW_MINIMUM,
                reason=f"Rejected: Requested amount ₹{request.amount:.2f} is below minimum permissible bound ₹{min_allowed_amount:.2f}.",
                confidence=request.confidence,
                expected_value=request.expected_value,
                constraints_evaluated=constraints_log,
            )

        if request.amount > max_allowed_amount:
            constraints_log["amount_check"] = f"FAIL (Amount ₹{request.amount} > ₹{max_allowed_amount})"
            return SentinelDecision(
                approved=False,
                policy_code=SentinelPolicyCodes.AMOUNT_EXCEEDS_LIMIT,
                reason=f"Rejected: Requested amount ₹{request.amount:.2f} exceeds allowable ceiling ₹{max_allowed_amount:.2f}.",
                confidence=request.confidence,
                expected_value=request.expected_value,
                constraints_evaluated=constraints_log,
            )
        constraints_log["amount_check"] = f"PASS (₹{request.amount:.2f})"

        # 3. Monthly/Cumulative Budget Check (For Autonomous Buyer Agent or Merchant caps)
        monthly_budget = request.context.get("monthly_budget_inr")
        current_spend = request.context.get("current_month_spend_inr")
        if monthly_budget is not None and current_spend is not None:
            if (current_spend + request.amount) > monthly_budget:
                constraints_log["budget_check"] = f"FAIL (Spend ₹{current_spend + request.amount:.2f} > Budget ₹{monthly_budget:.2f})"
                return SentinelDecision(
                    approved=False,
                    policy_code=SentinelPolicyCodes.BUDGET_EXCEEDED,
                    reason=f"Rejected: Purchase amount ₹{request.amount:.2f} would exceed monthly budget cap of ₹{monthly_budget:.2f} (current spend: ₹{current_spend:.2f}).",
                    confidence=request.confidence,
                    expected_value=request.expected_value,
                    constraints_evaluated=constraints_log,
                )
            constraints_log["budget_check"] = "PASS"

        # 4. Catalog Price, SKU & Stock Validation (for Merchant Catalog / Buyer Agent)
        catalog_item = request.context.get("catalog_item")
        if catalog_item:
            if not catalog_item.get("in_stock", True):
                constraints_log["stock_check"] = f"FAIL (SKU '{catalog_item.get('sku')}' is OUT_OF_STOCK)"
                return SentinelDecision(
                    approved=False,
                    policy_code=SentinelPolicyCodes.OUT_OF_STOCK,
                    reason=f"Rejected: Catalog item '{catalog_item.get('name', catalog_item.get('sku'))}' is currently out of stock.",
                    confidence=request.confidence,
                    expected_value=request.expected_value,
                    constraints_evaluated=constraints_log,
                )
            catalog_price = catalog_item.get("price")
            if catalog_price is not None and abs(request.amount - catalog_price) > 0.01:
                constraints_log["price_check"] = f"FAIL (Requested ₹{request.amount:.2f} != Catalog price ₹{catalog_price:.2f})"
                return SentinelDecision(
                    approved=False,
                    policy_code=SentinelPolicyCodes.PRICE_MISMATCH,
                    reason=f"Rejected: Requested amount ₹{request.amount:.2f} does not match catalog price ₹{catalog_price:.2f}.",
                    confidence=request.confidence,
                    expected_value=request.expected_value,
                    constraints_evaluated=constraints_log,
                )
            constraints_log["catalog_check"] = "PASS"

        # 5. Scope & Permission Check (For Buyer Agent & Elevated Operations)
        required_scope = request.context.get("requires_scope")
        if required_scope:
            if required_scope not in request.granted_permissions:
                constraints_log["permission_check"] = f"FAIL (Missing scope '{required_scope}')"
                return SentinelDecision(
                    approved=False,
                    policy_code=SentinelPolicyCodes.PERMISSION_DENIED,
                    reason=f"Rejected: Subject lacks required execution permission scope '{required_scope}'. Granted: {request.granted_permissions}",
                    confidence=request.confidence,
                    expected_value=request.expected_value,
                    constraints_evaluated=constraints_log,
                )
            constraints_log["permission_check"] = f"PASS (Scoped: {required_scope})"

        # 6. Retry Frequency & Velocity Limit
        max_retries = request.context.get("max_retries", self.config.max_retries)
        if "RETRY" in request.action_type.upper() or request.subject_type == "payment_recovery":
            if request.current_attempt_count >= max_retries:
                constraints_log["retry_limit_check"] = f"FAIL (Attempts {request.current_attempt_count} >= Max {max_retries})"
                return SentinelDecision(
                    approved=False,
                    policy_code=SentinelPolicyCodes.MAX_RETRIES_EXCEEDED,
                    reason=f"Rejected: Maximum retry limit reached ({request.current_attempt_count}/{max_retries}). Halting blind retry loop.",
                    confidence=request.confidence,
                    expected_value=request.expected_value,
                    constraints_evaluated=constraints_log,
                )
            constraints_log["retry_limit_check"] = f"PASS ({request.current_attempt_count}/{max_retries})"

        # 7. Cooldown Window Check
        if request.last_attempt_timestamp and "RETRY" in request.action_type.upper():
            try:
                last_time = dateutil.parser.isoparse(request.last_attempt_timestamp)
                now = datetime.now(timezone.utc)
                if last_time.tzinfo is None:
                    last_time = last_time.replace(tzinfo=timezone.utc)
                
                hours_elapsed = (now - last_time).total_seconds() / 3600.0
                required_cooldown = request.context.get("required_cooldown_hours", self.config.cooldown_hours)
                
                if hours_elapsed < required_cooldown:
                    constraints_log["cooldown_check"] = f"FAIL ({hours_elapsed:.1f}h elapsed < {required_cooldown}h required)"
                    return SentinelDecision(
                        approved=False,
                        policy_code=SentinelPolicyCodes.COOLDOWN_ACTIVE,
                        reason=f"Rejected: Mandatory cooldown active. Only {hours_elapsed:.1f} hours elapsed since last attempt (requires {required_cooldown}h).",
                        confidence=request.confidence,
                        expected_value=request.expected_value,
                        constraints_evaluated=constraints_log,
                    )
                constraints_log["cooldown_check"] = f"PASS ({hours_elapsed:.1f}h elapsed)"
            except (ValueError, TypeError) as e:
                logger.debug("Failed to parse cooldown timestamp '%s': %s", request.last_attempt_timestamp, e)
                constraints_log["cooldown_check"] = f"SKIPPED (invalid timestamp: {request.last_attempt_timestamp})"
            except Exception as e:
                logger.warning("Unexpected error evaluating cooldown for '%s': %s", request.last_attempt_timestamp, e)
                constraints_log["cooldown_check"] = f"SKIPPED (error: {e})"

        # 8. Escalation Frequency Throttling (Anti-Spam / Regulatory Compliance)
        if any(act in request.action_type.upper() for act in ["NOTIFY", "ESCALATE", "PROMPT"]):
            max_escalations = request.context.get("max_escalations", self.config.max_escalations)
            if request.escalation_count >= max_escalations:
                constraints_log["escalation_check"] = f"FAIL ({request.escalation_count} escalations >= Max {max_escalations})"
                return SentinelDecision(
                    approved=False,
                    policy_code=SentinelPolicyCodes.ESCALATION_THROTTLED,
                    reason=f"Rejected: Customer dunning frequency exceeded ({request.escalation_count} notifications sent; maximum allowable is {max_escalations}).",
                    confidence=request.confidence,
                    expected_value=request.expected_value,
                    constraints_evaluated=constraints_log,
                )
            constraints_log["escalation_check"] = f"PASS ({request.escalation_count}/{max_escalations})"

        # 9. Hard Risk / Fraud Block Threshold
        risk_score = request.context.get("risk_score", 0.0)
        max_permissible_risk = request.context.get("max_permissible_risk", self.config.max_permissible_risk)
        if risk_score > max_permissible_risk:
            constraints_log["risk_check"] = f"FAIL (Risk score {risk_score:.2f} > {max_permissible_risk:.2f})"
            return SentinelDecision(
                approved=False,
                policy_code=SentinelPolicyCodes.RISK_THRESHOLD_EXCEEDED,
                reason=f"Rejected: Gateway risk score {risk_score:.2f} exceeds permissible safety ceiling of {max_permissible_risk:.2f}.",
                confidence=request.confidence,
                expected_value=request.expected_value,
                constraints_evaluated=constraints_log,
            )
        constraints_log["risk_check"] = "PASS"

        # If all deterministic constraints clear:
        return SentinelDecision(
            approved=True,
            policy_code=SentinelPolicyCodes.OK,
            reason="Approved: All deterministic policy constraints, bounds, cooldowns, and EV checks cleared.",
            confidence=request.confidence,
            expected_value=request.expected_value,
            constraints_evaluated=constraints_log,
        )


# Global singleton instance for direct zero-overhead evaluation
the_sentinel = Sentinel()
