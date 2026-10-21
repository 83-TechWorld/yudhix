-- Core Comment Table (Preserved masked comment, author pseudonym, and platform metrics)
CREATE TABLE IF NOT EXISTS comment (
    tenant_id UUID NOT NULL,
    id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    platform_comment_id VARCHAR(255) NOT NULL,
    parent_comment_id VARCHAR(255),
    source_id UUID NOT NULL,
    product_id UUID,
    author_hash VARCHAR(100) NOT NULL,
    author_key_version SMALLINT NOT NULL DEFAULT 1,
    masked_text TEXT,
    text_expires_at TIMESTAMPTZ NOT NULL,
    language VARCHAR(10),
    country_hint VARCHAR(10),
    like_count INT NOT NULL DEFAULT 0,
    reply_count INT NOT NULL DEFAULT 0,
    dislike_count INT,
    platform_created_at TIMESTAMPTZ NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    content_hash VARCHAR(64) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    custom_attributes JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, platform, platform_comment_id)
);

-- Comment Analysis Result
CREATE TABLE IF NOT EXISTS comment_analysis (
    tenant_id UUID NOT NULL,
    comment_id UUID NOT NULL,
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    model_version VARCHAR(100) NOT NULL,
    sentiment VARCHAR(20) NOT NULL,
    sentiment_score NUMERIC(4,3) NOT NULL,
    intent VARCHAR(50),
    topic_id UUID,
    toxic BOOLEAN NOT NULL DEFAULT false,
    churn_risk NUMERIC(3,2),
    impact_score NUMERIC(5,2) NOT NULL,
    priority VARCHAR(10) NOT NULL,
    needs_review BOOLEAN NOT NULL DEFAULT false,
    suggested_reply TEXT,
    PRIMARY KEY (tenant_id, comment_id)
);

-- Granular Aspect Sentiments (battery, display, price, support)
CREATE TABLE IF NOT EXISTS comment_aspect (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    comment_id UUID NOT NULL,
    aspect VARCHAR(100) NOT NULL,
    sentiment VARCHAR(20) NOT NULL,
    score NUMERIC(4,3),
    evidence TEXT
);

-- Daily Aggregated Product Sentiment (Historical analytics without personal data)
CREATE TABLE IF NOT EXISTS daily_product_sentiment (
    tenant_id UUID NOT NULL,
    day DATE NOT NULL,
    product_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    country_code VARCHAR(10) NOT NULL DEFAULT 'GLOBAL',
    positive_cnt INT NOT NULL DEFAULT 0,
    negative_cnt INT NOT NULL DEFAULT 0,
    neutral_cnt INT NOT NULL DEFAULT 0,
    mixed_cnt INT NOT NULL DEFAULT 0,
    total_likes BIGINT NOT NULL DEFAULT 0,
    total_replies BIGINT NOT NULL DEFAULT 0,
    avg_impact NUMERIC(5,2) DEFAULT 0.0,
    replied_cnt INT NOT NULL DEFAULT 0,
    improved_cnt INT NOT NULL DEFAULT 0,
    PRIMARY KEY (tenant_id, day, product_id, platform, country_code)
);

CREATE INDEX IF NOT EXISTS idx_comment_tenant_status ON comment(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_comment_analysis_priority ON comment_analysis(tenant_id, priority);
CREATE INDEX IF NOT EXISTS idx_comment_aspect ON comment_aspect(tenant_id, aspect);
