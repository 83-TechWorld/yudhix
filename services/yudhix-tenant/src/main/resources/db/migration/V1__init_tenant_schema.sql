-- Country Configuration Catalog
CREATE TABLE IF NOT EXISTS country_config (
    country_code VARCHAR(10) PRIMARY KEY,
    country_name VARCHAR(100) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,
    currency VARCHAR(10) NOT NULL,
    tax_profile VARCHAR(50) NOT NULL,
    data_region VARCHAR(50) NOT NULL,
    default_retention_days INT NOT NULL DEFAULT 30,
    ai_disclosure_required BOOLEAN NOT NULL DEFAULT false,
    policy_codes TEXT[] NOT NULL DEFAULT '{}'
);

-- Seed Initial Countries: India (IN) & USA (US)
INSERT INTO country_config (country_code, country_name, enabled, currency, tax_profile, data_region, default_retention_days, ai_disclosure_required, policy_codes)
VALUES 
    ('IN', 'India', true, 'INR', 'IN_GST_18', 'ap-south-1', 30, true, ARRAY['TOS', 'PRIVACY', 'DPA', 'IN_DPDP_NOTICE', 'ASCI_AD_CODE']),
    ('US', 'United States', true, 'USD', 'US_STATE_TAX', 'us-east-1', 30, false, ARRAY['TOS', 'PRIVACY', 'DPA', 'US_CCPA_ADDENDUM', 'FTC_REVIEW_GUIDELINES'])
ON CONFLICT (country_code) DO NOTHING;

-- Tenant Entity
CREATE TABLE IF NOT EXISTS tenant (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    hq_country VARCHAR(10) NOT NULL REFERENCES country_config(country_code),
    operating_countries TEXT[] NOT NULL DEFAULT '{}',
    data_region VARCHAR(50) NOT NULL DEFAULT 'ap-south-1',
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING_CONSENT',
    plan_code VARCHAR(50) NOT NULL DEFAULT 'FREE_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Tenant Settings (Key-Value / JSON Configuration)
CREATE TABLE IF NOT EXISTS tenant_setting (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    setting_key VARCHAR(100) NOT NULL,
    setting_value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, setting_key)
);

-- Tenant Users (Internal Staff / Agents / Approvers)
CREATE TABLE IF NOT EXISTS tenant_user (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    keycloak_user_id VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    roles TEXT[] NOT NULL DEFAULT '{}',
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, keycloak_user_id)
);

CREATE INDEX IF NOT EXISTS idx_tenant_slug ON tenant(slug);
CREATE INDEX IF NOT EXISTS idx_tenant_status ON tenant(status);
CREATE INDEX IF NOT EXISTS idx_tenant_user_email ON tenant_user(email);
