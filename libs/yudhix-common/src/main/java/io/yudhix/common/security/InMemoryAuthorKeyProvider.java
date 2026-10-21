package io.yudhix.common.security;

import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import java.security.NoSuchAlgorithmException;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * In-memory provider for development and testing. Generates and caches AES/HMAC keys per tenant.
 */
public class InMemoryAuthorKeyProvider implements AuthorKeyProvider {

    private final Map<UUID, SecretKey> keyStore = new ConcurrentHashMap<>();
    private final short defaultVersion = 1;

    @Override
    public SecretKey currentKey(UUID tenantId) {
        return keyStore.computeIfAbsent(tenantId, id -> {
            try {
                KeyGenerator keyGen = KeyGenerator.getInstance("HmacSHA256");
                keyGen.init(256);
                return keyGen.generateKey();
            } catch (NoSuchAlgorithmException e) {
                throw new IllegalStateException("HmacSHA256 algorithm unavailable", e);
            }
        });
    }

    @Override
    public short currentVersion(UUID tenantId) {
        return defaultVersion;
    }
}
