export type FailureCause = 
  | 'INSUFFICIENT_FUNDS'
  | 'CARD_EXPIRED'
  | 'ISSUER_DECLINE'
  | 'RISK_BLOCK'
  | 'BANK_DOWNTIME';

export type RecoveryAction = 
  | 'RETRY_NOW'
  | 'RETRY_LATER'
  | 'NOTIFY_CUSTOMER'
  | 'OFFER_ALTERNATE_PAYMENT_METHOD'
  | 'PROMPT_CARD_UPDATE';

export type CustomerTier = 'Enterprise' | 'Growth_SMB' | 'Pro_Consumer' | 'Free_Trial';

export interface PaymentRecord {
  payment_id: string;
  subscription_id: string;
  amount: number;
  currency: string;
  timestamp: string;
  decline_code: string;
  raw_signal: string;
  customer_id: string;
  customer_name: string;
  customer_tier: CustomerTier;
  tenure_months: number;
  past_failed_retries: number;
  dunning_attempts: number;
  last_attempt_at: string | null;
  preferred_payment_method: string;
  true_cause: FailureCause;
  true_recoverable: boolean;
}

export interface DiagnosisResult {
  payment_id: string;
  cause: FailureCause;
  confidence: number;
  reasoning: string;
  key_signals: string[];
}

export interface StrategyCandidate {
  action: RecoveryAction;
  success_probability: number;
  expected_value: number;
  estimated_cost: number;
  rationale: string;
  recommended_delay_hours: number;
  formula_applied?: string;
}

export interface SentinelDecision {
  approved: boolean;
  reason: string;
  policy_code: string;
  confidence: number;
  expected_value: number;
  constraints_evaluated: Record<string, string>;
}

export interface ExecutionOutcome {
  payment_id: string;
  action: RecoveryAction;
  success: boolean;
  transaction_id: string | null;
  recovered_amount: number;
  gateway_code: string;
  gateway_message: string;
  timestamp: string;
  execution_backend: string;
}

export interface FallbackStep {
  step_number: number;
  candidate_action: RecoveryAction;
  expected_value: number;
  sentinel_approved: boolean;
  sentinel_decision: SentinelDecision;
  execution_attempted: boolean;
  execution_success: boolean | null;
  execution_details: ExecutionOutcome | null;
  notes: string;
}

export interface CounterfactualMetric {
  action: RecoveryAction;
  expected_value: number;
  success_probability: number;
  status: string;
  rationale: string;
}

export interface RecoveryDecisionCardData {
  payment: PaymentRecord;
  diagnosis: DiagnosisResult;
  ranked_candidates: StrategyCandidate[];
  final_sentinel_decision: SentinelDecision;
  fallback_steps: FallbackStep[];
  final_outcome: ExecutionOutcome | null;
  counterfactual_paths: CounterfactualMetric[];
  recovered: boolean;
  net_revenue_impact: number;
  pipeline_duration_ms: number;
  advisory_note?: string | null;
  is_borderline?: boolean;
}

export interface AuditLogEntry {
  entry_id: string;
  payment_id: string;
  timestamp: string;
  stage: string;
  action: string;
  status: string;
  reasoning?: string;
  decision?: string | null;
  details?: Record<string, any>;
}

export interface CalibrationBucket {
  bucket_range: string;
  predicted_min: number;
  predicted_max: number;
  predictions_count: number;
  actual_recovered_count: number;
  actual_recovery_rate: number;
}

export interface BatchRunSummary {
  total_records: number;
  rebound_recovered_amount: number;
  rebound_recovered_count: number;
  rebound_attempted_count: number;
  rebound_recovery_precision: number;
  rebound_total_execution_costs: number;
  rebound_net_recovered: number;
  
  baseline_recovered_amount: number;
  baseline_recovered_count: number;
  baseline_attempted_count: number;
  baseline_recovery_precision: number;
  baseline_total_execution_costs: number;
  baseline_net_recovered: number;

  net_uplift_amount: number;
  net_uplift_percent: number;
  ineffective_retries_prevented: number;
  diagnosis_accuracy: number;
  sentinel_blocks_count: number;
  
  records: RecoveryDecisionCardData[];
  audit_logs: AuditLogEntry[];
  calibration_buckets?: CalibrationBucket[];
}

export interface MerchantPolicyConfig {
  max_retries: number;
  cooldown_hours: number;
  max_escalations: number;
  min_ev: number;
  max_recovery_amount: number;
  min_amount: number;
  max_permissible_risk: number;
}

export interface MerchantCatalogItem {
  sku: string;
  name: string;
  price: number;
  in_stock: boolean;
  requires_permission?: string;
  category?: string;
  description?: string;
}

// Legacy alias
export type BuyerCatalogItem = MerchantCatalogItem;

export interface QueueItem {
  item_id: string;
  payment_id: string;
  diagnosed_cause: string;
  top_ranked_strategy: string;
  group_key: string;
  amount: number;
  customer_name: string;
  customer_tier: string;
  card_data: RecoveryDecisionCardData;
  item_type: string;
  advisory_note?: string | null;
  is_borderline: boolean;
}

export interface QueueGroup {
  group_key: string;
  diagnosed_cause: string;
  top_ranked_strategy: string;
  item_count: number;
  total_amount: number;
  item_type: string;
  label: string;
  items: QueueItem[];
}
