"""
Pydantic Schemas for Rebound — AI Revenue Recovery Agent
Defines data models for the 8-stage pipeline, the Sentinel policy gate,
merchant policy configuration, catalog store, and queue management.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class FailureCause(str, Enum):
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    CARD_EXPIRED = "CARD_EXPIRED"
    ISSUER_DECLINE = "ISSUER_DECLINE"
    RISK_BLOCK = "RISK_BLOCK"
    BANK_DOWNTIME = "BANK_DOWNTIME"


class RecoveryAction(str, Enum):
    RETRY_NOW = "RETRY_NOW"
    RETRY_LATER = "RETRY_LATER"
    NOTIFY_CUSTOMER = "NOTIFY_CUSTOMER"
    OFFER_ALTERNATE_PAYMENT_METHOD = "OFFER_ALTERNATE_PAYMENT_METHOD"
    PROMPT_CARD_UPDATE = "PROMPT_CARD_UPDATE"


class CustomerTier(str, Enum):
    ENTERPRISE = "Enterprise"
    GROWTH_SMB = "Growth_SMB"
    PRO_CONSUMER = "Pro_Consumer"
    FREE_TRIAL = "Free_Trial"


class PaymentRecord(BaseModel):
    payment_id: str
    subscription_id: str
    amount: float
    currency: str = "INR"
    timestamp: str
    decline_code: str
    raw_signal: str
    customer_id: str
    customer_name: str
    customer_tier: CustomerTier
    tenure_months: int
    past_failed_retries: int = 0
    dunning_attempts: int = 0
    last_attempt_at: Optional[str] = None
    preferred_payment_method: str = "card_recurring"
    true_cause: FailureCause
    true_recoverable: bool


class DiagnosisResult(BaseModel):
    payment_id: str
    cause: FailureCause
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    key_signals: List[str] = []
    provider: str = "gemini"
    model_name: Optional[str] = None
    is_llm_derived: bool = False
    raw_model_response: Optional[str] = None


class StrategyCandidate(BaseModel):
    action: RecoveryAction
    success_probability: float = Field(ge=0.0, le=1.0)
    expected_value: float
    estimated_cost: float
    rationale: str
    recommended_delay_hours: int = 0
    formula_applied: str = "expected_value = (recovery_probability * amount) - cost_of_action"
    is_llm_derived: bool = False
    raw_model_response: Optional[str] = None


class RankingResult(BaseModel):
    payment_id: str
    candidates: List[StrategyCandidate]
    top_action: RecoveryAction


class PolicyRequest(BaseModel):
    """
    Action-agnostic input for the Sentinel.
    Can evaluate both recovery actions and simulated buyer agent purchase requests.
    Notice: advisory_note is an optional signal provided for human audit,
    and is structurally excluded from the Sentinel's deterministic gate logic.
    """
    subject_id: str
    subject_type: str = "payment_recovery"  # "payment_recovery" or "buyer_agent_purchase"
    action_type: str
    amount: float
    current_attempt_count: int = 0
    last_attempt_timestamp: Optional[str] = None
    escalation_count: int = 0
    expected_value: float = 0.0
    confidence: float = 1.0
    granted_permissions: List[str] = []
    advisory_note: Optional[str] = None
    context: Dict[str, Any] = {}


class SentinelDecision(BaseModel):
    approved: bool
    reason: str
    policy_code: str
    confidence: float
    expected_value: float
    constraints_evaluated: Dict[str, Any]


class ExecutionOutcome(BaseModel):
    payment_id: str
    action: RecoveryAction
    success: bool
    transaction_id: Optional[str] = None
    recovered_amount: float = 0.0
    gateway_code: str
    gateway_message: str
    timestamp: str
    execution_backend: str  # "razorpay_test_mode_api" or "razorpay_test_stub"
    razorpay_order_id: Optional[str] = None
    razorpay_payment_link: Optional[str] = None
    razorpay_signature: Optional[str] = None
    signature_verified: Optional[bool] = None
    test_instrument: Optional[str] = None


class FallbackStep(BaseModel):
    step_number: int
    candidate_action: RecoveryAction
    expected_value: float
    sentinel_approved: bool
    sentinel_decision: SentinelDecision
    execution_attempted: bool = False
    execution_success: Optional[bool] = None
    execution_details: Optional[ExecutionOutcome] = None
    notes: str


class CounterfactualMetric(BaseModel):
    action: RecoveryAction
    expected_value: float
    success_probability: float
    status: str  # "executed", "gated_by_sentinel", "unreached_fallback", "rejected"
    rationale: str


class RecoveryDecisionCardData(BaseModel):
    payment: PaymentRecord
    diagnosis: DiagnosisResult
    ranked_candidates: List[StrategyCandidate]
    final_sentinel_decision: SentinelDecision
    fallback_steps: List[FallbackStep]
    final_outcome: Optional[ExecutionOutcome] = None
    counterfactual_paths: List[CounterfactualMetric]
    recovered: bool
    net_revenue_impact: float
    pipeline_duration_ms: float
    advisory_note: Optional[str] = None
    is_borderline: bool = False


class AuditLogEntry(BaseModel):
    entry_id: str
    payment_id: str
    timestamp: str
    stage: str  # DETECT, DIAGNOSE, RANK, SENTINEL_GATE, EXECUTE, OBSERVE, FALLBACK, STOP
    action: str
    status: str  # SUCCESS, REJECTED, FAILED, INFO
    reasoning: str = ""
    decision: Optional[str] = None
    details: Dict[str, Any] = {}


class CalibrationBucket(BaseModel):
    bucket_range: str  # e.g. "0-20%", "20-40%"
    predicted_min: float
    predicted_max: float
    predictions_count: int
    actual_recovered_count: int
    actual_recovery_rate: float


class BatchRunSummary(BaseModel):
    total_records: int
    rebound_recovered_amount: float
    rebound_recovered_count: int
    rebound_attempted_count: int
    rebound_recovery_precision: float
    rebound_total_execution_costs: float
    rebound_net_recovered: float
    
    baseline_recovered_amount: float
    baseline_recovered_count: int
    baseline_attempted_count: int
    baseline_recovery_precision: float
    baseline_total_execution_costs: float
    baseline_net_recovered: float

    net_uplift_amount: float
    net_uplift_percent: float
    ineffective_retries_prevented: int
    diagnosis_accuracy: float
    sentinel_blocks_count: int
    
    records: List[RecoveryDecisionCardData]
    audit_logs: List[AuditLogEntry]
    calibration_buckets: List[CalibrationBucket] = []


# --- CHANGE 6: Merchant Policy Configuration ---
class MerchantPolicyConfig(BaseModel):
    max_retries: int = Field(default=3, ge=0, le=10, description="Max allowed payment retry attempts")
    cooldown_hours: float = Field(default=4.0, ge=0.0, le=168.0, description="Mandatory cooldown between retries in hours")
    max_escalations: int = Field(default=2, ge=0, le=10, description="Max customer dunning alerts allowed")
    min_ev: float = Field(default=0.01, ge=0.0, le=10000.0, description="Minimum expected value cutoff in INR")
    max_recovery_amount: float = Field(default=250000.0, ge=1.0, le=10000000.0, description="Ceiling on auto-recovery amount")
    min_amount: float = Field(default=1.0, ge=0.1, le=1000.0, description="Minimum transaction amount in INR")
    max_permissible_risk: float = Field(default=0.70, ge=0.0, le=1.0, description="Max allowed risk score before hard block")


# --- CHANGE 7: Merchant Catalog Item Schema ---
class MerchantCatalogItem(BaseModel):
    sku: str
    name: str
    price: float = Field(ge=0.0)
    in_stock: bool = True
    requires_permission: Optional[str] = "procurement.saas.basic"
    category: Optional[str] = "General"


# Legacy alias for backward compatibility
BuyerCatalogItem = MerchantCatalogItem


# --- CHANGE 5: Parsed Buyer Intent Schema ---
class ParsedBuyerIntent(BaseModel):
    sku: str
    requested_amount: float
    agent_permission_scope: List[str]
    advisory_note: Optional[str] = None
    parsing_confidence: float = 1.0
    raw_intent: str = ""
    is_llm_derived: bool = False
    provider: str = "gemini"


class BuyerAgentPurchaseRequest(BaseModel):
    agent_id: str
    agent_name: str
    sku_id: str
    amount: float
    requested_units: int
    business_justification: str
    granted_scopes: List[str]
    monthly_budget_inr: float
    current_month_spend_inr: float
    prior_orders_today: int
    advisory_note: Optional[str] = None


# --- CHANGE 1: Queue & Smart Grouping Schemas ---
class QueueItem(BaseModel):
    item_id: str
    payment_id: str
    diagnosed_cause: str
    top_ranked_strategy: str
    group_key: str
    amount: float
    customer_name: str
    customer_tier: str
    card_data: RecoveryDecisionCardData
    item_type: str = "recovery"  # "recovery" or "agent_commerce"
    advisory_note: Optional[str] = None
    is_borderline: bool = True


class QueueGroup(BaseModel):
    group_key: str
    diagnosed_cause: str
    top_ranked_strategy: str
    item_count: int
    total_amount: float
    item_type: str = "recovery"
    label: str
    items: List[QueueItem]


# --- Subscription Provisioning Schemas ---
class ProvisionSubscriptionRequest(BaseModel):
    internal_customer_id: str
    customer_name: str
    customer_email: str
    customer_contact: str = "+919876543210"
    plan_name: str = "Starter"


class ProvisionSubscriptionResponse(BaseModel):
    success: bool
    internal_customer_id: str
    customer_id: str
    subscription_id: str
    plan: str
    plan_id: str
    amount_inr: float
    status: str
    authorization_url: str
    created_at: str

