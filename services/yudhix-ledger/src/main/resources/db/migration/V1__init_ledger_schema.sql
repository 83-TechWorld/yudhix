-- Append-only, cryptographic hash-chained audit log
CREATE TABLE IF NOT EXISTS audit_event (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor_id VARCHAR(100),
    actor_type VARCHAR(50) NOT NULL, -- USER, SYSTEM, SERVICE
    action VARCHAR(100) NOT NULL, -- REPLY_APPROVED, TENANT_ONBOARDED, DSR_COMPLETED, POLICY_ACCEPTED
    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    before_state JSONB,
    after_state JSONB,
    ip_hash VARCHAR(100),
    user_agent TEXT,
    prev_hash VARCHAR(64) NOT NULL,
    row_hash VARCHAR(64) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_tenant_id ON audit_event(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_occurred_at ON audit_event(occurred_at);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_event(action);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_event(entity_type, entity_id);
