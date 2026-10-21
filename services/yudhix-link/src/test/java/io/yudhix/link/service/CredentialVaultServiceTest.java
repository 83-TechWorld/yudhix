package io.yudhix.link.service;

import io.yudhix.link.entity.PlatformCredential;
import io.yudhix.link.repository.PlatformCredentialRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class CredentialVaultServiceTest {

    @Mock
    private PlatformCredentialRepository credentialRepository;

    @InjectMocks
    private CredentialVaultService vaultService;

    private final String masterKeyHex = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

    @BeforeEach
    void setup() {
        ReflectionTestUtils.setField(vaultService, "masterKeyHex", masterKeyHex);
    }

    @Test
    void testEncryptAndDecryptRoundTrip() {
        UUID tenantId = UUID.randomUUID();
        String platform = "YOUTUBE";
        String rawSecret = "1//04xyz-google-refresh-token-secure-value";

        final PlatformCredential[] holder = new PlatformCredential[1];

        when(credentialRepository.findByTenantIdAndPlatform(tenantId, platform)).thenAnswer(i -> Optional.ofNullable(holder[0]));
        when(credentialRepository.save(any(PlatformCredential.class))).thenAnswer(i -> {
            PlatformCredential cred = i.getArgument(0);
            holder[0] = cred;
            return cred;
        });

        vaultService.storeCredential(tenantId, platform, rawSecret);

        String decrypted = vaultService.retrieveCredential(tenantId, platform);
        assertEquals(rawSecret, decrypted);
    }
}
