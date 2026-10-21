-- Policy Documents (Versioned, immutable text with SHA-256 content hashes)
CREATE TABLE IF NOT EXISTS policy_document (
    id UUID PRIMARY KEY,
    code VARCHAR(50) NOT NULL,
    country_code VARCHAR(10), -- NULL for global policies
    platform VARCHAR(50),     -- NULL for non-platform specific
    version VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body_md TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL DEFAULT now(),
    mandatory BOOLEAN NOT NULL DEFAULT true,
    UNIQUE (code, country_code, version)
);

-- Seed Standard Global & Regional Policy Packs
INSERT INTO policy_document (id, code, country_code, platform, version, title, body_md, content_hash, effective_from, mandatory)
VALUES
    (
        'a1b2c3d4-0001-0000-0000-000000000001',
        'TOS',
        NULL,
        NULL,
        '1.0',
        'Yudhix Master Terms of Service',
        '# Yudhix Master Terms of Service\n\nThese terms govern tenant use of the Yudhix Platform for lawful social listening and product experience resolution. Deceptive practices, artificial astroturfing, and undisclosed promotional replies are strictly prohibited.',
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        now(),
        true
    ),
    (
        'a1b2c3d4-0002-0000-0000-000000000002',
        'PRIVACY',
        NULL,
        NULL,
        '1.0',
        'Yudhix Global Privacy Policy',
        '# Yudhix Global Privacy Policy\n\nYudhix adheres to strict data minimization. Public social comment authors are pseudonymized using keyed cryptographic HMAC-SHA256. Raw personal identifiers are masked prior to model enrichment.',
        'f2ca1bb6c7e907d06dafe4687e579fce76b37e4e93b7605022da52e6ccc26fd2',
        now(),
        true
    ),
    (
        'a1b2c3d4-0003-0000-0000-000000000003',
        'DPA',
        NULL,
        NULL,
        '1.0',
        'Data Processing Agreement (DPA)',
        '# Data Processing Agreement\n\nDefines roles: Tenant is Data Fiduciary/Controller; Yudhix is Data Processor. Security measures, incident reporting, and audit rights are detailed herein.',
        '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8',
        now(),
        true
    ),
    (
        'a1b2c3d4-0004-0000-0000-000000000004',
        'IN_DPDP_NOTICE',
        'IN',
        NULL,
        '1.0',
        'India Digital Personal Data Protection (DPDP) Act 2023 & Rules 2025 Notice',
        '# India DPDP Notice\n\nCompliant with the Digital Personal Data Protection Act, 2023. Specifies grievance officer contact, 6-hour CERT-In incident reporting commitment, purpose limitation, and DSR erasure procedures.',
        '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a',
        now(),
        true
    ),
    (
        'a1b2c3d4-0005-0000-0000-000000000005',
        'US_CCPA_ADDENDUM',
        'US',
        NULL,
        '1.0',
        'California Consumer Privacy Act (CCPA/CPRA) Service Provider Addendum',
        '# California CCPA/CPRA Addendum\n\nYudhix certifies that it acts as a Service Provider and does not sell, share, or retain consumer personal information outside the direct business relationship with Tenant.',
        'ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d',
        now(),
        true
    )
ON CONFLICT (code, country_code, version) DO NOTHING;

-- Consent Records (Audit-proof proof of policy acceptance)
CREATE TABLE IF NOT EXISTS consent_record (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    policy_id UUID NOT NULL REFERENCES policy_document(id),
    content_hash VARCHAR(64) NOT NULL,
    accepted_by VARCHAR(100) NOT NULL,
    signer_name VARCHAR(255) NOT NULL,
    signer_title VARCHAR(255),
    accepted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip_hash VARCHAR(100),
    withdrawn_at TIMESTAMPTZ
);

-- Data Subject Rights (DSR) Requests
CREATE TABLE IF NOT EXISTS dsr_request (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    author_hash VARCHAR(100) NOT NULL,
    request_type VARCHAR(50) NOT NULL, -- ERASURE, ACCESS, PORTABILITY
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_consent_tenant ON consent_record(tenant_id);
CREATE INDEX IF NOT EXISTS idx_dsr_tenant ON dsr_request(tenant_id);
CREATE INDEX IF NOT EXISTS idx_dsr_author_hash ON dsr_request(author_hash);
