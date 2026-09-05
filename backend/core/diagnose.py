import os
import json
import logging
from typing import Dict, Any, Optional

from backend.models.schemas import PaymentRecord, DiagnosisResult, FailureCause
from backend.core.llm_client import llm_client, LLMConfigurationError, LLMInferenceError

logger = logging.getLogger("rebound.diagnose")


class DiagnosisEngine:
    """
    AI Diagnosis Engine for subscription payment failures.
    Standardized on Google Gemini API via llm_client.
    ZERO SILENT FALLBACKS:
    - If GEMINI_API_KEY is configured: Calls Gemini for genuine confidence and reasoning.
    - If unconfigured or failed: Returns transparent deterministic rule result
      with is_llm_derived=False, provider='rule_engine', and confidence=0.0 (no fake float).
    """

    def __init__(self):
        self.llm = llm_client

    def diagnose(self, payment: PaymentRecord) -> DiagnosisResult:
        """
        Diagnose the true cause of payment failure with confidence and reasoning.
        """
        # 1. If LLM is configured, execute genuine model inference
        if self.llm.is_configured():
            try:
                llm_output = self.llm.diagnose_payment(
                    payment_id=payment.payment_id,
                    amount=payment.amount,
                    decline_code=payment.decline_code,
                    raw_signal=payment.raw_signal,
                    customer_tier=payment.customer_tier.value,
                    tenure_months=payment.tenure_months,
                    past_failed_retries=payment.past_failed_retries,
                    dunning_attempts=payment.dunning_attempts,
                )
                return DiagnosisResult(
                    payment_id=payment.payment_id,
                    cause=FailureCause(llm_output["cause"]),
                    confidence=float(llm_output["confidence"]),
                    reasoning=llm_output["reasoning"],
                    key_signals=llm_output.get("key_signals", [payment.decline_code]),
                    provider=llm_output.get("_provider", self.llm.provider),
                    model_name=llm_output.get("_model", "gemini-3.5-flash-lite"),
                    is_llm_derived=True,
                    raw_model_response=llm_output.get("_raw_model_response"),
                )
            except Exception as e:
                logger.error(
                    "LLM diagnosis failed for payment %s: %s. Falling back to rule engine.",
                    payment.payment_id,
                    e,
                    exc_info=True,
                )
                # Fall back to transparent rule engine with explicit error notation
                return self._deterministic_diagnose(payment, error_reason=str(e))

        # 2. Transparent deterministic rule fallback (no fake AI claims or fake confidence floats)
        return self._deterministic_diagnose(payment)

    def _deterministic_diagnose(self, payment: PaymentRecord, error_reason: Optional[str] = None) -> DiagnosisResult:
        """
        Deterministic domain rule classifier.
        Explicitly marked with is_llm_derived=False and confidence=0.0 to prevent
        hallucinated status claims or fake precision when no LLM ran.
        """
        code = payment.decline_code.upper()
        signal = payment.raw_signal.lower()
        
        fallback_note = (
            f" [Rule-based fallback: LLM error '{error_reason}']"
            if error_reason
            else " [Rule-based baseline: LLM not configured]"
        )

        # 1. RISK / FRAUD BLOCK
        if any(w in code for w in ["RISK", "FRAUD"]) or any(w in signal for w in ["fraud", "stolen", "chargeback", "thirdwatch", "velocity", "anomaly", "compromised", "bot"]):
            return DiagnosisResult(
                payment_id=payment.payment_id,
                cause=FailureCause.RISK_BLOCK,
                confidence=0.0,
                reasoning=(
                    f"Transaction flagged by gateway risk shield rules. Signal '{payment.decline_code}' "
                    f"indicates potential velocity or credential compromise.{fallback_note}"
                ),
                key_signals=[payment.decline_code, "Gateway risk signal"],
                provider="rule_engine",
                model_name="deterministic_rule_baseline",
                is_llm_derived=False,
                raw_model_response=None,
            )

        # 2. BANK DOWNTIME / SWITCH TIMEOUT
        if any(w in code for w in ["DOWNTIME", "ISSUER_DOWN", "TIMEOUT", "GATEWAY_ERROR", "UNAVAILABLE"]) or any(w in signal for w in ["timeout", "504", "503", "502", "switch down", "maintenance", "unavailable", "latency", "overload"]):
            return DiagnosisResult(
                payment_id=payment.payment_id,
                cause=FailureCause.BANK_DOWNTIME,
                confidence=0.0,
                reasoning=(
                    f"Network or CBS infrastructure outage detected at issuer switch from decline '{payment.decline_code}'.{fallback_note}"
                ),
                key_signals=[payment.decline_code, "Gateway switch timeout"],
                provider="rule_engine",
                model_name="deterministic_rule_baseline",
                is_llm_derived=False,
                raw_model_response=None,
            )

        # 3. CARD EXPIRED
        if any(w in code for w in ["CARD_EXPIRED", "EXPIRED"]) or any(w in signal for w in ["expired", "54", "lapsed", "renewal token"]):
            return DiagnosisResult(
                payment_id=payment.payment_id,
                cause=FailureCause.CARD_EXPIRED,
                confidence=0.0,
                reasoning=(
                    f"Card credentials or authorization token expired per decline '{payment.decline_code}'.{fallback_note}"
                ),
                key_signals=[payment.decline_code, "Card token lapsed"],
                provider="rule_engine",
                model_name="deterministic_rule_baseline",
                is_llm_derived=False,
                raw_model_response=None,
            )

        # 4. INSUFFICIENT FUNDS
        if any(w in code for w in ["INSUFFICIENT_BALANCE", "INSUFFICIENT_FUNDS"]) or any(w in signal for w in ["insufficient funds", "51", "balance low", "balance depleted", "low balance"]):
            return DiagnosisResult(
                payment_id=payment.payment_id,
                cause=FailureCause.INSUFFICIENT_FUNDS,
                confidence=0.0,
                reasoning=(
                    f"Customer account has inadequate balance for debit of INR {payment.amount:,.2f}.{fallback_note}"
                ),
                key_signals=[payment.decline_code, f"Amount: INR {payment.amount:,.2f}"],
                provider="rule_engine",
                model_name="deterministic_rule_baseline",
                is_llm_derived=False,
                raw_model_response=None,
            )

        # 5. ISSUER DECLINE / MANDATE LIMIT
        return DiagnosisResult(
            payment_id=payment.payment_id,
            cause=FailureCause.ISSUER_DECLINE,
            confidence=0.0,
            reasoning=(
                f"Bank issuer rejected recurring charge under code '{payment.decline_code}'.{fallback_note}"
            ),
            key_signals=[payment.decline_code, "Issuer policy decline"],
            provider="rule_engine",
            model_name="deterministic_rule_baseline",
            is_llm_derived=False,
            raw_model_response=None,
        )


# Global singleton engine
diagnosis_engine = DiagnosisEngine()

