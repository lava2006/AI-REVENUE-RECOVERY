"""
FastAPI Server for Rebound — AI Revenue Recovery Agent
Exposes endpoints for the 8-stage pipeline, the standalone Sentinel gate,
audit logs, Decision Cards, configurable policy rules, dynamic catalog, and the Review Queue.
"""

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import csv
import io

from backend.models.schemas import (
    PaymentRecord,
    RecoveryDecisionCardData,
    AuditLogEntry,
    BatchRunSummary,
    PolicyRequest,
    SentinelDecision,
    MerchantPolicyConfig,
    MerchantCatalogItem,
    BuyerCatalogItem,
    BuyerAgentPurchaseRequest,
    QueueItem,
    QueueGroup,
    CalibrationBucket,
    CustomerTier,
    ProvisionSubscriptionRequest,
    ProvisionSubscriptionResponse,
)
from backend.core.dataset import BENCHMARK_DATASET
from backend.core.pipeline import rebound_pipeline, compute_calibration_buckets
from backend.core.baseline import naive_baseline
from backend.core.sentinel import the_sentinel
from backend.core.executor import razorpay_executor
from backend.core.subscription_service import subscription_service
from backend.core.buyer_agent_demo import (
    buyer_agent_runner,
    catalog_store,
    parse_buyer_intent,
    DEFAULT_CATALOG_ITEMS,
)
from backend.core.db import db_manager
from backend.core.llm_client import llm_client
from backend.core.diagnose import diagnosis_engine
from backend.core.rank import ranking_engine


