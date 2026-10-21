-- Subscription Plans
CREATE TABLE IF NOT EXISTS plan (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    monthly_price NUMERIC(10,2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    comment_quota INT NOT NULL,
    llm_quota INT NOT NULL,
    reply_quota INT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT true
);

-- Seed Default Plans
INSERT INTO plan (id, name, monthly_price, currency, comment_quota, llm_quota, reply_quota)
VALUES
    ('STARTER', 'Starter Tier', 99.00, 'USD', 10000, 2000, 500),
    ('PROFESSIONAL', 'Professional Tier', 499.00, 'USD', 100000, 25000, 5000),
    ('ENTERPRISE', 'Enterprise Unlimited', 1999.00, 'USD', -1, -1, -1)
ON CONFLICT (id) DO NOTHING;

-- Active Tenant Subscriptions
CREATE TABLE IF NOT EXISTS subscription (
    tenant_id UUID PRIMARY KEY,
    plan_id VARCHAR(50) NOT NULL REFERENCES plan(id),
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end TIMESTAMPTZ NOT NULL,
    payment_method_id VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Idempotent Usage Events (comments_ingested, comments_llm_analyzed, replies_posted)
CREATE TABLE IF NOT EXISTS usage_event (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    idempotency_key VARCHAR(120) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, metric_type, idempotency_key)
);

-- Monthly Generated Invoices
CREATE TABLE IF NOT EXISTS invoice (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    billing_period VARCHAR(20) NOT NULL,
    subtotal NUMERIC(10,2) NOT NULL,
    tax NUMERIC(10,2) NOT NULL DEFAULT 0.0,
    total NUMERIC(10,2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    status VARCHAR(50) NOT NULL DEFAULT 'DRAFT', -- DRAFT, ISSUED, PAID, FAILED
    payment_gateway_ref VARCHAR(100),
    issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    paid_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_usage_event_tenant_metric ON usage_event(tenant_id, metric_type, recorded_at);
CREATE INDEX IF NOT EXISTS idx_invoice_tenant_period ON invoice(tenant_id, billing_period);
