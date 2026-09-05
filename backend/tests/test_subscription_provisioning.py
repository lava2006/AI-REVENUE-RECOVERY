"""
Test suite for Razorpay Subscriptions Backend Provisioning Flow
Verifies:
1. Immutable plan configuration resolution (all 5 tiers)
2. Programmatic Customer creation via POST /v1/customers
3. Programmatic Subscription creation via POST /v1/subscriptions
4. Database persistence in SQLite/Supabase
5. REST endpoints (/api/demo/plans, /api/demo/provision-subscription, /api/demo/subscriptions)
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.core.subscription_service import subscription_service
from backend.core.db import db_manager


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_plans_configuration_integrity():
    """Verify all 5 verified plans are present in configuration with correct IDs."""
    plans = subscription_service.get_plans()
    assert len(plans) == 5, f"Expected 5 plans, found {len(plans)}"
    
    expected_ids = {
        "Starter": "plan_TYM6Bzg8iBVNwz",
        "Growth": "plan_TYM7kSBKYsf6Fn",
        "Enterprise": "plan_TYM8RxbGcgA41q",
        "Annual": "plan_TYM9PDBAuv2auP",
        "Trial": "plan_TYMA0Cu68OotHH",
    }
    
    for plan_name, expected_id in expected_ids.items():
        assert plan_name in plans, f"Plan {plan_name} missing from configuration"
        assert plans[plan_name]["plan_id"] == expected_id, f"Plan ID mismatch for {plan_name}"
        assert plans[plan_name]["amount_in_inr"] > 0, f"Amount must be positive for {plan_name}"


def test_plan_resolution_helper():
    """Verify resolve_plan handles exact, case-insensitive, and invalid cases."""
    starter = subscription_service.resolve_plan("Starter")
    assert starter["plan_id"] == "plan_TYM6Bzg8iBVNwz"
    
    # Case-insensitive
    growth = subscription_service.resolve_plan("growth")
    assert growth["plan_id"] == "plan_TYM7kSBKYsf6Fn"
    
    # Invalid plan name
    with pytest.raises(ValueError) as excinfo:
        subscription_service.resolve_plan("NonExistentPlan")
    assert "Unknown plan name" in str(excinfo.value)


def test_rest_api_list_plans(client):
    """Verify GET /api/demo/plans returns all 5 plans."""
    resp = client.get("/api/demo/plans")
    assert resp.status_code == 200
    data = resp.json()
    assert "Starter" in data
    assert "Growth" in data
    assert "Enterprise" in data
    assert "Annual" in data
    assert "Trial" in data


def test_programmatic_provision_subscription_flow(client):
    """
    Executes a genuine programmatic provisioning call to Razorpay Test Mode:
    Creates Customer, creates Subscription, verifies DB persistence.
    """
    unique_cust_id = f"cust_demo_{uuid.uuid4().hex[:6]}"
    payload = {
        "internal_customer_id": unique_cust_id,
        "customer_name": "Test Runner",
        "customer_email": f"{unique_cust_id}@rebound.ai",
        "customer_contact": "+919876543210",
        "plan_name": "Trial",  # INR 1.00 plan
    }

    resp = client.post("/api/demo/provision-subscription", json=payload)
    assert resp.status_code == 200, f"Provisioning failed: {resp.text}"
    data = resp.json()

    assert data["success"] is True
    assert data["internal_customer_id"] == unique_cust_id
    assert data["customer_id"].startswith("cust_"), f"Invalid Razorpay customer_id: {data['customer_id']}"
    assert data["subscription_id"].startswith("sub_"), f"Invalid Razorpay subscription_id: {data['subscription_id']}"
    assert data["plan"] == "Trial"
    assert data["status"] in ["created", "authenticated", "active"]
    assert "https://rzp.io/rzp/" in data["authorization_url"], f"Invalid short_url: {data['authorization_url']}"

    # Verify Database Persistence
    db_record = db_manager.get_subscription(data["subscription_id"])
    assert db_record is not None, "Subscription not found in database"
    assert db_record["internal_customer_id"] == unique_cust_id
    assert db_record["razorpay_customer_id"] == data["customer_id"]
    assert db_record["plan_name"] == "Trial"
    assert db_record["status"] == data["status"]
    assert db_record["short_url"] == data["authorization_url"]

    # Verify GET /api/demo/subscriptions lists this item
    list_resp = client.get("/api/demo/subscriptions")
    assert list_resp.status_code == 200
    all_subs = list_resp.json()
    assert any(s["subscription_id"] == data["subscription_id"] for s in all_subs)

    # Verify GET /api/demo/subscriptions/{id} returns enriched state
    single_resp = client.get(f"/api/demo/subscriptions/{data['subscription_id']}")
    assert single_resp.status_code == 200
    single_data = single_resp.json()
    assert single_data["subscription_id"] == data["subscription_id"]
    assert "live_gateway_status" in single_data
