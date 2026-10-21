package io.yudhix.tenant.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Entity
@Table(name = "tenant_user", uniqueConstraints = {
        @UniqueConstraint(columnNames = {"tenant_id", "keycloak_user_id"})
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class TenantUser {

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Column(name = "keycloak_user_id", nullable = false, length = 100)
    private String keycloakUserId;

    @Column(nullable = false)
    private String email;

    @Column(name = "full_name")
    private String fullName;

    @Column(columnDefinition = "text[]")
    @Builder.Default
    private List<String> roles = new ArrayList<>();

    @Column(nullable = false)
    @Builder.Default
    private boolean active = true;

    @Column(name = "created_at", nullable = false, updatable = false)
    @Builder.Default
    private Instant createdAt = Instant.now();

    @PrePersist
    public void prePersist() {
        if (id == null) {
            id = UUID.randomUUID();
        }
        if (createdAt == null) {
            createdAt = Instant.now();
        }
    }
}
