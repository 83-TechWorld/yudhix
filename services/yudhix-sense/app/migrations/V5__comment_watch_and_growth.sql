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

-- Claims are checked against the knowledge base at analysis time. When facts are added or removed,
-- videos are flagged so the UI can offer "Re-check claims" (fact-check only, no new transcript).
ALTER TABLE video_truth_analysis ADD COLUMN IF NOT EXISTS facts_stale BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE video_truth_analysis ADD COLUMN IF NOT EXISTS facts_checked_at TIMESTAMPTZ;

-- AI provider per workspace (Settings > AI). The key is encrypted (Fernet); only its last 4 characters are shown.
CREATE TABLE IF NOT EXISTS ai_setting (
    tenant_id    UUID PRIMARY KEY,
    mode         VARCHAR(10)  NOT NULL DEFAULT 'LOCAL',   -- LOCAL | CLOUD (CLOUD only with a VALID key)
    provider     VARCHAR(30),
    model        VARCHAR(200),
    embed_model  VARCHAR(200),
    base_url     VARCHAR(500),
    api_key_enc  TEXT,
    key_hint     VARCHAR(12),
    status       VARCHAR(12)  NOT NULL DEFAULT 'UNTESTED', -- UNTESTED | VALID | INVALID
    last_error   TEXT,
    validated_at TIMESTAMPTZ,
    updated_by   VARCHAR(100),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Anti-hallucination: what the model quoted, and claims a person should look at.
ALTER TABLE video_claim ADD COLUMN IF NOT EXISTS source_quote  TEXT;
ALTER TABLE video_claim ADD COLUMN IF NOT EXISTS needs_review  BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE video_claim ADD COLUMN IF NOT EXISTS review_reason TEXT;
ALTER TABLE video_claim ADD COLUMN IF NOT EXISTS reviewed_by   VARCHAR(100);
ALTER TABLE video_claim ADD COLUMN IF NOT EXISTS reviewed_at   TIMESTAMPTZ;

-- Meaning-based fact search: one vector per fact and embedding model (plain arrays, no pgvector needed).
CREATE TABLE IF NOT EXISTS knowledge_embedding (
    knowledge_id UUID         NOT NULL REFERENCES product_knowledge(id) ON DELETE CASCADE,
    model        VARCHAR(200) NOT NULL,
    tenant_id    UUID         NOT NULL,
    content_hash VARCHAR(64)  NOT NULL,
    vector       REAL[]       NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (knowledge_id, model)
);

-- Uploaded documents (PDF, Word, text, Markdown, CSV). Each is split into clause-sized facts in
-- product_knowledge; deleting the document deletes its facts. The extracted text stays here, never only at a provider.
CREATE TABLE IF NOT EXISTS knowledge_document (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID         NOT NULL,
    filename    VARCHAR(255) NOT NULL,
    title       VARCHAR(255) NOT NULL,
    category    VARCHAR(100) NOT NULL DEFAULT 'General',
    file_type   VARCHAR(10)  NOT NULL,
    size_bytes  INTEGER      NOT NULL,
    sha256      VARCHAR(64)  NOT NULL,
    pages       INTEGER,
    uploaded_by VARCHAR(100),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, sha256)
);
ALTER TABLE product_knowledge ADD COLUMN IF NOT EXISTS document_id UUID REFERENCES knowledge_document(id) ON DELETE CASCADE;
ALTER TABLE product_knowledge ADD COLUMN IF NOT EXISTS chunk_index INTEGER;
CREATE INDEX IF NOT EXISTS idx_knowledge_document ON product_knowledge (document_id);

-- AI sync: each workspace keeps one fact index per AI connection (embedding model). Vectors live in
-- knowledge_embedding; this records each sync run so the UI can show what is synced and what is pending.
CREATE TABLE IF NOT EXISTS ai_sync_run (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   UUID         NOT NULL,
    model       VARCHAR(200) NOT NULL,
    trigger     VARCHAR(20)  NOT NULL,          -- CONNECT | UPLOAD | MANUAL | ANALYSIS
    status      VARCHAR(12)  NOT NULL DEFAULT 'RUNNING',  -- RUNNING | DONE | FAILED
    total       INTEGER      NOT NULL DEFAULT 0,
    embedded    INTEGER      NOT NULL DEFAULT 0,
    removed     INTEGER      NOT NULL DEFAULT 0,
    error       TEXT,
    started_by  VARCHAR(100),
    started_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ai_sync_run ON ai_sync_run (tenant_id, started_at DESC);
