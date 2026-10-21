package io.yudhix.link.service;

import io.yudhix.link.entity.PlatformCredential;
import io.yudhix.link.repository.PlatformCredentialRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.HexFormat;
import java.util.UUID;

/**
 * AES-256-GCM Envelope Encryption for OAuth platform tokens.
 * Tokens are never persisted or returned in raw text.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class CredentialVaultService {

    private static final String AES_GCM = "AES/GCM/NoPadding";
    private static final int GCM_IV_LENGTH = 12; // 96-bit IV
    private static final int GCM_TAG_LENGTH = 128; // 128-bit authentication tag

    private final PlatformCredentialRepository credentialRepository;

    @Value("${yudhix.security.master-key}")
    private String masterKeyHex;

    @Transactional
    public void storeCredential(UUID tenantId, String platform, String rawRefreshToken) {
        log.info("Encrypting and storing OAuth credential for tenant {} on platform {}", tenantId, platform);

        byte[] iv = new byte[GCM_IV_LENGTH];
        new SecureRandom().nextBytes(iv);

        try {
            SecretKey secretKey = getMasterKey();
            Cipher cipher = Cipher.getInstance(AES_GCM);
            GCMParameterSpec spec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
            cipher.init(Cipher.ENCRYPT_MODE, secretKey, spec);

            byte[] cipherTextWithTag = cipher.doFinal(rawRefreshToken.getBytes(StandardCharsets.UTF_8));

            // Extract tag (last 16 bytes) and ciphertext
            int cipherTextLength = cipherTextWithTag.length - 16;
            byte[] cipherText = new byte[cipherTextLength];
            byte[] tag = new byte[16];
            System.arraycopy(cipherTextWithTag, 0, cipherText, 0, cipherTextLength);
            System.arraycopy(cipherTextWithTag, cipherTextLength, tag, 0, 16);

            String encodedCipher = Base64.getEncoder().encodeToString(cipherText);
            String ivHex = HexFormat.of().formatHex(iv);
            String tagHex = HexFormat.of().formatHex(tag);

            PlatformCredential credential = credentialRepository.findByTenantIdAndPlatform(tenantId, platform.toUpperCase())
                    .orElseGet(() -> PlatformCredential.builder()
                            .tenantId(tenantId)
                            .platform(platform.toUpperCase())
                            .build());

            credential.setEncryptedRefreshToken(encodedCipher);
            credential.setTokenIv(ivHex);
            credential.setTokenTag(tagHex);
            credentialRepository.save(credential);

        } catch (Exception e) {
            throw new IllegalStateException("Failed to encrypt OAuth credential", e);
        }
    }

    @Transactional(readOnly = true)
    public String retrieveCredential(UUID tenantId, String platform) {
        PlatformCredential credential = credentialRepository.findByTenantIdAndPlatform(tenantId, platform.toUpperCase())
                .orElseThrow(() -> new IllegalStateException("Missing credential for platform: " + platform));

        try {
            byte[] iv = HexFormat.of().parseHex(credential.getTokenIv());
            byte[] tag = HexFormat.of().parseHex(credential.getTokenTag());
            byte[] cipherText = Base64.getDecoder().decode(credential.getEncryptedRefreshToken());

            // Recombine ciphertext + tag for GCM decryption
            byte[] cipherTextWithTag = new byte[cipherText.length + tag.length];
            System.arraycopy(cipherText, 0, cipherTextWithTag, 0, cipherText.length);
            System.arraycopy(tag, 0, cipherTextWithTag, cipherText.length, tag.length);

            SecretKey secretKey = getMasterKey();
            Cipher cipher = Cipher.getInstance(AES_GCM);
            GCMParameterSpec spec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
            cipher.init(Cipher.DECRYPT_MODE, secretKey, spec);

            byte[] plainBytes = cipher.doFinal(cipherTextWithTag);
            return new String(plainBytes, StandardCharsets.UTF_8);

        } catch (Exception e) {
            throw new IllegalStateException("Failed to decrypt OAuth credential", e);
        }
    }

    private SecretKey getMasterKey() {
        byte[] keyBytes = HexFormat.of().parseHex(masterKeyHex.trim());
        return new SecretKeySpec(keyBytes, "AES");
    }
}