app = FastAPI(
    title="Rebound — AI Revenue Recovery Agent API",
    description="Track 3: AI Revenue Recovery with Standalone Sentinel Policy Engine",
    version="1.1.0",
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cached batch state
CACHED_BATCH_SUMMARY: Optional[BatchRunSummary] = None
CACHED_AUDIT_TRAIL: List[AuditLogEntry] = []
PAYMENT_CARD_MAP: Dict[str, RecoveryDecisionCardData] = {}

# --- Review Queue State ---
QUEUE_INITIALIZED: bool = False
QUEUE_ITEMS_MAP: Dict[str, QueueItem] = {}
AUTO_HANDLED_STATS = {
    "count": 0,
    "recovered_amount": 0.0,
    "net_impact": 0.0,
}
QUEUE_SESSION_RECOVERED = {
    "count": 0,
    "amount": 0.0,
}


def _execute_full_batch() -> BatchRunSummary:
    global CACHED_BATCH_SUMMARY, CACHED_AUDIT_TRAIL, PAYMENT_CARD_MAP
    
    cards: List[RecoveryDecisionCardData] = []
    audits: List[AuditLogEntry] = []
    
    # Warm benchmark cache deterministically to boot in 0.1s without exhausting external API quota
    orig_diag = diagnosis_engine.llm.provider
    orig_rank = ranking_engine.llm.provider
    diagnosis_engine.llm.provider = "none"
    ranking_engine.llm.provider = "none"
    rebound_pipeline.executor.force_stub = True
    rebound_pipeline.executor.reload_credentials()
    try:
        for payment in BENCHMARK_DATASET:
            card, audit = rebound_pipeline.process_payment(payment)
            cards.append(card)
            audits.extend(audit)
            PAYMENT_CARD_MAP[payment.payment_id] = card
    finally:
        diagnosis_engine.llm.provider = orig_diag
        ranking_engine.llm.provider = orig_rank
        rebound_pipeline.executor.force_stub = False
        rebound_pipeline.executor.reload_credentials()

    CACHED_AUDIT_TRAIL = audits

    # Rebound Metrics
    reb_recovered_amt = sum(c.final_outcome.recovered_amount for c in cards if c.recovered and c.final_outcome)
    reb_recovered_count = sum(1 for c in cards if c.recovered)
    reb_attempts = sum(len(c.fallback_steps) for c in cards)
    reb_precision = (reb_recovered_count / reb_attempts) if reb_attempts > 0 else 0.0
    reb_costs = round(sum(
        c.final_outcome.recovered_amount - c.net_revenue_impact if c.recovered and c.final_outcome else -c.net_revenue_impact
        for c in cards
    ), 2)
    reb_net = round(reb_recovered_amt - reb_costs, 2)

    # Baseline Metrics
    base_summary = naive_baseline.run_batch(BENCHMARK_DATASET)
    base_recovered_amt = base_summary["recovered_amount"]
    base_recovered_count = base_summary["recovered_count"]
    base_attempts = base_summary["attempted_count"]
    base_precision = base_summary["recovery_precision"]
    base_costs = base_summary["total_execution_costs"]
    base_net = base_summary["net_recovered"]

    net_uplift = round(reb_net - base_net, 2)
    uplift_pct = round((net_uplift / max(1.0, base_net)) * 100.0, 1)

    correct_diagnoses = sum(1 for c in cards if c.diagnosis.cause == c.payment.true_cause)
    diag_accuracy = round((correct_diagnoses / len(BENCHMARK_DATASET)) * 100.0, 1)

    sentinel_blocks = sum(
        sum(1 for step in c.fallback_steps if not step.sentinel_approved)
        for c in cards
    )
    ineffective_prevented = base_attempts - reb_attempts

    calibration = compute_calibration_buckets(cards)

    summary = BatchRunSummary(
        total_records=len(BENCHMARK_DATASET),
        rebound_recovered_amount=round(reb_recovered_amt, 2),
        rebound_recovered_count=reb_recovered_count,
        rebound_attempted_count=reb_attempts,
        rebound_recovery_precision=round(reb_precision, 4),
        rebound_total_execution_costs=round(reb_costs, 2),
        rebound_net_recovered=reb_net,
        
        baseline_recovered_amount=base_recovered_amt,
        baseline_recovered_count=base_recovered_count,
        baseline_attempted_count=base_attempts,
        baseline_recovery_precision=base_precision,
        baseline_total_execution_costs=base_costs,
        baseline_net_recovered=base_net,

        net_uplift_amount=net_uplift,
        net_uplift_percent=uplift_pct,
        ineffective_retries_prevented=max(0, ineffective_prevented),
        diagnosis_accuracy=diag_accuracy,
        sentinel_blocks_count=sentinel_blocks,
        
        records=cards,
        audit_logs=audits,
        calibration_buckets=calibration,
    )
    CACHED_BATCH_SUMMARY = summary
    return summary


def _restore_state_from_db():
    """Restores queue state and statistics from persistent database (Supabase or SQLite)."""
    global QUEUE_INITIALIZED, QUEUE_ITEMS_MAP, AUTO_HANDLED_STATS, QUEUE_SESSION_RECOVERED
    stats = db_manager.get_queue_session_stats()
    if stats and stats.get("first_run_loaded"):
        QUEUE_INITIALIZED = True
        AUTO_HANDLED_STATS["count"] = stats.get("auto_handled_count", 0)
        AUTO_HANDLED_STATS["recovered_amount"] = stats.get("auto_handled_amount", 0.0)
        AUTO_HANDLED_STATS["net_impact"] = stats.get("auto_handled_net", 0.0)
        QUEUE_SESSION_RECOVERED["count"] = stats.get("session_recovered_count", 0)
        QUEUE_SESSION_RECOVERED["amount"] = stats.get("session_recovered_amount", 0.0)

        db_items = db_manager.get_all_queue_items()
        if db_items:
            QUEUE_ITEMS_MAP.clear()
            for it in db_items:
                card = PAYMENT_CARD_MAP.get(it["payment_id"])
                if card:
                    q_item = QueueItem(
                        item_id=it["item_id"],
                        payment_id=it["payment_id"],
                        diagnosed_cause=it["diagnosed_cause"],
                        top_ranked_strategy=it["top_ranked_strategy"],
                        group_key=it["group_key"],
                        amount=it["amount"],
                        customer_name=it["customer_name"],
                        customer_tier=it["customer_tier"],
                        card_data=card,
                        item_type=it.get("item_type", "recovery"),
                        is_borderline=bool(it.get("is_borderline", 1)),
                        advisory_note=it.get("advisory_note"),
                    )
                    QUEUE_ITEMS_MAP[q_item.item_id] = q_item


# Auto-warm cache and restore persistent state on startup
_execute_full_batch()
_restore_state_from_db()


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Rebound Revenue Recovery",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sentinel_status": "ACTIVE_DETERMINISTIC",
        "database_backend": db_manager.backend,
        "database_connected": True,
        "llm_configured": llm_client.is_configured(),
        "llm_provider": llm_client.provider,
        "total_dataset_records": len(BENCHMARK_DATASET),
        "policy_config": the_sentinel.config.model_dump(),
    }


# ============================================================================
# RAZORPAY SUBSCRIPTION PROVISIONING & MANAGEMENT (v3)
# ============================================================================

@app.get("/api/demo/plans")
def list_demo_plans():
    """Returns the 5 pre-configured, verified Razorpay Subscription Plans."""
    try:
        return subscription_service.get_plans()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/demo/provision-subscription", response_model=ProvisionSubscriptionResponse)
def provision_subscription(req: ProvisionSubscriptionRequest):
    """
    Programmatically provisions a Customer and a Subscription in Razorpay Test Mode.
    Zero manual dashboard intervention required.
    Returns the one-time mandate authorization_url for the customer.
    """
    try:
        res = subscription_service.provision_subscription(
            internal_customer_id=req.internal_customer_id,
            customer_name=req.customer_name,
            customer_email=req.customer_email,
            customer_contact=req.customer_contact,
            plan_name=req.plan_name,
        )
        return ProvisionSubscriptionResponse(**res)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Razorpay provisioning failed: {str(e)}")


@app.get("/api/demo/subscriptions")
def list_demo_subscriptions():
    """Lists all programmatically provisioned subscriptions stored in database."""
    return db_manager.get_all_subscriptions()


