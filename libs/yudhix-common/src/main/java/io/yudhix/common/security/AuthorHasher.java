package io.yudhix.common.security;

import javax.crypto.Mac;
import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.util.Base64;
import java.util.Objects;
import java.util.UUID;

/**
 * Privacy-preserving keyed author pseudonymizer:
 * author_hash = version + "." + Base64Url(HMAC-SHA256(tenant_key, platform + ":" + platform_author_id))
 * Prevents dictionary attacks across tenants while allowing repeat poster detection.
 */
public final class AuthorHasher {

    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private final AuthorKeyProvider keyProvider;

    public AuthorHasher(AuthorKeyProvider keyProvider) {
        this.keyProvider = Objects.requireNonNull(keyProvider, "keyProvider must not be null");
    }

    public String hash(UUID tenantId, String platform, String platformAuthorId) {
        Objects.requireNonNull(tenantId, "tenantId must not be null");
        Objects.requireNonNull(platform, "platform must not be null");
        Objects.requireNonNull(platformAuthorId, "platformAuthorId must not be null");

        SecretKey key = keyProvider.currentKey(tenantId);
        short version = keyProvider.currentVersion(tenantId);

        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            mac.init(key);
            String payload = platform.trim().toUpperCase() + ":" + platformAuthorId.trim();
            byte[] rawHash = mac.doFinal(payload.getBytes(StandardCharsets.UTF_8));
            String encoded = Base64.getUrlEncoder().withoutPadding().encodeToString(rawHash);
            return version + "." + encoded;
        } catch (NoSuchAlgorithmException | InvalidKeyException e) {
            throw new IllegalStateException("Failed to calculate HMAC-SHA256 author hash", e);
        }
    }

    /**
     * Generates a safe, human-readable pseudonym for dashboard UI display (e.g. Author #7F3A2C).
     */
    public static String toDisplayAlias(String authorHash) {
        if (authorHash == null || authorHash.isBlank()) {
            return "Author #Unknown";
        }
        int dotIndex = authorHash.indexOf('.');
        String hashPart = (dotIndex >= 0 && dotIndex < authorHash.length() - 1)
                ? authorHash.substring(dotIndex + 1)
                : authorHash;

        String prefix = hashPart.length() >= 6 ? hashPart.substring(0, 6) : hashPart;
        return "Author #" + prefix.toUpperCase();
    }
}
