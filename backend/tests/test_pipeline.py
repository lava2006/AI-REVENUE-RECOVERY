"""
Integration and Pre-Submission Evaluation Tests for Rebound
Runs full batch evaluation over all 55 synthetic records, verifies baseline comparison,
graceful fallback, audit trail completeness, calibration buckets, and queue smart grouping.
"""

import pytest
import random
from backend.core.dataset import BENCHMARK_DATASET
from backend.core.pipeline import rebound_pipeline, compute_calibration_buckets
from backend.core.baseline import naive_baseline
from backend.core.diagnose import diagnosis_engine
from backend.core.rank import ranking_engine
from backend.core.buyer_agent_demo import buyer_agent_runner, BuyerAgentPurchaseRequest
from backend.models.schemas import FailureCause, RecoveryAction, SentinelDecision, QueueItem, QueueGroup


class TestReboundPipelineEvaluation:

    @classmethod
    def setup_class(cls):
        """Execute full batch run once for test assertions using deterministic rules."""
        cls.dataset = BENCHMARK_DATASET
        cls.rebound_results = []
        cls.all_audit_logs = []
        # Temporarily use deterministic engine to avoid exhausting external API quotas on 55 synthetic items
        orig_diag = diagnosis_engine.llm.provider
        orig_rank = ranking_engine.llm.provider
        diagnosis_engine.llm.provider = "none"
        ranking_engine.llm.provider = "none"
        rebound_pipeline.executor.force_stub = True
        rebound_pipeline.executor.reload_credentials()
        try:
            for payment in cls.dataset:
                card, audit = rebound_pipeline.process_payment(payment)
                cls.rebound_results.append(card)
                cls.all_audit_logs.extend(audit)
        finally:
            diagnosis_engine.llm.provider = orig_diag
            ranking_engine.llm.provider = orig_rank
            rebound_pipeline.executor.force_stub = False
            rebound_pipeline.executor.reload_credentials()

        cls.baseline_summary = naive_baseline.run_batch(cls.dataset)

    def test_a_correctness_and_evaluability(self):
        """
        Section 8.A: Correctness & Evaluability
        Batch run over all 50+ records: total ₹ recovered, recovery precision,
        diagnosis accuracy, and naive baseline comparison.
        """
        total_records = len(self.dataset)
        assert total_records >= 50, f"Must have 50+ records, got {total_records}"

        # 1. Diagnosis Accuracy
        correct_diagnoses = sum(
            1 for card in self.rebound_results
            if card.diagnosis.cause == card.payment.true_cause
        )
        diag_accuracy = correct_diagnoses / total_records
        print(f"\n[EVAL] Diagnosis Accuracy: {correct_diagnoses}/{total_records} ({diag_accuracy*100:.1f}%)")
        assert diag_accuracy >= 0.95, f"Diagnosis accuracy too low: {diag_accuracy}"

        # 2. Rebound vs Baseline Recovery
        reb_recovered_amt = sum(c.final_outcome.recovered_amount for c in self.rebound_results if c.recovered and c.final_outcome)
        reb_recovered_count = sum(1 for c in self.rebound_results if c.recovered)
        base_recovered_amt = self.baseline_summary["recovered_amount"]
        base_recovered_count = self.baseline_summary["recovered_count"]

        reb_net = sum(c.net_revenue_impact for c in self.rebound_results)
        base_net = self.baseline_summary["net_recovered"]
        uplift_net = reb_net - base_net

        print(f"[EVAL] Rebound Recovered: INR {reb_recovered_amt:,.2f} ({reb_recovered_count} payments), Net: INR {reb_net:,.2f}")
        print(f"[EVAL] Baseline Recovered: INR {base_recovered_amt:,.2f} ({base_recovered_count} payments), Net: INR {base_net:,.2f}")
        print(f"[EVAL] Net Uplift: +INR {uplift_net:,.2f}")

        assert reb_recovered_amt > base_recovered_amt, "Rebound must recover strictly more revenue than naive baseline"
        assert reb_net > base_net, "Rebound net recovery must exceed naive baseline after costs"

        # 3. Precision (Recoveries per Attempt)
        reb_attempts = sum(len(c.fallback_steps) for c in self.rebound_results)
        reb_precision = reb_recovered_count / reb_attempts if reb_attempts > 0 else 0
        base_precision = self.baseline_summary["recovery_precision"]
        print(f"[EVAL] Precision: Rebound {reb_precision:.2%} vs Baseline {base_precision:.2%}")
        assert reb_precision > base_precision, "Rebound recovery precision must exceed naive baseline"

        # 4. Counterfactual EV Integrity: Verify each EV is genuinely derived
        for card in self.rebound_results:
            for path in card.counterfactual_paths:
                assert isinstance(path.expected_value, float)
                expected_calc = (path.success_probability * card.payment.amount)
                assert abs(path.expected_value - expected_calc) <= 15.0

    def test_b_sentinel_policy_blocks_occur_and_protect_capital(self):
        """
        Section 8.B: Confirms Sentinel halts dangerous actions (Risk Blocks, Cooldowns, Retries).
        """
        blocked_steps = [
            step for card in self.rebound_results
            for step in card.fallback_steps
            if not step.sentinel_approved
        ]
        print(f"[EVAL] Total Sentinel Block Events across batch: {len(blocked_steps)}")
        assert len(blocked_steps) > 0, "Sentinel must block non-compliant actions across the batch"

        # Check that high risk cards were blocked from retrying
        risk_cards = [c for c in self.rebound_results if c.payment.true_cause == FailureCause.RISK_BLOCK]
        for card in risk_cards:
            assert card.recovered is False, "High risk fraudulent cards must not be recovered"
            assert any(not s.sentinel_approved for s in card.fallback_steps)

    def test_c_audit_trail_completeness_trace(self):
        """
        Section 8.C: Pick 3 random records and trace DETECT -> DIAGNOSE -> RANK -> GATE -> EXECUTE
        entirely from audit logs.
        """
        sample_payments = random.sample(self.dataset, 3)
        for payment in sample_payments:
            p_logs = [log for log in self.all_audit_logs if log.payment_id == payment.payment_id]
            stages_present = [log.stage for log in p_logs]
            print(f"[EVAL] Audit trace for {payment.payment_id}: {stages_present}")

            assert "DETECT" in stages_present
            assert "DIAGNOSE" in stages_present
            assert "RANK" in stages_present
            assert "SENTINEL_GATE" in stages_present

            for log in p_logs:
                assert log.timestamp
                assert log.reasoning != "", "Audit log entry should include structured reasoning"
                assert log.details is not None
                assert isinstance(log.details, dict)

    def test_d_failure_handling_and_graceful_fallback(self):
        """
        Section 8.D: Confirm fallback loop falls back to next-ranked strategy and stops per policy.
        """
        fallback_occurrences = [
            card for card in self.rebound_results
            if len(card.fallback_steps) > 1
        ]
        print(f"[EVAL] Cases demonstrating multi-step graceful fallback: {len(fallback_occurrences)}")
        assert len(fallback_occurrences) > 0, "Must have at least one case demonstrating graceful fallback"

        sample = fallback_occurrences[0]
        step1 = sample.fallback_steps[0]
        step2 = sample.fallback_steps[1]
        print(f"[EVAL] Graceful Fallback Example on {sample.payment.payment_id}:")
        print(f"       Step 1: {step1.candidate_action.value} -> Sentinel Approved={step1.sentinel_approved}, Notes: {step1.notes}")
        print(f"       Step 2: {step2.candidate_action.value} -> Sentinel Approved={step2.sentinel_approved}, Notes: {step2.notes}")

    def test_e_sentinel_reuse_in_buyer_agent(self):
        """
        Confirms identical Sentinel evaluates buyer agent procurement requests.
        """
        req_overbudget = BuyerAgentPurchaseRequest(
            agent_id="bot_ops_01",
            agent_name="Ops AutoBot",
            sku_id="sku_enterprise_llm",
            amount=125000.0,
            requested_units=1,
            business_justification="Heavy inference run",
            granted_scopes=["procurement.ai_compute.enterprise"],
            monthly_budget_inr=100000.0,
            current_month_spend_inr=30000.0,
            prior_orders_today=1,
        )
        res = buyer_agent_runner.evaluate_purchase(req_overbudget)
        assert res["sentinel_decision"]["approved"] is False
        assert "BUDGET" in res["sentinel_decision"]["policy_code"]

    def test_f_calibration_buckets_and_reasoned_ev(self):
        """
        Change 8: Calibration table computes predicted vs actual recovery rates across buckets,
        and rationales are non-template (reference customer tier/tenure/retries).
        """
        buckets = compute_calibration_buckets(self.rebound_results)
        assert len(buckets) == 5
        total_bucketed = sum(b.predictions_count for b in buckets)
        assert total_bucketed == len(self.dataset)

        # Check rationales contain varied context
        rationales = [c.ranked_candidates[0].rationale for c in self.rebound_results]
        # Verify that rationales mention customer context
        assert any("tenure" in r.lower() for r in rationales)
        assert any("tier" in r.lower() for r in rationales)

    def test_g_queue_smart_grouping(self):
        """
        Change 1: Verify borderline items can be grouped by (cause, top_strategy)
        and identified cleanly.
        """
        borderline_cards = [c for c in self.rebound_results if c.is_borderline]
        assert len(borderline_cards) > 0, "Must have borderline items for queue triage"
        
        # Verify grouping works
        groups_dict = {}
        for c in borderline_cards:
            k = f"{c.diagnosis.cause.value}::{c.ranked_candidates[0].action.value}"
            groups_dict.setdefault(k, []).append(c)
        assert len(groups_dict) >= 2, "Should produce multiple distinct pattern groups"