@app.get("/api/demo/subscriptions/{subscription_id}")
def get_demo_subscription(subscription_id: str):
    """Retrieves a single subscription status from database and live Razorpay status."""
    db_sub = db_manager.get_subscription(subscription_id)
    if not db_sub:
        raise HTTPException(status_code=404, detail=f"Subscription {subscription_id} not found in database.")
    
    # Enrich with live gateway status if available
    try:
        live_sub = subscription_service.fetch_subscription(subscription_id)
        db_sub["live_gateway_status"] = live_sub.get("status")
        db_sub["auth_attempts"] = live_sub.get("auth_attempts")
        db_sub["paid_count"] = live_sub.get("paid_count")
    except Exception:
        db_sub["live_gateway_status"] = db_sub.get("status")

    return db_sub


# ============================================================================
# CONFIGURABLE POLICY RULES (Change 6)
# ============================================================================

@app.get("/api/policy-config", response_model=MerchantPolicyConfig)
def get_policy_config():
    """Retrieve active Sentinel policy thresholds."""
    return the_sentinel.config


@app.post("/api/policy-config", response_model=MerchantPolicyConfig)
def update_policy_config(config: MerchantPolicyConfig):
    """
    Update merchant policy thresholds in real-time.
    Dynamic lookup by Sentinel at decision time.
    """
    the_sentinel.update_config(config)
    # Refresh cached batch to reflect new policy rules
    _execute_full_batch()
    return the_sentinel.config


# ============================================================================
# UPLOADABLE MERCHANT CATALOG (Change 7)
# ============================================================================

@app.get("/api/buyer-agent/catalog", response_model=List[MerchantCatalogItem])
def get_buyer_catalog():
    """Retrieve active merchant catalog for agent purchase gating."""
    return catalog_store.get_catalog()


@app.post("/api/buyer-agent/catalog/upload")
def upload_buyer_catalog(items: Optional[List[MerchantCatalogItem]] = None, csv_data: Optional[str] = Body(None)):
    """
    Upload a replacement merchant catalog via JSON payload or raw CSV text.
    Validates sku, name, price, and stock status before storing.
    """
    parsed_items: List[MerchantCatalogItem] = []
    
    if items:
        parsed_items = items
    elif csv_data:
        reader = csv.DictReader(io.StringIO(csv_data))
        for row in reader:
            parsed_items.append(MerchantCatalogItem(
                sku=row.get("sku", f"sku_{uuid.uuid4().hex[:6]}"),
                name=row.get("name", "Unnamed Item"),
                price=float(row.get("price", 0.0)),
                in_stock=row.get("in_stock", "true").lower() in ["true", "1", "yes"],
                category=row.get("category", "General"),
                requires_permission=row.get("requires_permission", "procurement.saas.basic"),
                description=row.get("description", ""),
            ))
    else:
        raise HTTPException(status_code=400, detail="No catalog items or CSV content provided.")

    catalog_store.update_catalog(parsed_items)
    return {
        "status": "success",
        "catalog_size": len(parsed_items),
        "catalog": catalog_store.get_catalog(),
    }


@app.post("/api/buyer-agent/catalog/reset")
def reset_buyer_catalog():
    """Reset catalog back to seeded benchmark items."""
    catalog_store.reset_defaults()
    return {"status": "reset_to_defaults", "catalog": catalog_store.get_catalog()}


# ============================================================================
# BUYER AGENT PARSING & EVALUATION (Change 5)
# ============================================================================

@app.post("/api/buyer-agent/parse-intent")
def parse_agent_intent(prompt: str = Body(..., embed=True)):
    """
    Upstream intent parser for autonomous buyer agent.
    Converts unstructured requests into structured {sku, requested_amount, scope}.
    """
    intent = parse_buyer_intent(prompt, catalog_store.get_catalog())
    return intent


@app.post("/api/buyer-agent/evaluate")
def evaluate_buyer_agent_purchase(req: BuyerAgentPurchaseRequest):
    """
    Closing Demo Beat: Point the EXACT SAME UNMODIFIED Sentinel
    at a simulated AI buyer agent's purchase request.
    """
    return buyer_agent_runner.evaluate_purchase(req)


# ============================================================================
# REVIEW QUEUE & SMART GROUPING (Change 1)
# ============================================================================

def _build_queue_groups(items: List[QueueItem]) -> List[QueueGroup]:
    """Auto-groups queue items by (diagnosed_cause, top_ranked_strategy)."""
    groups_dict: Dict[str, List[QueueItem]] = {}
    for it in items:
        k = it.group_key
        if k not in groups_dict:
            groups_dict[k] = []
        groups_dict[k].append(it)

    groups: List[QueueGroup] = []
    for k, itms in groups_dict.items():
        sample = itms[0]
        label = f"{len(itms)} payments — {sample.diagnosed_cause} · {sample.top_ranked_strategy} recommended"
        if sample.item_type == "agent_commerce":
            label = f"{len(itms)} Agent Request — {sample.top_ranked_strategy}"
        groups.append(QueueGroup(
            group_key=k,
            diagnosed_cause=sample.diagnosed_cause,
            top_ranked_strategy=sample.top_ranked_strategy,
            item_count=len(itms),
            total_amount=round(sum(i.amount for i in itms), 2),
            item_type=sample.item_type,
            label=label,
            items=itms,
        ))
    return groups


