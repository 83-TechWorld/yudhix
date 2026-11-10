-- =============================================================================
-- yudhix-sense V2: Truth-first core
-- Idempotent: safe to run on every startup and on databases that already have
-- the truth tables (they were first created by hand, outside migrations).
-- =============================================================================

-- 1. Brand knowledge base (RAG ground truth) ----------------------------------
CREATE TABLE IF NOT EXISTS product_knowledge (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID NOT NULL,
    product_id         UUID,
    document_title     VARCHAR(255) NOT NULL,
    category           VARCHAR(100) NOT NULL,
    clause_ref         VARCHAR(100),
    official_statement TEXT NOT NULL,
    citation_source    VARCHAR(255),
    verified_at        TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at         TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_product_knowledge_tenant ON product_knowledge (tenant_id);

-- 2. Decoded videos --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS video_truth_analysis (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL,
    video_id                VARCHAR(100) NOT NULL,
    channel_title           VARCHAR(255) NOT NULL,
    video_title             VARCHAR(500) NOT NULL,
    video_url               VARCHAR(500) NOT NULL,
    published_date          VARCHAR(100),
    duration_seconds        INTEGER DEFAULT 0,
    rage_bait_score         DOUBLE PRECISION DEFAULT 0.0,
    factual_accuracy_score  DOUBLE PRECISION DEFAULT 0.0,
    sensationalism_grade    VARCHAR(50) DEFAULT 'MODERATE',
    total_claims            INTEGER DEFAULT 0,
    misleading_claims_count INTEGER DEFAULT 0,
    summary                 TEXT,
    created_at              TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE video_truth_analysis ADD COLUMN IF NOT EXISTS product_id UUID;
ALTER TABLE video_truth_analysis ADD COLUMN IF NOT EXISTS thumbnail_url VARCHAR(500);
ALTER TABLE video_truth_analysis ADD COLUMN IF NOT EXISTS transcript_source VARCHAR(50) DEFAULT 'SEEDED';
ALTER TABLE video_truth_analysis ADD COLUMN IF NOT EXISTS analysis_method VARCHAR(50) DEFAULT 'SEEDED';
ALTER TABLE video_truth_analysis ADD COLUMN IF NOT EXISTS view_count BIGINT;
ALTER TABLE video_truth_analysis ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;
CREATE UNIQUE INDEX IF NOT EXISTS uq_video_truth_tenant_video ON video_truth_analysis (tenant_id, video_id);

-- 3. Atomic claims extracted from a video ----------------------------------------
CREATE TABLE IF NOT EXISTS video_claim (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id              UUID NOT NULL,
    video_analysis_id      UUID REFERENCES video_truth_analysis(id) ON DELETE CASCADE,
    timestamp_start        VARCHAR(20) NOT NULL,
    timestamp_seconds      INTEGER DEFAULT 0,
    creator_quote          TEXT NOT NULL,
    topic                  VARCHAR(100) NOT NULL,
    verdict                VARCHAR(50) NOT NULL,
    confidence_score       DOUBLE PRECISION DEFAULT 0.9,
    rag_knowledge_id       UUID REFERENCES product_knowledge(id) ON DELETE SET NULL,
    fact_check_analysis    TEXT NOT NULL,
    official_citation      TEXT,
    incited_comments_count INTEGER DEFAULT 0,
    sentiment_impact       VARCHAR(50) DEFAULT 'NEGATIVE',
    created_at             TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE video_claim ADD COLUMN IF NOT EXISTS verification_method VARCHAR(30) DEFAULT 'SEEDED';
CREATE INDEX IF NOT EXISTS idx_video_claim_video ON video_claim (tenant_id, video_analysis_id);

-- 4. Background "Analyze video" jobs ---------------------------------------------
CREATE TABLE IF NOT EXISTS video_analysis_job (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL,
    video_url   VARCHAR(500) NOT NULL,
    video_id    VARCHAR(100),
    product_id  UUID,
    status      VARCHAR(30) NOT NULL DEFAULT 'QUEUED',   -- QUEUED | RUNNING | COMPLETED | FAILED
    stage       VARCHAR(50) NOT NULL DEFAULT 'QUEUED',
    progress    INTEGER NOT NULL DEFAULT 0,
    message     TEXT,
    error       TEXT,
    created_by  VARCHAR(100),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_video_job_tenant ON video_analysis_job (tenant_id, created_at DESC);

-- 5. Which comment was triggered by which claim (outrage attribution) -----------
CREATE TABLE IF NOT EXISTS comment_claim_link (
    tenant_id  UUID NOT NULL,
    comment_id UUID NOT NULL,
    claim_id   UUID NOT NULL REFERENCES video_claim(id) ON DELETE CASCADE,
    score      DOUBLE PRECISION NOT NULL,
    method     VARCHAR(30) NOT NULL DEFAULT 'LEXICAL',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, comment_id, claim_id)
);
ALTER TABLE comment_claim_link ADD COLUMN IF NOT EXISTS evidence VARCHAR(200);
CREATE INDEX IF NOT EXISTS idx_claim_link_claim ON comment_claim_link (tenant_id, claim_id);

-- 6. Creator clarification notes ---------------------------------------------------
CREATE TABLE IF NOT EXISTS creator_outreach (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL,
    video_id      VARCHAR(100) NOT NULL,
    channel_title VARCHAR(255),
    claim_ids     UUID[] NOT NULL DEFAULT '{}',
    subject       VARCHAR(300) NOT NULL,
    body          TEXT NOT NULL,
    status        VARCHAR(30) NOT NULL DEFAULT 'DRAFT',   -- DRAFT | SENT
    created_by    VARCHAR(100),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_outreach_video ON creator_outreach (tenant_id, video_id);

-- 7. Reply workflow extras ----------------------------------------------------------
ALTER TABLE IF EXISTS reply ADD COLUMN IF NOT EXISTS claim_id UUID;
ALTER TABLE IF EXISTS reply ADD COLUMN IF NOT EXISTS delivery_mode VARCHAR(20);          -- LIVE | SIMULATED
ALTER TABLE IF EXISTS reply ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMPTZ;
ALTER TABLE IF EXISTS reply ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;
ALTER TABLE IF EXISTS reply_outcome ADD COLUMN IF NOT EXISTS outcome VARCHAR(20);         -- IMPROVED | NEUTRAL | WORSENED
ALTER TABLE IF EXISTS reply_outcome ADD COLUMN IF NOT EXISTS follow_up_text TEXT;
ALTER TABLE IF EXISTS reply_outcome ADD COLUMN IF NOT EXISTS source VARCHAR(20);          -- PLATFORM | MANUAL
