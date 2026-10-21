-- Encrypted Platform OAuth Credentials Vault (AES-256-GCM)
CREATE TABLE IF NOT EXISTS platform_credential (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    encrypted_refresh_token TEXT NOT NULL,
    token_iv VARCHAR(64) NOT NULL,
    token_tag VARCHAR(64) NOT NULL,
    key_version INT NOT NULL DEFAULT 1,
    expires_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, platform)
);

-- Incremental Ingestion Watermark
CREATE TABLE IF NOT EXISTS source_watermark (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    source_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    last_comment_ts TIMESTAMPTZ,
    page_token TEXT,
    last_run_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    UNIQUE (tenant_id, source_id, platform)
);

-- Short-Lived Comment Staging (24h TTL, raw text wiped after Presidio PII masking)
CREATE TABLE IF NOT EXISTS comment_staging (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    platform_comment_id VARCHAR(255) NOT NULL,
    parent_comment_id VARCHAR(255),
    source_id UUID NOT NULL,
    author_hash VARCHAR(100) NOT NULL,
    raw_text TEXT NOT NULL,
    like_count INT NOT NULL DEFAULT 0,
    reply_count INT NOT NULL DEFAULT 0,
    dislike_count INT,
    platform_created_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '24 hours'),
    processed BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_staging_tenant ON comment_staging(tenant_id);
CREATE INDEX IF NOT EXISTS idx_staging_processed ON comment_staging(processed);
CREATE INDEX IF NOT EXISTS idx_watermark_source ON source_watermark(source_id);
