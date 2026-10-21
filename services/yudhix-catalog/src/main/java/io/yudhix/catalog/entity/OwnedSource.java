package io.yudhix.catalog.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Entity
@Table(name = "owned_source")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class OwnedSource {

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Column(nullable = false, length = 50)
    private String platform; // YOUTUBE, LINKEDIN

    @Column(name = "source_type", nullable = false, length = 50)
    private String sourceType; // CHANNEL, PAGE, SEARCH_QUERY

    @Column(name = "external_ref", nullable = false)
    private String externalRef;

    @Column(name = "product_ids", columnDefinition = "uuid[]")
    @Builder.Default
    private List<UUID> productIds = new ArrayList<>();

    @Column(name = "schedule_cron", nullable = false, length = 50)
    @Builder.Default
    private String scheduleCron = "0 */6 * * *";

    @Column(nullable = false)
    @Builder.Default
    private boolean enabled = true;

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
