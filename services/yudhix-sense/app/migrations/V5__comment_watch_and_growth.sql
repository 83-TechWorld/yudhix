-- =============================================================================
-- yudhix-sense V5: fetch new comments, the comment-check schedule, and product ideas.
-- Idempotent: applied on every startup.
-- =============================================================================

-- Jobs are either a full analysis or a quick "fetch new comments" check.
ALTER TABLE video_analysis_job ADD COLUMN IF NOT EXISTS kind    VARCHAR(20) NOT NULL DEFAULT 'ANALYZE';  -- ANALYZE | COMMENTS
ALTER TABLE video_analysis_job ADD COLUMN IF NOT EXISTS trigger VARCHAR(20) NOT NULL DEFAULT 'USER';     -- USER | SCHEDULE
ALTER TABLE video_analysis_job ADD COLUMN IF NOT EXISTS result  JSONB;
CREATE INDEX IF NOT EXISTS idx_video_job_video ON video_analysis_job (tenant_id, video_id, created_at DESC);

-- When this video's comments were last checked (by a full analysis, the button or the schedule).
ALTER TABLE video_truth_analysis ADD COLUMN IF NOT EXISTS comments_checked_at TIMESTAMPTZ;
UPDATE video_truth_analysis SET comments_checked_at = COALESCE(analyzed_at, created_at) WHERE comments_checked_at IS NULL;

-- Per-workspace schedule for checking analyzed videos for new comments. No row = defaults (on, every 6 hours).
CREATE TABLE IF NOT EXISTS comment_watch (
    tenant_id      UUID PRIMARY KEY,
    enabled        BOOLEAN     NOT NULL DEFAULT true,
    interval_hours INTEGER     NOT NULL DEFAULT 6 CHECK (interval_hours BETWEEN 1 AND 168),
    updated_by     VARCHAR(100),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Product ideas: feature requests from comments, grouped by theme, managed by the product team.
CREATE TABLE IF NOT EXISTS product_idea (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID         NOT NULL,
    theme_key   VARCHAR(120) NOT NULL,              -- normalized title, used to group similar requests
    title       VARCHAR(200) NOT NULL,
    topic       VARCHAR(30),                        -- PRICE, FEATURES, ... (app/truth/audience.py TOPICS)
    status      VARCHAR(20)  NOT NULL DEFAULT 'NEW', -- NEW | REVIEWING | PLANNED | SHIPPED | DECLINED
    note        TEXT,
    updated_by  VARCHAR(100),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, theme_key)
);
CREATE INDEX IF NOT EXISTS idx_product_idea_tenant ON product_idea (tenant_id, status);

CREATE TABLE IF NOT EXISTS product_idea_comment (
    tenant_id  UUID NOT NULL,
    idea_id    UUID NOT NULL REFERENCES product_idea(id) ON DELETE CASCADE,
    comment_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (idea_id, comment_id)
);
CREATE INDEX IF NOT EXISTS idx_idea_comment_comment ON product_idea_comment (tenant_id, comment_id);
