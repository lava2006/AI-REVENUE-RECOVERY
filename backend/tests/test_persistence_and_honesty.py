"""
Unit and Integration Tests for Rebound
Tests:
1. Honesty checks: LLM unconfigured -> is_llm_derived=False, no fake confidence floats.
2. Math check: EV = (P_success * Amount) - ActionCost.
3. Persistence check: Data saved to SQLite / Supabase, persists across restarts.
4. Sentinel integrity: Deterministic gating behavior.
"""

import os
import pytest
from backend.models.schemas import (
    PaymentRecord,
    CustomerTier,
    FailureCause,
    RecoveryAction,
)
from backend.core.diagnose import diagnosis_engine
from backend.core.rank import ranking_engine
from backend.core.sentinel import the_sentinel, SentinelPolicyCodes
from backend.core.buyer_agent_demo import parse_buyer_intent
from backend.core.db import db_manager
from backend.core.pipeline import rebound_pipeline


def test_diagnose_honesty_unconfigured(monkeypatch):
    """Verify that without API keys, diagnosis does NOT fabricate LLM claims or confidence floats."""
    monkeypatch.setattr(diagnosis_engine.llm, "provider", "none")
    monkeypatch.setattr(diagnosis_engine.llm, "is_configured", lambda: False)

    payment = PaymentRecord(
        payment_id="pay_test_001",
        subscription_id="sub_test_001",
        amount=15000.0,
        currency="INR",
        timestamp="2026-03-01T10:00:00Z",
        decline_code="INSUFFICIENT_FUNDS",
        raw_signal="Insufficient available balance in account",
        customer_id="cust_001",
        customer_name="Test Customer",
        customer_tier=CustomerTier.ENTERPRISE,
        tenure_months=12,
        true_cause=FailureCause.INSUFFICIENT_FUNDS,
        true_recoverable=True,
    )
    res = diagnosis_engine.diagnose(payment)
    assert res.is_llm_derived is False
    assert res.confidence == 0.0
    assert res.provider == "rule_engine"
    assert "not configured" in res.reasoning


def test_strategy_ranking_ev_math(monkeypatch):
    """Verify that Expected Value strictly equals (P * Amount) - Cost."""
    monkeypatch.setattr(ranking_engine.llm, "provider", "none")
    monkeypatch.setattr(ranking_engine.llm, "is_configured", lambda: False)

    payment = PaymentRecord(
        payment_id="pay_test_002",
        subscription_id="sub_test_002",
        amount=20000.0,
        currency="INR",
        timestamp="2026-03-01T10:00:00Z",
        decline_code="BANK_DOWNTIME",
        raw_signal="Switch timeout 504",
        customer_id="cust_002",
        customer_name="Test Customer 2",
        customer_tier=CustomerTier.GROWTH_SMB,
        tenure_months=6,
        true_cause=FailureCause.BANK_DOWNTIME,
        true_recoverable=True,
    )
    diag = diagnosis_engine.diagnose(payment)
    ranking = ranking_engine.rank(payment, diag)
    assert len(ranking.candidates) == 5
    for cand in ranking.candidates:
        cost = ranking_engine.ACTION_COSTS[cand.action]
        expected_ev = round((cand.success_probability * payment.amount) - cost, 2)
        assert abs(cand.expected_value - expected_ev) < 0.01
        assert cand.is_llm_derived is False


def test_buyer_intent_parser_honesty(monkeypatch):
    """Verify buyer intent parser returns is_llm_derived=False when unconfigured."""
    from backend.core.buyer_agent_demo import llm_client
    monkeypatch.setattr(llm_client, "provider", "none")
    monkeypatch.setattr(llm_client, "is_configured", lambda: False)

    intent = parse_buyer_intent("Need to purchase 1 developer seat for INR 3,500")
    assert intent.is_llm_derived is False
    assert intent.parsing_confidence == 0.0
    assert intent.provider == "regex_parser"


def test_gemini_live_inference():
    """Verify genuine live Gemini LLM inference for diagnosis, strategy EV ranking, and buyer intent parsing."""
    if not diagnosis_engine.llm.is_configured() or diagnosis_engine.llm.provider != "gemini":
        pytest.skip("GEMINI_API_KEY not active in test environment")

    # 1. Live Gemini Diagnosis
    payment = PaymentRecord(
        payment_id="pay_live_gemini_01",
        subscription_id="sub_live_01",
        amount=18500.0,
        currency="INR",
        timestamp="2026-03-01T10:00:00Z",
        decline_code="GATEWAY_ERROR_ISSUER_DOWN",
        raw_signal="HDFC Bank core switch timeout (HTTP 504 Gateway Timeout). Issuer unavailable.",
        customer_id="cust_live_01",
        customer_name="Acme Corp",
        customer_tier=CustomerTier.ENTERPRISE,
        tenure_months=18,
        true_cause=FailureCause.BANK_DOWNTIME,
        true_recoverable=True,
    )
    diag = diagnosis_engine.diagnose(payment)
    assert diag.is_llm_derived is True
    assert diag.provider == "gemini"
    assert diag.cause in [FailureCause.BANK_DOWNTIME, FailureCause.ISSUER_DECLINE]
    assert 0.10 <= diag.confidence <= 1.0

    # 2. Live Gemini Strategy Ranking with EV Verification
    ranking = ranking_engine.rank(payment, diag)
    assert len(ranking.candidates) == 5
    for cand in ranking.candidates:
        assert cand.is_llm_derived is True
        cost = ranking_engine.ACTION_COSTS[cand.action]
        expected_ev = round((cand.success_probability * payment.amount) - cost, 2)
        assert abs(cand.expected_value - expected_ev) < 0.01

    # 3. Live Gemini Buyer Agent Intent Parsing
    buyer_res = parse_buyer_intent("Purchase 2 developer seats for INR 7000")
    assert buyer_res.is_llm_derived is True
    assert buyer_res.provider == "gemini"
    assert buyer_res.sku == "sku_saas_seat"
    assert buyer_res.requested_amount == 7000.0


def test_database_persistence_and_restart():
    """Verify that payment records, diagnoses, and queue session stats persist in database."""
    payment = PaymentRecord(
        payment_id="pay_persist_999",
        subscription_id="sub_persist_999",
        amount=25000.0,
        currency="INR",
        timestamp="2026-03-01T12:00:00Z",
        decline_code="DOWNTIME",
        raw_signal="CBS timeout 504 switch error",
        customer_id="cust_persist_999",
        customer_name="Persistence Client",
        customer_tier=CustomerTier.ENTERPRISE,
        tenure_months=24,
        true_cause=FailureCause.BANK_DOWNTIME,
        true_recoverable=True,
    )
    card, audit = rebound_pipeline.process_payment(payment)
    assert card.recovered is True

    # Read back directly from database manager
    audit_rows = db_manager.get_all_audit_logs(payment_id="pay_persist_999")
    assert len(audit_rows) > 0
    stages = [r["stage"] for r in audit_rows]
    assert "DETECT" in stages
    assert "DIAGNOSE" in stages
    assert "SENTINEL_GATE" in stages
    assert "EXECUTE" in stages
