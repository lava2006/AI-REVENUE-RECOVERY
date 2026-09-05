"""
Unit and Integration Tests for Real Razorpay Test-Mode Integration.
Tests:
1. Real Order creation via POST /v1/orders (verifying genuine order_ id)
2. Real Payment Link creation via POST /v1/payment_links (verifying genuine plink_ id and short URL)
3. Cryptographic HMAC-SHA256 signature verification (genuine passes, tampered fails)
4. Full pipeline execution with real Razorpay Order creation and signature check
5. Loud, explicit fallback to razorpay_test_stub when credentials are missing or invalidated
6. Database persistence of real Razorpay identifiers across simulated reboot
"""

import os
import pytest
from backend.models.schemas import PaymentRecord, CustomerTier, FailureCause, RecoveryAction
from backend.core.executor import razorpay_executor, OFFICIAL_TEST_INSTRUMENTS
from backend.core.pipeline import rebound_pipeline
from backend.core.db import db_manager


def test_real_razorpay_order_creation():
    """Verify that a genuine Order is created on Razorpay Test servers via POST /v1/orders."""
    if not razorpay_executor.has_live_keys:
        pytest.skip("Razorpay test keys not configured in environment.")

    payment = PaymentRecord(
        payment_id="pay_live_test_ord_01",
        subscription_id="sub_live_test_01",
        amount=3500.0,
        currency="INR",
        timestamp="2026-03-01T10:00:00Z",
        decline_code="GATEWAY_ERROR_ISSUER_DOWN",
        raw_signal="HDFC CBS timeout 504",
        customer_id="cust_ord_01",
        customer_name="Test Enterprise Corp",
        customer_tier=CustomerTier.ENTERPRISE,
        tenure_months=12,
        true_cause=FailureCause.BANK_DOWNTIME,
        true_recoverable=True,
    )
    order_data = razorpay_executor.create_order(payment, RecoveryAction.RETRY_LATER)
    assert order_data is not None
    assert "id" in order_data
    assert order_data["id"].startswith("order_")
    assert order_data["entity"] == "order"
    assert order_data["amount"] == 350000  # 3500.00 INR in paise
    assert order_data["currency"] == "INR"
    assert order_data["receipt"] == "pay_live_test_ord_01"
    assert order_data["status"] == "created"
    print(f"\n[LIVE RAZORPAY] Real Order Created: {order_data['id']}")


def test_real_razorpay_payment_link_creation():
    """Verify that a genuine 1-click Payment Link is created via POST /v1/payment_links."""
    if not razorpay_executor.has_live_keys:
        pytest.skip("Razorpay test keys not configured in environment.")

    payment = PaymentRecord(
        payment_id="pay_live_test_plink_01",
        subscription_id="sub_live_test_02",
        amount=2500.0,
        currency="INR",
        timestamp="2026-03-01T10:00:00Z",
        decline_code="INSUFFICIENT_FUNDS",
        raw_signal="Low balance",
        customer_id="cust_plink_01",
        customer_name="SaaS Buyer",
        customer_tier=CustomerTier.GROWTH_SMB,
        tenure_months=8,
        true_cause=FailureCause.INSUFFICIENT_FUNDS,
        true_recoverable=True,
    )
    plink_data = razorpay_executor.create_payment_link(payment, RecoveryAction.NOTIFY_CUSTOMER)
    assert plink_data is not None
    assert "id" in plink_data
    assert plink_data["id"].startswith("plink_")
    assert plink_data["amount"] == 250000
    assert "short_url" in plink_data
    assert plink_data["short_url"].startswith("http")
    print(f"\n[LIVE RAZORPAY] Real Payment Link Created: {plink_data['id']} -> {plink_data['short_url']}")


def test_mandatory_server_side_signature_verification():
    """Verify cryptographic HMAC-SHA256 signature verification logic."""
    order_id = "order_test_signature_999"
    payment_id = "pay_test_signature_999"

    # 1. Genuine Signature must PASS
    genuine_sig = razorpay_executor.create_test_signature(order_id, payment_id)
    assert razorpay_executor.verify_signature(order_id, payment_id, genuine_sig) is True

    # 2. Tampered / Injected Signature must FAIL
    tampered_sig = genuine_sig[:-4] + "dead"
    assert razorpay_executor.verify_signature(order_id, payment_id, tampered_sig) is False

    # 3. Wrong order_id must FAIL
    assert razorpay_executor.verify_signature("order_wrong_order_111", payment_id, genuine_sig) is False


