package io.yudhix.common.security;

import org.junit.jupiter.api.Test;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class AuthorHasherTest {

    @Test
    void testAuthorHasherGeneratesConsistentPseudonym() {
        AuthorKeyProvider keyProvider = new InMemoryAuthorKeyProvider();
        AuthorHasher hasher = new AuthorHasher(keyProvider);

        UUID tenantA = UUID.randomUUID();
        UUID tenantB = UUID.randomUUID();
        String platform = "YOUTUBE";
        String rawAuthorId = "UC_x5XG1OV2P6uZZ5FSM9Ttw";

        String hash1 = hasher.hash(tenantA, platform, rawAuthorId);
        String hash2 = hasher.hash(tenantA, platform, rawAuthorId);
        String hashTenantB = hasher.hash(tenantB, platform, rawAuthorId);

        // Same tenant & author produces identical hash
        assertEquals(hash1, hash2);
        assertTrue(hash1.startsWith("1."));

        // Different tenant produces distinct hash (no cross-tenant tracking)
        assertNotEquals(hash1, hashTenantB);

        // Display alias generation
        String alias = AuthorHasher.toDisplayAlias(hash1);
        assertTrue(alias.startsWith("Author #"));
        assertEquals(14, alias.length());
    }
}
