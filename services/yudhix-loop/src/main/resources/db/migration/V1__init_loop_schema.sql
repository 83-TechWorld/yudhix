-- Turnaround Evaluation Tracking (Closed Feedback Loop)
CREATE TABLE IF NOT EXISTS reply_outcome (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    reply_id UUID NOT NULL,
    comment_id UUID NOT NULL,
    initial_sentiment VARCHAR(20) NOT NULL,
    checkpoint_24h_sentiment VARCHAR(20),
    checkpoint_72h_sentiment VARCHAR(20),
    checkpoint_7d_sentiment VARCHAR(20),
    turned_around BOOLEAN NOT NULL DEFAULT false,
    follow_up_comment_id VARCHAR(255),
    notes TEXT,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Human Reviewer Feedback for AI Retraining/Calibration
CREATE TABLE IF NOT EXISTS label_feedback (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    comment_id UUID NOT NULL,
    reviewer_id UUID NOT NULL,
    original_sentiment VARCHAR(20) NOT NULL,
    corrected_sentiment VARCHAR(20) NOT NULL,
    original_toxic BOOLEAN NOT NULL DEFAULT false,
    corrected_toxic BOOLEAN NOT NULL DEFAULT false,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reply_outcome_tenant ON reply_outcome(tenant_id, reply_id);
CREATE INDEX IF NOT EXISTS idx_reply_outcome_turnaround ON reply_outcome(tenant_id, turned_around);
CREATE INDEX IF NOT EXISTS idx_label_feedback_tenant ON label_feedback(tenant_id, comment_id);
