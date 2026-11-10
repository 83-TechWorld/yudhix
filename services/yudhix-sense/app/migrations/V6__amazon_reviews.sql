-- =============================================================================
-- yudhix-sense V6: Amazon product reviews as a second channel next to YouTube comments.
-- Reviews are stored as comments with platform 'AMAZON' (custom_attributes.listing_id, rating, ...),
-- so sentiment, topics, ideas and the inbox work the same for both channels.
-- Idempotent: applied on every startup.
-- =============================================================================

CREATE TABLE IF NOT EXISTS product_listing (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID         NOT NULL,
    product_id      UUID         NOT NULL,
    channel         VARCHAR(20)  NOT NULL DEFAULT 'AMAZON',
    marketplace     VARCHAR(60)  NOT NULL,              -- amazon.com, amazon.in, ...
    external_id     VARCHAR(40)  NOT NULL,              -- ASIN
    url             VARCHAR(1000) NOT NULL,
    title           VARCHAR(500),
    image_url       VARCHAR(1000),
    rating          NUMERIC(3, 2),                      -- average stars shown on the listing
    ratings_count   INTEGER,
    reviews_stored  INTEGER      NOT NULL DEFAULT 0,
    status          VARCHAR(20)  NOT NULL DEFAULT 'NEW', -- NEW | OK | BLOCKED | FAILED
    last_error      TEXT,
    checked_at      TIMESTAMPTZ,
    created_by      VARCHAR(100),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, channel, marketplace, external_id)
);
CREATE INDEX IF NOT EXISTS idx_listing_product ON product_listing (tenant_id, product_id);
CREATE INDEX IF NOT EXISTS idx_comment_platform_product ON comment (tenant_id, platform, product_id);
