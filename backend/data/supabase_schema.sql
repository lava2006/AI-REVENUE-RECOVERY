-- ============================================================================
-- Rebound — Supabase PostgreSQL Schema
-- Run this script in the Supabase SQL Editor to initialize all tables
-- ============================================================================

-- 1. Merchant Policy Configuration Table
CREATE TABLE IF NOT EXISTS policy_config (
    id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    max_retries INT NOT NULL DEFAULT 3,
    cooldown_hours NUMERIC NOT NULL DEFAULT 4.0,
    min_ev NUMERIC NOT NULL DEFAULT 0.0,
    max_recovery_amount NUMERIC NOT NULL DEFAULT 500000.0,
    min_amount NUMERIC NOT NULL DEFAULT 1.0,
    max_escalations INT NOT NULL DEFAULT 2,
    max_permissible_risk NUMERIC NOT NULL DEFAULT 0.70,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Merchant Catalog Table
CREATE TABLE IF NOT EXISTS merchant_catalog (
    sku TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    price NUMERIC NOT NULL,
    in_stock BOOLEAN NOT NULL DEFAULT TRUE,
    category TEXT NOT NULL,
    requires_permission TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Payments Table
CREATE TABLE IF NOT EXISTS payments (
    payment_id TEXT PRIMARY KEY,
    subscription_id TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    timestamp TIMESTAMPTZ NOT NULL,
    decline_code TEXT NOT NULL,
    raw_signal TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    customer_tier TEXT NOT NULL,
    tenure_months INT NOT NULL,
    past_failed_retries INT NOT NULL,
    dunning_attempts INT NOT NULL,
    last_attempt_at TIMESTAMPTZ,
    preferred_payment_method TEXT NOT NULL,
    true_cause TEXT NOT NULL,
    true_recoverable BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Diagnoses Table
CREATE TABLE IF NOT EXISTS diagnoses (
    payment_id TEXT PRIMARY KEY REFERENCES payments(payment_id) ON DELETE CASCADE,
    diagnosed_cause TEXT NOT NULL,
    confidence NUMERIC NOT NULL,
    reasoning TEXT NOT NULL,
    key_signals JSONB NOT NULL DEFAULT '[]',
    provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    is_llm_derived BOOLEAN NOT NULL,
    raw_model_response TEXT,
    diagnosed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Strategies Table
CREATE TABLE IF NOT EXISTS strategies (
    id BIGSERIAL PRIMARY KEY,
    payment_id TEXT NOT NULL REFERENCES payments(payment_id) ON DELETE CASCADE,
    strategy_name TEXT NOT NULL,
    rank INT NOT NULL,
    probability NUMERIC NOT NULL,
    expected_value NUMERIC NOT NULL,
    cost NUMERIC NOT NULL,
    reasoning_text TEXT NOT NULL,
    recommended_delay_hours INT NOT NULL DEFAULT 0,
    formula_applied TEXT NOT NULL
);

-- 6. Sentinel Gate Decisions Table
CREATE TABLE IF NOT EXISTS gate_decisions (
    id BIGSERIAL PRIMARY KEY,
    payment_id TEXT NOT NULL REFERENCES payments(payment_id) ON DELETE CASCADE,
    strategy_chosen TEXT NOT NULL,
    approved BOOLEAN NOT NULL,
    policy_code TEXT NOT NULL,
    reason TEXT NOT NULL,
    confidence NUMERIC NOT NULL,
    expected_value NUMERIC NOT NULL,
    constraints_evaluated JSONB NOT NULL DEFAULT '{}',
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. Gateway Execution Outcomes Table
CREATE TABLE IF NOT EXISTS outcomes (
    id BIGSERIAL PRIMARY KEY,
    payment_id TEXT NOT NULL REFERENCES payments(payment_id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    final_status TEXT NOT NULL,
    recovered_amount NUMERIC NOT NULL DEFAULT 0.0,
    transaction_id TEXT,
    gateway_code TEXT NOT NULL,
    gateway_message TEXT NOT NULL,
    execution_backend TEXT NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. Persistent Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_log (
    event_id TEXT PRIMARY KEY,
    payment_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    human_readable_reasoning TEXT NOT NULL,
    decision TEXT,
    details JSONB NOT NULL DEFAULT '{}',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_log_payment_id ON audit_log(payment_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp DESC);

-- 9. Review Queue Items Table
CREATE TABLE IF NOT EXISTS queue_items (
    item_id TEXT PRIMARY KEY,
    payment_id TEXT NOT NULL REFERENCES payments(payment_id) ON DELETE CASCADE,
    diagnosed_cause TEXT NOT NULL,
    top_ranked_strategy TEXT NOT NULL,
    group_key TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    customer_name TEXT NOT NULL,
    customer_tier TEXT NOT NULL,
    item_type TEXT NOT NULL,
    is_borderline BOOLEAN NOT NULL,
    advisory_note TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 10. Queue Session Stats Table (Preserves recovery totals across server restarts)
CREATE TABLE IF NOT EXISTS queue_session_stats (
    id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    first_run_loaded BOOLEAN NOT NULL DEFAULT FALSE,
    auto_handled_count INT NOT NULL DEFAULT 0,
    auto_handled_amount NUMERIC NOT NULL DEFAULT 0.0,
    auto_handled_net NUMERIC NOT NULL DEFAULT 0.0,
    session_recovered_count INT NOT NULL DEFAULT 0,
    session_recovered_amount NUMERIC NOT NULL DEFAULT 0.0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Insert default rows if not present
INSERT INTO policy_config (id, max_retries, cooldown_hours, min_ev, max_recovery_amount, min_amount, max_escalations, max_permissible_risk)
VALUES (1, 3, 4.0, 0.0, 500000.0, 1.0, 2, 0.70)
ON CONFLICT (id) DO NOTHING;

INSERT INTO queue_session_stats (id, first_run_loaded, auto_handled_count, auto_handled_amount, auto_handled_net, session_recovered_count, session_recovered_amount)
VALUES (1, FALSE, 0, 0.0, 0.0, 0, 0.0)
ON CONFLICT (id) DO NOTHING;
