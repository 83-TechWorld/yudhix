package io.yudhix.common.security;

import javax.crypto.SecretKey;
import java.util.UUID;

/**
 * Interface to supply per-tenant cryptographic keys for HMAC pseudonymization.
 * Implemented by KMS/Vault or in-memory provider for local testing.
 */
public interface AuthorKeyProvider {

    SecretKey currentKey(UUID tenantId);

    short currentVersion(UUID tenantId);
}