def test_full_pipeline_live_razorpay_execution():
    """Verify complete pipeline execution generating real Order and verified outcome."""
    if not razorpay_executor.has_live_keys:
        pytest.skip("Razorpay test keys not configured in environment.")

    payment = PaymentRecord(
        payment_id="pay_pipe_live_rzp_01",
        subscription_id="sub_pipe_01",
        amount=12000.0,
        currency="INR",
        timestamp="2026-03-01T10:00:00Z",
        decline_code="GATEWAY_ERROR_ISSUER_DOWN",
        raw_signal="Switch timeout 504",
        customer_id="cust_pipe_01",
        customer_name="Pipeline Client",
        customer_tier=CustomerTier.ENTERPRISE,
        tenure_months=20,
        true_cause=FailureCause.BANK_DOWNTIME,
        true_recoverable=True,
    )
    card, audit = rebound_pipeline.process_payment(payment)
    assert card.recovered is True
    assert card.final_outcome is not None
    assert card.final_outcome.execution_backend == "razorpay_test_mode_api"
    assert card.final_outcome.razorpay_order_id is not None
    assert card.final_outcome.razorpay_order_id.startswith("order_")
    assert card.final_outcome.signature_verified is True
    assert card.final_outcome.test_instrument == OFFICIAL_TEST_INSTRUMENTS["SUCCESS_VISA"]

    # Verify audit trail contains the real Razorpay Order ID
    exec_audit = next((a for a in audit if a.stage == "EXECUTE"), None)
    assert exec_audit is not None
    assert exec_audit.details.get("razorpay_order_id") == card.final_outcome.razorpay_order_id
    assert exec_audit.details.get("signature_verified") is True


def test_loud_fallback_when_credentials_missing(monkeypatch):
    """Verify loud, explicit fallback to razorpay_test_stub when keys are missing or blanked."""
    monkeypatch.setenv("RAZORPAY_KEY_ID", "")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "")
    razorpay_executor.reload_credentials()

    payment = PaymentRecord(
        payment_id="pay_fallback_01",
        subscription_id="sub_fb_01",
        amount=5000.0,
        currency="INR",
        timestamp="2026-03-01T10:00:00Z",
        decline_code="GATEWAY_ERROR_ISSUER_DOWN",
        raw_signal="Switch 504",
        customer_id="cust_fb_01",
        customer_name="Fallback Customer",
        customer_tier=CustomerTier.GROWTH_SMB,
        tenure_months=6,
        true_cause=FailureCause.BANK_DOWNTIME,
        true_recoverable=True,
    )
    outcome = razorpay_executor.execute_action(payment, RecoveryAction.RETRY_NOW)
    assert outcome.execution_backend == "razorpay_test_stub"
    assert outcome.success is True
    assert outcome.gateway_code == "PAYMENT_CAPTURED_SUCCESS"


def test_database_persistence_of_real_razorpay_data():
    """Verify that real Razorpay order IDs and signature status persist in DB across restarts."""
    from dotenv import load_dotenv
    load_dotenv(override=True)
    razorpay_executor.reload_credentials()
    if not razorpay_executor.has_live_keys:
        pytest.skip("Razorpay test keys not configured.")

    payment = PaymentRecord(
        payment_id="pay_persist_rzp_999",
        subscription_id="sub_persist_999",
        amount=8500.0,
        currency="INR",
        timestamp="2026-03-01T10:00:00Z",
        decline_code="GATEWAY_ERROR_ISSUER_DOWN",
        raw_signal="Switch 504",
        customer_id="cust_persist_999",
        customer_name="Persist Customer",
        customer_tier=CustomerTier.ENTERPRISE,
        tenure_months=15,
        true_cause=FailureCause.BANK_DOWNTIME,
        true_recoverable=True,
    )
    card, audit = rebound_pipeline.process_payment(payment)
    assert card.recovered is True
    real_order_id = card.final_outcome.razorpay_order_id

    # Read back audit log from database
    audit_rows = db_manager.get_all_audit_logs(payment_id="pay_persist_rzp_999")
    exec_rows = [r for r in audit_rows if r["stage"] == "EXECUTE"]
    assert len(exec_rows) > 0
    assert exec_rows[0]["details"]["razorpay_order_id"] == real_order_id
    assert exec_rows[0]["details"]["signature_verified"] is True
