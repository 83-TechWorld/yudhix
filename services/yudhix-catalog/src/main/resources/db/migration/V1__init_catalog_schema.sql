CREATE TABLE IF NOT EXISTS product (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    code VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    is_competitor BOOLEAN NOT NULL DEFAULT false,
    custom_attributes JSONB NOT NULL DEFAULT '{}',
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, code)
);

CREATE TABLE IF NOT EXISTS product_alias (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    product_id UUID NOT NULL REFERENCES product(id) ON DELETE CASCADE,
    alias VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS owned_source (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    external_ref VARCHAR(255) NOT NULL,
    product_ids UUID[] NOT NULL DEFAULT '{}',
    schedule_cron VARCHAR(50) NOT NULL DEFAULT '0 */6 * * *',
    enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_product_tenant ON product(tenant_id);
CREATE INDEX IF NOT EXISTS idx_product_alias_tenant ON product_alias(tenant_id, alias);
CREATE INDEX IF NOT EXISTS idx_owned_source_tenant ON owned_source(tenant_id, platform);
