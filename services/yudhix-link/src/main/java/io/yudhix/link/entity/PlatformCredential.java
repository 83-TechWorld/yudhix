package io.yudhix.link.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "platform_credential", uniqueConstraints = {
        @UniqueConstraint(columnNames = {"tenant_id", "platform"})
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class PlatformCredential {

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Column(nullable = false, length = 50)
    private String platform;

    @Column(name = "encrypted_refresh_token", nullable = false, columnDefinition = "text")
    private String encryptedRefreshToken;

    @Column(name = "token_iv", nullable = false, length = 64)
    private String tokenIv;

    @Column(name = "token_tag", nullable = false, length = 64)
    private String tokenTag;

    @Column(name = "key_version", nullable = false)
    @Builder.Default
    private int keyVersion = 1;

    @Column(name = "expires_at")
    private Instant expiresAt;

    @Column(name = "updated_at", nullable = false)
    @Builder.Default
    private Instant updatedAt = Instant.now();

    @PrePersist
    public void prePersist() {
        if (id == null) {
            id = UUID.randomUUID();
        }
        updatedAt = Instant.now();
    }

    @PreUpdate
    public void preUpdate() {
        updatedAt = Instant.now();
    }
}