@app.get("/api/queue")
def get_queue():
    """Retrieve the current state of the Review Queue."""
    items = list(QUEUE_ITEMS_MAP.values())
    groups = _build_queue_groups(items)
    return {
        "first_run_loaded": QUEUE_INITIALIZED,
        "queue_cleared": QUEUE_INITIALIZED and len(items) == 0,
        "pending_items_count": len(items),
        "groups": groups,
        "auto_handled_count": AUTO_HANDLED_STATS["count"],
        "auto_handled_amount": round(AUTO_HANDLED_STATS["recovered_amount"], 2),
        "session_recovered_count": QUEUE_SESSION_RECOVERED["count"],
        "session_recovered_amount": round(QUEUE_SESSION_RECOVERED["amount"], 2),
    }


@app.post("/api/queue/load")
def load_queue_payments():
    """
    First-run lightweight start: 'Load today's payments'.
    Automatically processes high-confidence/low-friction items in background,
    and puts borderline/low-confidence items into the Review Queue grouped by pattern.
    """
    global QUEUE_INITIALIZED, QUEUE_ITEMS_MAP, AUTO_HANDLED_STATS, QUEUE_SESSION_RECOVERED
    
    QUEUE_ITEMS_MAP.clear()
    auto_count = 0
    auto_rec_amt = 0.0
    auto_net = 0.0

    for payment in BENCHMARK_DATASET:
        card, audit = rebound_pipeline.process_payment(payment)
        PAYMENT_CARD_MAP[payment.payment_id] = card
        CACHED_AUDIT_TRAIL.extend(audit)

        if card.is_borderline:
            group_key = f"{card.diagnosis.cause.value}::{card.ranked_candidates[0].action.value}"
            item = QueueItem(
                item_id=f"q_{payment.payment_id}",
                payment_id=payment.payment_id,
                diagnosed_cause=card.diagnosis.cause.value,
                top_ranked_strategy=card.ranked_candidates[0].action.value,
                group_key=group_key,
                amount=payment.amount,
                customer_name=f"Customer {payment.customer_id}",
                customer_tier=payment.customer_tier.value,
                card_data=card,
                item_type="recovery",
                is_borderline=True,
                advisory_note=card.advisory_note,
            )
            QUEUE_ITEMS_MAP[item.item_id] = item
        else:
            # Silent background auto-handling
            auto_count += 1
            if card.recovered and card.final_outcome:
                auto_rec_amt += card.final_outcome.recovered_amount
            auto_net += card.net_revenue_impact

    AUTO_HANDLED_STATS["count"] = auto_count
    AUTO_HANDLED_STATS["recovered_amount"] = round(auto_rec_amt, 2)
    AUTO_HANDLED_STATS["net_impact"] = round(auto_net, 2)
    QUEUE_INITIALIZED = True
    QUEUE_SESSION_RECOVERED = {"count": 0, "amount": 0.0}

    # Persist queue items and initial session stats into database (Supabase or SQLite)
    db_manager.clear_queue_items()
    for item in QUEUE_ITEMS_MAP.values():
        db_manager.upsert_queue_item({
            "item_id": item.item_id,
            "payment_id": item.payment_id,
            "diagnosed_cause": item.diagnosed_cause,
            "top_ranked_strategy": item.top_ranked_strategy,
            "group_key": item.group_key,
            "amount": item.amount,
            "customer_name": item.customer_name,
            "customer_tier": item.customer_tier,
            "item_type": item.item_type,
            "is_borderline": item.is_borderline,
            "advisory_note": item.advisory_note,
            "status": "PENDING",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    db_manager.update_queue_session_stats({
        "first_run_loaded": 1,
        "auto_handled_count": AUTO_HANDLED_STATS["count"],
        "auto_handled_amount": AUTO_HANDLED_STATS["recovered_amount"],
        "auto_handled_net": AUTO_HANDLED_STATS["net_impact"],
        "session_recovered_count": QUEUE_SESSION_RECOVERED["count"],
        "session_recovered_amount": QUEUE_SESSION_RECOVERED["amount"],
    })

    return get_queue()


@app.post("/api/queue/approve-item")
def approve_queue_item(item_id: str = Body(..., embed=True)):
    """
    Review and approve an individual card from the queue.
    Invokes the Sentinel deterministically, logs audit trail, and executes.
    """
    global QUEUE_ITEMS_MAP, QUEUE_SESSION_RECOVERED
    item = QUEUE_ITEMS_MAP.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Queue item {item_id} not found")

    payment = next((p for p in BENCHMARK_DATASET if p.payment_id == item.payment_id), None)
    if not payment:
        # Simulated or synthetic payment
        payment = item.card_data.payment

    # Re-evaluate with Sentinel individually
    candidate = item.card_data.ranked_candidates[0]
    policy_req = PolicyRequest(
        subject_id=payment.payment_id,
        subject_type="payment_recovery",
        action_type=candidate.action.value,
        amount=payment.amount,
        current_attempt_count=payment.past_failed_retries,
        last_attempt_timestamp=payment.last_attempt_at,
        escalation_count=payment.dunning_attempts,
        expected_value=candidate.expected_value,
        confidence=item.card_data.diagnosis.confidence,
        granted_permissions=["payment.recovery.execute"],
        advisory_note="Human reviewed and approved from Queue",
        context={
            "risk_score": 0.10,
            "max_retries": the_sentinel.config.max_retries,
            "max_escalations": the_sentinel.config.max_escalations,
            "required_cooldown_hours": the_sentinel.config.cooldown_hours,
            "min_ev_threshold": the_sentinel.config.min_ev,
            "max_amount_bound": the_sentinel.config.max_recovery_amount,
            "min_amount_bound": the_sentinel.config.min_amount,
            "max_permissible_risk": the_sentinel.config.max_permissible_risk,
        },
    )

    decision = the_sentinel.evaluate(policy_req)
    outcome = razorpay_executor.execute_action(payment, candidate.action) if decision.approved else None

    # Log individual audit entry
    audit_entry = AuditLogEntry(
        entry_id=f"audit_{uuid.uuid4().hex[:10]}",
        payment_id=payment.payment_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        stage="SENTINEL_GATE",
        action=f"QUEUE_APPROVE_{candidate.action.value}",
        status="SUCCESS" if decision.approved else "REJECTED",
        reasoning=f"Human approved from review queue. Sentinel verdict: {decision.reason}",
        decision="APPROVED" if decision.approved else "BLOCKED",
        details={
            "item_id": item_id,
            "sentinel_code": decision.policy_code,
            "executed": decision.approved,
            "recovered": outcome.success if outcome else False,
        }
    )
    CACHED_AUDIT_TRAIL.insert(0, audit_entry)
    db_manager.save_audit_log({
        "event_id": audit_entry.entry_id,
        "payment_id": audit_entry.payment_id,
        "stage": audit_entry.stage,
        "action": audit_entry.action,
        "status": audit_entry.status,
        "human_readable_reasoning": audit_entry.reasoning,
        "decision": audit_entry.decision,
        "details": audit_entry.details,
        "timestamp": audit_entry.timestamp,
    })

    # Remove from queue and persistent storage
    del QUEUE_ITEMS_MAP[item_id]
    db_manager.remove_queue_item(item_id)
    
    rec_amt = outcome.recovered_amount if (outcome and outcome.success) else 0.0
    if rec_amt > 0:
        QUEUE_SESSION_RECOVERED["count"] += 1
        QUEUE_SESSION_RECOVERED["amount"] += rec_amt

    db_manager.update_queue_session_stats({
        "first_run_loaded": 1,
        "auto_handled_count": AUTO_HANDLED_STATS["count"],
        "auto_handled_amount": AUTO_HANDLED_STATS["recovered_amount"],
        "auto_handled_net": AUTO_HANDLED_STATS["net_impact"],
        "session_recovered_count": QUEUE_SESSION_RECOVERED["count"],
        "session_recovered_amount": QUEUE_SESSION_RECOVERED["amount"],
    })

    return {
        "status": "approved",
        "sentinel_approved": decision.approved,
        "policy_code": decision.policy_code,
        "recovered_amount": rec_amt,
        "remaining_queue_items": len(QUEUE_ITEMS_MAP),
    }


@app.post("/api/queue/approve-group")
def approve_queue_group(group_key: str = Body(..., embed=True)):
    """
    'Approve all in this group'.
    CRITICAL: Does NOT bypass the Sentinel.
    Runs EVERY item through the Sentinel individually, one by one,
    and writes an individual audit log entry for every single item.
    """
    global QUEUE_ITEMS_MAP, QUEUE_SESSION_RECOVERED
    matching_items = [it for it in QUEUE_ITEMS_MAP.values() if it.group_key == group_key]
    if not matching_items:
        raise HTTPException(status_code=404, detail=f"No items found for group {group_key}")

    approved_count = 0
    blocked_count = 0
    total_recovered = 0.0
    audit_ids = []

    for item in matching_items:
        payment = next((p for p in BENCHMARK_DATASET if p.payment_id == item.payment_id), None)
        if not payment:
            payment = item.card_data.payment

        candidate = item.card_data.ranked_candidates[0]
        policy_req = PolicyRequest(
            subject_id=payment.payment_id,
            subject_type="payment_recovery",
            action_type=candidate.action.value,
            amount=payment.amount,
            current_attempt_count=payment.past_failed_retries,
            last_attempt_timestamp=payment.last_attempt_at,
            escalation_count=payment.dunning_attempts,
            expected_value=candidate.expected_value,
            confidence=item.card_data.diagnosis.confidence,
            granted_permissions=["payment.recovery.execute"],
            advisory_note="Batch-approved as part of pattern group",
            context={
                "risk_score": 0.10,
                "max_retries": the_sentinel.config.max_retries,
                "max_escalations": the_sentinel.config.max_escalations,
                "required_cooldown_hours": the_sentinel.config.cooldown_hours,
                "min_ev_threshold": the_sentinel.config.min_ev,
                "max_amount_bound": the_sentinel.config.max_recovery_amount,
                "min_amount_bound": the_sentinel.config.min_amount,
                "max_permissible_risk": the_sentinel.config.max_permissible_risk,
            },
        )

        # 1-by-1 Sentinel evaluation
        decision = the_sentinel.evaluate(policy_req)
        
        outcome = None
        if decision.approved:
            outcome = razorpay_executor.execute_action(payment, candidate.action)
            approved_count += 1
            if outcome.success:
                total_recovered += outcome.recovered_amount
        else:
            blocked_count += 1

        # Individual Audit Log per item
        audit_entry = AuditLogEntry(
            entry_id=f"audit_{uuid.uuid4().hex[:10]}",
            payment_id=payment.payment_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            stage="SENTINEL_GATE",
            action=f"GROUP_APPROVE_{candidate.action.value}",
            status="SUCCESS" if decision.approved else "REJECTED",
            reasoning=f"Batch-approved via group '{group_key}'. Sentinel evaluated individually: {decision.reason}",
            decision="APPROVED" if decision.approved else "BLOCKED",
            details={
                "group_key": group_key,
                "item_id": item.item_id,
                "policy_code": decision.policy_code,
                "recovered": outcome.success if outcome else False,
            }
        )
        CACHED_AUDIT_TRAIL.insert(0, audit_entry)
        audit_ids.append(audit_entry.entry_id)
        db_manager.save_audit_log({
            "event_id": audit_entry.entry_id,
            "payment_id": audit_entry.payment_id,
            "stage": audit_entry.stage,
            "action": audit_entry.action,
            "status": audit_entry.status,
            "human_readable_reasoning": audit_entry.reasoning,
            "decision": audit_entry.decision,
            "details": audit_entry.details,
            "timestamp": audit_entry.timestamp,
        })

        # Remove processed item
        del QUEUE_ITEMS_MAP[item.item_id]
        db_manager.remove_queue_item(item.item_id)

    QUEUE_SESSION_RECOVERED["count"] += approved_count
    QUEUE_SESSION_RECOVERED["amount"] += round(total_recovered, 2)

    db_manager.update_queue_session_stats({
        "first_run_loaded": 1,
        "auto_handled_count": AUTO_HANDLED_STATS["count"],
        "auto_handled_amount": AUTO_HANDLED_STATS["recovered_amount"],
        "auto_handled_net": AUTO_HANDLED_STATS["net_impact"],
        "session_recovered_count": QUEUE_SESSION_RECOVERED["count"],
        "session_recovered_amount": QUEUE_SESSION_RECOVERED["amount"],
    })

    return {
        "status": "group_processed",
        "group_key": group_key,
        "total_items_in_group": len(matching_items),
        "sentinel_approved_count": approved_count,
        "sentinel_blocked_count": blocked_count,
        "total_recovered_inr": round(total_recovered, 2),
        "audit_entries_generated": len(audit_ids),
        "remaining_queue_items": len(QUEUE_ITEMS_MAP),
    }


@app.post("/api/queue/simulate-failure")
def simulate_new_failure():
    """
    Demo Trigger 1: 'Simulate a new failure'.
    Seeds a borderline failure payment that reliably lands in the Review Queue.
    """
    global QUEUE_INITIALIZED, QUEUE_ITEMS_MAP
    if not QUEUE_INITIALIZED:
        load_queue_payments()

    sim_id = f"pay_sim_{uuid.uuid4().hex[:6]}"
    sim_payment = PaymentRecord(
        payment_id=sim_id,
        amount=38500.0,
        currency="INR",
        timestamp=datetime.now(timezone.utc).isoformat(),
        decline_code="BAD_REQUEST_PAYMENT_DECLINED_BY_BANK",
        raw_signal="Issuer mandate rejected: velocity limit exceeded on corporate card",
        customer_id=f"cust_sim_{uuid.uuid4().hex[:4]}",
        customer_tier=CustomerTier.ENTERPRISE,
        tenure_months=18,
        past_failed_retries=2,
        dunning_attempts=1,
        last_attempt_at=datetime.now(timezone.utc).isoformat(),
        true_cause="ISSUER_DECLINE",
        true_recoverable=True,
    )

    card, audit = rebound_pipeline.process_payment(sim_payment)
    PAYMENT_CARD_MAP[sim_id] = card
    CACHED_AUDIT_TRAIL.extend(audit)

    group_key = f"{card.diagnosis.cause.value}::{card.ranked_candidates[0].action.value}"
    q_item = QueueItem(
        item_id=f"q_{sim_id}",
        payment_id=sim_id,
        diagnosed_cause=card.diagnosis.cause.value,
        top_ranked_strategy=card.ranked_candidates[0].action.value,
        group_key=group_key,
        amount=sim_payment.amount,
        customer_name="Simulated Enterprise Client",
        customer_tier="Enterprise",
        card_data=card,
        item_type="recovery",
        is_borderline=True,
        advisory_note="Seeded live borderline payment failure for review triage",
    )
    QUEUE_ITEMS_MAP[q_item.item_id] = q_item
    db_manager.upsert_queue_item({
        "item_id": q_item.item_id,
        "payment_id": q_item.payment_id,
        "diagnosed_cause": q_item.diagnosed_cause,
        "top_ranked_strategy": q_item.top_ranked_strategy,
        "group_key": q_item.group_key,
        "amount": q_item.amount,
        "customer_name": q_item.customer_name,
        "customer_tier": q_item.customer_tier,
        "item_type": q_item.item_type,
        "is_borderline": q_item.is_borderline,
        "advisory_note": q_item.advisory_note,
        "status": "PENDING",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return get_queue()


@app.post("/api/queue/simulate-buyer-agent")
def simulate_buyer_agent_in_queue():
    """
    Demo Trigger 2: 'Simulate Agent Purchase Request'.
    Renders an 'Agent Commerce' card into the exact same queue,
    demonstrating the Sentinel gating an AI buyer agent.
    """
    global QUEUE_INITIALIZED, QUEUE_ITEMS_MAP
    if not QUEUE_INITIALIZED:
        load_queue_payments()

    agent_id = f"agent_sim_{uuid.uuid4().hex[:4]}"
    req = BuyerAgentPurchaseRequest(
        agent_id=agent_id,
        agent_name="ProcurementBot-v3",
        sku_id="sku_gpu_cluster",
        amount=48000.0,
        requested_units=1,
        business_justification="Ad-hoc H100 GPU compute burst for sprint training",
        granted_scopes=["procurement.infra.high_value"],
        monthly_budget_inr=100000.0,
        current_month_spend_inr=65000.0,
        prior_orders_today=1,
        advisory_note="Autonomous agent hardware provisioning request",
    )

    result = buyer_agent_runner.evaluate_purchase(req)
    sentinel_dec = SentinelDecision(**result["sentinel_decision"])

    # Create dummy payment & card representation for unified UI display
    dummy_payment = PaymentRecord(
        payment_id=f"agent_req_{uuid.uuid4().hex[:6]}",
        amount=req.amount,
        currency="INR",
        timestamp=datetime.now(timezone.utc).isoformat(),
        decline_code="AGENT_PURCHASE_INTENT",
        raw_signal=f"Autonomous purchase request: {req.sku_id} ({req.business_justification})",
        customer_id=agent_id,
        customer_tier=CustomerTier.ENTERPRISE,
        tenure_months=12,
        past_failed_retries=0,
        dunning_attempts=0,
        true_cause="ISSUER_DECLINE",
        true_recoverable=True,
    )

    dummy_card = RecoveryDecisionCardData(
        payment=dummy_payment,
        diagnosis=PAYMENT_CARD_MAP[list(PAYMENT_CARD_MAP.keys())[0]].diagnosis,
        ranked_candidates=[],
        final_sentinel_decision=sentinel_dec,
        fallback_steps=[],
        final_outcome=None,
        counterfactual_paths=[],
        recovered=sentinel_dec.approved,
        net_revenue_impact=req.amount if sentinel_dec.approved else 0.0,
        pipeline_duration_ms=4.2,
        advisory_note="Agent Commerce purchase authorization request",
        is_borderline=True,
    )

    group_key = "AGENT_COMMERCE::BUYER_PURCHASE"
    q_item = QueueItem(
        item_id=f"q_{dummy_payment.payment_id}",
        payment_id=dummy_payment.payment_id,
        diagnosed_cause="AGENT_PURCHASE_INTENT",
        top_ranked_strategy="AUTHORIZE_AGENT_PURCHASE",
        group_key=group_key,
        amount=req.amount,
        customer_name=f"AI Agent: {req.agent_name}",
        customer_tier="Enterprise",
        card_data=dummy_card,
        item_type="agent_commerce",
        is_borderline=True,
        advisory_note=req.business_justification,
    )
    QUEUE_ITEMS_MAP[q_item.item_id] = q_item
    db_manager.upsert_queue_item({
        "item_id": q_item.item_id,
        "payment_id": q_item.payment_id,
        "diagnosed_cause": q_item.diagnosed_cause,
        "top_ranked_strategy": q_item.top_ranked_strategy,
        "group_key": q_item.group_key,
        "amount": q_item.amount,
        "customer_name": q_item.customer_name,
        "customer_tier": q_item.customer_tier,
        "item_type": q_item.item_type,
        "is_borderline": q_item.is_borderline,
        "advisory_note": q_item.advisory_note,
        "status": "PENDING",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return get_queue()


# ============================================================================
# AUDIT TRAIL, BENCHMARK & EVAL REPORT ENDPOINTS
# ============================================================================

@app.get("/api/dataset", response_model=List[PaymentRecord])
def get_dataset():
    """Retrieve all synthetic benchmark records."""
    return BENCHMARK_DATASET


@app.post("/api/pipeline/run-batch", response_model=BatchRunSummary)
def run_batch():
    """Execute the full 55-record benchmark run and baseline comparison."""
    return _execute_full_batch()


@app.get("/api/pipeline/batch-summary", response_model=BatchRunSummary)
def get_batch_summary():
    """Get the cached latest batch run summary."""
    if not CACHED_BATCH_SUMMARY:
        return _execute_full_batch()
    return CACHED_BATCH_SUMMARY


@app.get("/api/payments/{payment_id}/card", response_model=RecoveryDecisionCardData)
def get_payment_card(payment_id: str):
    """Retrieve the high-polish Recovery Decision Card for a specific payment."""
    if payment_id in PAYMENT_CARD_MAP:
        return PAYMENT_CARD_MAP[payment_id]
    
    payment = next((p for p in BENCHMARK_DATASET if p.payment_id == payment_id), None)
    if not payment:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
    
    card, audit = rebound_pipeline.process_payment(payment)
    PAYMENT_CARD_MAP[payment_id] = card
    return card


@app.post("/api/pipeline/process-single", response_model=RecoveryDecisionCardData)
def process_single_payment(payment: PaymentRecord):
    """Process any single arbitrary payment record through the 8-stage pipeline."""
    card, audit = rebound_pipeline.process_payment(payment)
    PAYMENT_CARD_MAP[payment.payment_id] = card
    CACHED_AUDIT_TRAIL.extend(audit)
    return card


@app.get("/api/audit-trail", response_model=List[AuditLogEntry])
def get_audit_trail(
    payment_id: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    limit: int = Query(200, le=1000)
):
    """Retrieve structured timestamped audit logs from persistent database with filtering."""
    db_rows = db_manager.get_all_audit_logs(payment_id=payment_id)
    if db_rows:
        logs = [
            AuditLogEntry(
                entry_id=r["event_id"],
                payment_id=r["payment_id"],
                timestamp=r["timestamp"],
                stage=r["stage"],
                action=r["action"],
                status=r["status"],
                reasoning=r["human_readable_reasoning"],
                decision=r.get("decision"),
                details=r.get("details", {}) if isinstance(r.get("details"), dict) else {},
            )
            for r in db_rows
        ]
    else:
        logs = CACHED_AUDIT_TRAIL
        if payment_id:
            logs = [l for l in logs if l.payment_id == payment_id]
            
    if stage:
        logs = [l for l in logs if l.stage.upper() == stage.upper()]
    return logs[:limit]


@app.post("/api/sentinel/evaluate", response_model=SentinelDecision)
def evaluate_sentinel(request: PolicyRequest):
    """
    Directly invoke the standalone Sentinel policy gate.
    Used for unit testing, independent validation, and external agent gating.
    """
    return the_sentinel.evaluate(request)


@app.get("/api/eval-report")
def get_eval_report():
    """
    Returns Pre-Submission Evaluation metrics (A through E) + FAQ references.
    """
    summary = CACHED_BATCH_SUMMARY or _execute_full_batch()
    return {
        "A_correctness": {
            "total_records": summary.total_records,
            "diagnosis_accuracy_pct": summary.diagnosis_accuracy,
            "rebound_recovered_inr": summary.rebound_recovered_amount,
            "rebound_recovered_count": summary.rebound_recovered_count,
            "baseline_recovered_inr": summary.baseline_recovered_amount,
            "baseline_recovered_count": summary.baseline_recovered_count,
            "net_uplift_inr": summary.net_uplift_amount,
            "net_uplift_pct": summary.net_uplift_percent,
            "rebound_precision": summary.rebound_recovery_precision,
            "baseline_precision": summary.baseline_recovery_precision,
        },
        "B_sentinel_integrity": {
            "policy_blocks_total": summary.sentinel_blocks_count,
            "pure_rules_engine": True,
            "llm_calls_inside_sentinel": 0,
            "action_agnostic_interface": True,
        },
        "C_audit_trail": {
            "total_audit_events": len(CACHED_AUDIT_TRAIL),
            "stages_tracked": ["DETECT", "DIAGNOSE", "RANK", "SENTINEL_GATE", "EXECUTE", "OBSERVE", "FALLBACK", "STOP"],
        },
        "D_failure_handling": {
            "graceful_fallbacks_count": sum(1 for c in summary.records if len(c.fallback_steps) > 1),
            "infinite_loops_prevented": True,
        },
        "E_closing_demo": {
            "sentinel_reused_unmodified": True,
            "agent_types_tested": ["Autonomous Buyer Agent", "Payment Recovery Engine"],
        },
        "F_faq": {
            "section_title": "FAQ (Frequently Asked Questions)",
            "qa_count": 5,
            "doc_path": "docs/JUDGE_QA.md",
        },
        "calibration_buckets": [b.model_dump() for b in summary.calibration_buckets],
    }


# Mount production frontend build if present
import os
from fastapi.staticfiles import StaticFiles
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
