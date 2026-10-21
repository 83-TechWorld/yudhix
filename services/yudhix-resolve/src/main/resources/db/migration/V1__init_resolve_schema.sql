-- Brand-Safe Reply Workflow Table
CREATE TABLE IF NOT EXISTS reply (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    comment_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    reply_text TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'DRAFT',
    author_id UUID NOT NULL,
    approver_id UUID,
    sla_due_at TIMESTAMPTZ NOT NULL,
    posted_at TIMESTAMPTZ,
    platform_reply_id VARCHAR(255),
    rejection_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Pre-approved brand response templates
CREATE TABLE IF NOT EXISTS reply_template (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    variables JSONB NOT NULL DEFAULT '[]',
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Multi-stage Approval Audit Trail
CREATE TABLE IF NOT EXISTS approval_step (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    reply_id UUID NOT NULL REFERENCES reply(id) ON DELETE CASCADE,
    step_name VARCHAR(100) NOT NULL,
    reviewer_id UUID NOT NULL,
    decision VARCHAR(50) NOT NULL,
    comments TEXT,
    action_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reply_tenant_status ON reply(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_reply_comment ON reply(tenant_id, comment_id);
CREATE INDEX IF NOT EXISTS idx_reply_sla ON reply(tenant_id, sla_due_at) WHERE status IN ('DRAFT', 'IN_REVIEW');
