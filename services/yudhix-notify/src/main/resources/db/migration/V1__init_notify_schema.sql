-- Notification Rules (Crisis alerts, SLA thresholds)
CREATE TABLE IF NOT EXISTS notification_rule (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    name VARCHAR(150) NOT NULL,
    rule_type VARCHAR(50) NOT NULL, -- CRISIS_SPIKE, P1_ALERT, SLA_BREACH
    threshold_value NUMERIC(5,2),
    channel VARCHAR(50) NOT NULL, -- EMAIL, WEBHOOK, SLACK
    target_destination VARCHAR(255) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Notification Dispatch History
CREATE TABLE IF NOT EXISTS notification_log (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    rule_id UUID,
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    recipient VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'SENT', -- SENT, FAILED
    error_message TEXT,
    dispatched_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notify_rule_tenant ON notification_rule(tenant_id, active);
CREATE INDEX IF NOT EXISTS idx_notify_log_tenant ON notification_log(tenant_id, dispatched_at);
