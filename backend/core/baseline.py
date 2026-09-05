"""
Naive Blind-Retry Baseline Engine
Implements the standard industry baseline for comparison against Rebound:
Blindly re-attempts failed recurring payments without diagnosis, cooldown intelligence,
or alternative payment rails. Tracks recovered revenue, burned retry fees, and fraud penalties.
"""

from typing import List, Dict, Any
from backend.models.schemas import PaymentRecord, FailureCause, RecoveryAction


class NaiveBaselineRunner:
    """
    Simulates naive merchant behavior:
    - Retries immediately (RETRY_NOW) up to 3 times for every failure.
    - No root-cause diagnosis.
    - No alternative payment rail offering (UPI/Netbanking).
    - No card update prompting.
    - Retries even on high-risk/stolen cards (incurring chargeback fees).
    """

    RETRY_FEE_INR: float = 2.50
    CHARGEBACK_PENALTY_INR: float = 150.0  # Network penalty for repeatedly charging flagged cards

    def run_payment(self, payment: PaymentRecord) -> Dict[str, Any]:
        attempts = 0
        costs = 0.0
        recovered = False
        recovered_amount = 0.0
        failure_reasons = []

        max_naive_retries = 3

        while attempts < max_naive_retries and not recovered:
            attempts += 1
            costs += self.RETRY_FEE_INR

            # Naive retry mechanics:
            if payment.true_cause == FailureCause.BANK_DOWNTIME:
                # Downtime clears on 1st or 2nd attempt
                recovered = True
                recovered_amount = payment.amount
                break

            elif payment.true_cause == FailureCause.INSUFFICIENT_FUNDS:
                # Blind immediate retry rarely works without payday timing or alert
                # Small ~8% random chance if funds happened to arrive
                if attempts == 2 and payment.customer_tier.value == "Enterprise":
                    recovered = True
                    recovered_amount = payment.amount
                    break
                else:
                    failure_reasons.append("Account balance still insufficient")

            elif payment.true_cause == FailureCause.CARD_EXPIRED:
                # 0% chance of recovery through blind retrying
                failure_reasons.append("Card token still expired")

            elif payment.true_cause == FailureCause.ISSUER_DECLINE:
                # Blind retrying same card without mandate switch fails 100%
                failure_reasons.append("Issuer policy continues to reject recurring card debit")

            elif payment.true_cause == FailureCause.RISK_BLOCK:
                # Dangerous: blind retry on stolen card incurs heavy network penalty
                costs += self.CHARGEBACK_PENALTY_INR
                failure_reasons.append("Fraudulent transaction charged again; chargeback penalty incurred")

        net_recovered = recovered_amount - costs

        return {
            "payment_id": payment.payment_id,
            "recovered": recovered,
            "recovered_amount": recovered_amount,
            "attempts": attempts,
            "costs": costs,
            "net_recovered": net_recovered,
            "failure_reasons": failure_reasons,
        }

    def run_batch(self, dataset: List[PaymentRecord]) -> Dict[str, Any]:
        results = [self.run_payment(p) for p in dataset]
        total_recovered_amount = sum(r["recovered_amount"] for r in results)
        total_recovered_count = sum(1 for r in results if r["recovered"])
        total_attempts = sum(r["attempts"] for r in results)
        total_costs = sum(r["costs"] for r in results)
        net_recovered = total_recovered_amount - total_costs
        precision = (total_recovered_count / total_attempts) if total_attempts > 0 else 0.0

        return {
            "total_records": len(dataset),
            "recovered_amount": round(total_recovered_amount, 2),
            "recovered_count": total_recovered_count,
            "attempted_count": total_attempts,
            "recovery_precision": round(precision, 4),
            "total_execution_costs": round(total_costs, 2),
            "net_recovered": round(net_recovered, 2),
            "payment_results": results,
        }


# Global singleton baseline runner
naive_baseline = NaiveBaselineRunner()
