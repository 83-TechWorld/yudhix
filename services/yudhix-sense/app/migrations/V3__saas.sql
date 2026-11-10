-- =============================================================================
-- yudhix-sense V3: SaaS layer (workspaces, team, billing, notifications)
-- Idempotent: applied on every startup.
-- Identity lives in Keycloak (tenant_user.keycloak_user_id = token "sub").
-- =============================================================================

-- 1. Workspaces (tenant) ---------------------------------------------------------
ALTER TABLE tenant ADD COLUMN IF NOT EXISTS industry VARCHAR(80);
ALTER TABLE tenant ADD COLUMN IF NOT EXISTS team_size VARCHAR(20);
ALTER TABLE tenant ADD COLUMN IF NOT EXISTS created_by VARCHAR(100);
ALTER TABLE tenant ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE tenant ADD COLUMN IF NOT EXISTS is_demo BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE tenant_user ADD COLUMN IF NOT EXISTS invited_by VARCHAR(100);
ALTER TABLE tenant_user ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_tenant_user_kc ON tenant_user (keycloak_user_id) WHERE active;

-- 2. Invitations -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS workspace_invitation (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    email       VARCHAR(255) NOT NULL,
    role        VARCHAR(20) NOT NULL,                       -- admin | approver | agent | analyst
    token_hash  VARCHAR(64) NOT NULL UNIQUE,                -- SHA-256 of the emailed token; the token itself is never stored
    status      VARCHAR(20) NOT NULL DEFAULT 'PENDING',     -- PENDING | ACCEPTED | REVOKED
    invited_by  VARCHAR(100) NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    accepted_by VARCHAR(100),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_invitation_tenant ON workspace_invitation (tenant_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS uq_invitation_pending_email
    ON workspace_invitation (tenant_id, lower(email)) WHERE status = 'PENDING';

-- 3. Plans & subscriptions ------------------------------------------------------------
ALTER TABLE plan ADD COLUMN IF NOT EXISTS video_quota INTEGER NOT NULL DEFAULT 20;
ALTER TABLE plan ADD COLUMN IF NOT EXISTS seat_limit INTEGER NOT NULL DEFAULT 5;
ALTER TABLE plan ADD COLUMN IF NOT EXISTS yearly_price NUMERIC(10, 2);
ALTER TABLE plan ADD COLUMN IF NOT EXISTS tagline VARCHAR(200);
ALTER TABLE plan ADD COLUMN IF NOT EXISTS features JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE plan ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0;
ALTER TABLE plan ADD COLUMN IF NOT EXISTS highlighted BOOLEAN NOT NULL DEFAULT false;

INSERT INTO plan (id, name, monthly_price, currency, comment_quota, llm_quota, reply_quota, active)
VALUES ('STARTER', 'Starter', 99, 'USD', 10000, 2000, 500, true),
       ('PROFESSIONAL', 'Professional', 499, 'USD', 100000, 25000, 5000, true),
       ('ENTERPRISE', 'Enterprise', 1999, 'USD', -1, -1, -1, true)
ON CONFLICT (id) DO NOTHING;

UPDATE plan SET name = 'Starter', monthly_price = 99, yearly_price = 990, video_quota = 20, seat_limit = 5,
       comment_quota = 10000, llm_quota = 2000, reply_quota = 500, sort_order = 1, highlighted = false,
       tagline = 'For one brand getting started with truth-first monitoring',
       features = '["20 video analyses / month", "10,000 comments / month", "5 team members", "Claims, verdicts & audience impact", "Approval workflow", "Email support"]'
 WHERE id = 'STARTER';
UPDATE plan SET name = 'Professional', monthly_price = 499, yearly_price = 4990, video_quota = 100, seat_limit = 20,
       comment_quota = 100000, llm_quota = 25000, reply_quota = 5000, sort_order = 2, highlighted = true,
       tagline = 'For brand and social teams managing several products',
       features = '["100 video analyses / month", "100,000 comments / month", "20 team members", "Creator clarification notes", "Turnaround analytics", "Priority support"]'
 WHERE id = 'PROFESSIONAL';
UPDATE plan SET name = 'Enterprise', monthly_price = 1999, yearly_price = 19990, video_quota = -1, seat_limit = -1,
       comment_quota = -1, llm_quota = -1, reply_quota = -1, sort_order = 3, highlighted = false,
       tagline = 'For enterprises and agencies with compliance needs',
       features = '["Unlimited analyses & comments", "Unlimited team members", "SSO / SAML via Keycloak", "DPDP & CCPA policy packs", "Audit ledger export", "Dedicated success manager"]'
 WHERE id = 'ENTERPRISE';

ALTER TABLE subscription ADD COLUMN IF NOT EXISTS billing_interval VARCHAR(10) NOT NULL DEFAULT 'MONTH';  -- MONTH | YEAR
ALTER TABLE subscription ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMPTZ;
ALTER TABLE subscription ADD COLUMN IF NOT EXISTS cancel_at_period_end BOOLEAN NOT NULL DEFAULT false;

-- 4. Invoices ----------------------------------------------------------------------
CREATE SEQUENCE IF NOT EXISTS invoice_number_seq START 1001;
ALTER TABLE invoice ADD COLUMN IF NOT EXISTS number VARCHAR(30);
ALTER TABLE invoice ADD COLUMN IF NOT EXISTS period_start TIMESTAMPTZ;
ALTER TABLE invoice ADD COLUMN IF NOT EXISTS period_end TIMESTAMPTZ;
ALTER TABLE invoice ADD COLUMN IF NOT EXISTS due_at TIMESTAMPTZ;
ALTER TABLE invoice ADD COLUMN IF NOT EXISTS tax_label VARCHAR(60);
CREATE UNIQUE INDEX IF NOT EXISTS uq_invoice_number ON invoice (number) WHERE number IS NOT NULL;

CREATE TABLE IF NOT EXISTS invoice_line (
    id          BIGSERIAL PRIMARY KEY,
    invoice_id  UUID NOT NULL REFERENCES invoice(id) ON DELETE CASCADE,
    description VARCHAR(300) NOT NULL,
    quantity    NUMERIC(12, 2) NOT NULL DEFAULT 1,
    unit_price  NUMERIC(12, 4) NOT NULL,
    amount      NUMERIC(12, 2) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_invoice_line_invoice ON invoice_line (invoice_id);

-- 5. In-app notifications (one row per recipient) ---------------------------------------
CREATE TABLE IF NOT EXISTS app_notification (
    id         BIGSERIAL PRIMARY KEY,
    tenant_id  UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    user_id    VARCHAR(100) NOT NULL,
    kind       VARCHAR(40) NOT NULL,
    title      VARCHAR(200) NOT NULL,
    body       TEXT,
    link       VARCHAR(300),
    read_at    TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_app_notification_user ON app_notification (tenant_id, user_id, created_at DESC);

-- 6. Demo workspace for the seeded PlayStation data -------------------------------------
INSERT INTO tenant (id, name, slug, hq_country, operating_countries, data_region, status, plan_code, industry, team_size, is_demo)
VALUES ('9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d', 'PlayStation (Demo)', 'playstation-demo', 'IN', '{IN,US}', 'ap-south-1',
        'ACTIVE', 'ENTERPRISE', 'Consumer electronics', '1000+', true)
ON CONFLICT (id) DO UPDATE SET is_demo = true, status = 'ACTIVE';

INSERT INTO subscription (tenant_id, plan_id, status, current_period_start, current_period_end, billing_interval)
VALUES ('9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d', 'ENTERPRISE', 'ACTIVE', date_trunc('month', now()),
        date_trunc('month', now()) + interval '1 month', 'MONTH')
ON CONFLICT (tenant_id) DO NOTHING;
