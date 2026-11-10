-- =============================================================================
-- yudhix-sense V4: regional pricing (INR for India, USD everywhere else)
-- Idempotent: applied on every startup.
--
-- To change a price later, update plan_price, e.g.:
--   UPDATE plan_price SET monthly_price = 8999, yearly_price = 89990 WHERE plan_id = 'STARTER' AND currency = 'INR';
-- To add a currency, insert rows for every plan and set country_config.currency for its countries.
-- Countries whose currency has no rows here are billed in USD.
-- =============================================================================

CREATE TABLE IF NOT EXISTS plan_price (
    plan_id          VARCHAR(50)    NOT NULL REFERENCES plan(id) ON DELETE CASCADE,
    currency         VARCHAR(3)     NOT NULL,
    monthly_price    NUMERIC(12, 2) NOT NULL,
    yearly_price     NUMERIC(12, 2) NOT NULL,
    overage_per_1000 NUMERIC(10, 2) NOT NULL,   -- extra comments, per 1,000
    PRIMARY KEY (plan_id, currency)
);

-- Seed only if missing, so price edits made in the database are never overwritten.
INSERT INTO plan_price (plan_id, currency, monthly_price, yearly_price, overage_per_1000) VALUES
    ('STARTER',      'USD',     99,     990,   2),
    ('PROFESSIONAL', 'USD',    499,    4990,   2),
    ('ENTERPRISE',   'USD',   1999,   19990,   2),
    ('STARTER',      'INR',   7999,   79990, 150),
    ('PROFESSIONAL', 'INR',  39999,  399990, 150),
    ('ENTERPRISE',   'INR', 159999, 1599990, 150)
ON CONFLICT (plan_id, currency) DO NOTHING;

-- The currency a workspace is billed in. Fixed while a paid plan is active, so one invoice
-- never mixes currencies; set from the workspace's country when the trial starts or a plan is chosen.
ALTER TABLE subscription ADD COLUMN IF NOT EXISTS currency VARCHAR(3);
UPDATE subscription s
   SET currency = CASE WHEN EXISTS (SELECT 1 FROM plan_price pp WHERE pp.currency = c.currency) THEN c.currency ELSE 'USD' END
  FROM tenant t LEFT JOIN country_config c ON c.country_code = t.hq_country
 WHERE t.id = s.tenant_id AND s.currency IS NULL;
UPDATE subscription SET currency = 'USD' WHERE currency IS NULL;
