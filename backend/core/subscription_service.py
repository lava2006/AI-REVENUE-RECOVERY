"""
Razorpay Subscriptions Service Module for Rebound
Handles fully automated programmatic provisioning of customers and subscriptions
against Razorpay's REST APIs in Test Mode.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("rebound.subscriptions")
logger.setLevel(logging.INFO)

PLANS_CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "plans.json"


class SubscriptionService:
    def __init__(self):
        self.key_id = os.environ.get("RAZORPAY_KEY_ID", "")
        self.key_secret = os.environ.get("RAZORPAY_KEY_SECRET", "")
        self._plans_cache: Optional[Dict[str, Any]] = None
        self._client = None

    def reload_credentials(self):
        self.key_id = os.environ.get("RAZORPAY_KEY_ID", "")
        self.key_secret = os.environ.get("RAZORPAY_KEY_SECRET", "")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self.reload_credentials()
            if not self.key_id or not self.key_secret:
                raise RuntimeError("Razorpay API credentials (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET) not configured.")
            import razorpay
            self._client = razorpay.Client(auth=(self.key_id, self.key_secret))
        return self._client

    def get_plans(self) -> Dict[str, Any]:
        """Loads and caches immutable plan configuration from plans.json."""
        if self._plans_cache is None:
            if not PLANS_CONFIG_PATH.exists():
                raise FileNotFoundError(f"Plans config file not found at {PLANS_CONFIG_PATH}")
            with open(PLANS_CONFIG_PATH, "r", encoding="utf-8") as f:
                self._plans_cache = json.load(f)
        return self._plans_cache

    def resolve_plan(self, plan_name: str) -> Dict[str, Any]:
        """
        Resolves a plan name to its verified Razorpay plan configuration.
        Case-insensitive matching for convenience.
        """
        plans = self.get_plans()
        # Direct match
        if plan_name in plans:
            return plans[plan_name]
        
        # Case-insensitive match
        for name, config in plans.items():
            if name.lower() == plan_name.lower():
                return config
                
        valid_names = list(plans.keys())
        raise ValueError(f"Unknown plan name '{plan_name}'. Available plans: {valid_names}")

    def create_customer(
        self,
        name: str,
        email: str,
        contact: str,
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Creates a Razorpay customer record via POST /v1/customers.
        """
        payload = {
            "name": name,
            "email": email,
            "contact": contact,
            "notes": notes or {"service": "Rebound Autonomous Revenue Recovery"}
        }
        logger.info("[RAZORPAY_API] Creating customer: name=%s, email=%s", name, email)
        try:
            resp = self.client.customer.create(payload)
            logger.info("[RAZORPAY_API] Customer created successfully: customer_id=%s", resp.get("id"))
            return resp
        except Exception as e:
            logger.error("[RAZORPAY_API] Failed to create customer: %s", e, exc_info=True)
            raise RuntimeError(f"Razorpay customer creation failed: {str(e)}") from e

    def create_subscription(
        self,
        plan_id: str,
        customer_id: Optional[str] = None,
        total_count: int = 12,
        quantity: int = 1,
        customer_notify: int = 1,
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Creates a Razorpay Subscription via POST /v1/subscriptions.
        """
        payload = {
            "plan_id": plan_id,
            "total_count": total_count,
            "quantity": quantity,
            "customer_notify": customer_notify,
            "notes": notes or {"system": "Rebound AI Recovery Agent"}
        }
        if customer_id:
            payload["customer_id"] = customer_id

        logger.info("[RAZORPAY_API] Creating subscription for plan_id=%s, customer_id=%s", plan_id, customer_id)
        try:
            resp = self.client.subscription.create(payload)
            logger.info(
                "[RAZORPAY_API] Subscription created successfully: sub_id=%s, status=%s, short_url=%s",
                resp.get("id"),
                resp.get("status"),
                resp.get("short_url"),
            )
            return resp
        except Exception as e:
            logger.error("[RAZORPAY_API] Failed to create subscription: %s", e, exc_info=True)
            raise RuntimeError(f"Razorpay subscription creation failed: {str(e)}") from e

    def fetch_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Fetches live subscription status via GET /v1/subscriptions/{id}.
        """
        try:
            return self.client.subscription.fetch(subscription_id)
        except Exception as e:
            logger.error("[RAZORPAY_API] Failed to fetch subscription %s: %s", subscription_id, e)
            raise RuntimeError(f"Razorpay fetch subscription failed: {str(e)}") from e

    def provision_subscription(
        self,
        internal_customer_id: str,
        customer_name: str,
        customer_email: str,
        customer_contact: str,
        plan_name: str,
    ) -> Dict[str, Any]:
        """
        Complete end-to-end backend provisioning flow:
        1. Resolve plan_id from configuration
        2. Create Customer in Razorpay
        3. Create Subscription in Razorpay
        4. Persist mapping into database
        5. Return clean structured response with authorization_url
        """
        from backend.core.db import db_manager

        # Step 1: Resolve Plan
        plan_config = self.resolve_plan(plan_name)
        plan_id = plan_config["plan_id"]

        # Step 2: Create Customer
        customer_record = self.create_customer(
            name=customer_name,
            email=customer_email,
            contact=customer_contact,
            notes={"internal_customer_id": internal_customer_id},
        )
        razorpay_customer_id = customer_record.get("id")

        # Step 3: Create Subscription
        sub_record = self.create_subscription(
            plan_id=plan_id,
            customer_id=razorpay_customer_id,
            total_count=12,
            customer_notify=1,
            notes={
                "internal_customer_id": internal_customer_id,
                "plan_name": plan_name,
            },
        )
        subscription_id = sub_record.get("id")
        status = sub_record.get("status", "created")
        short_url = sub_record.get("short_url", "")
        now_iso = datetime.now(timezone.utc).isoformat()

        # Step 4: Persist in Database
        db_payload = {
            "internal_customer_id": internal_customer_id,
            "razorpay_customer_id": razorpay_customer_id,
            "plan_name": plan_config["name"],
            "razorpay_plan_id": plan_id,
            "subscription_id": subscription_id,
            "status": status,
            "short_url": short_url,
            "created_at": now_iso,
            "updated_at": now_iso,
            "raw_response": sub_record,
        }
        db_manager.save_subscription(db_payload)

        # Step 5: Structured Response
        return {
            "success": True,
            "internal_customer_id": internal_customer_id,
            "customer_id": razorpay_customer_id,
            "subscription_id": subscription_id,
            "plan": plan_config["name"],
            "plan_id": plan_id,
            "amount_inr": plan_config["amount_in_inr"],
            "status": status,
            "authorization_url": short_url,
            "created_at": now_iso,
        }


subscription_service = SubscriptionService()
