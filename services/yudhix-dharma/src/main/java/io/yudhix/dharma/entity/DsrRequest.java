package io.yudhix.dharma.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "dsr_request")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DsrRequest {

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Column(nullable = false, length = 50)
    private String platform;

    @Column(name = "author_hash", nullable = false, length = 100)
    private String authorHash;

    @Column(name = "request_type", nullable = false, length = 50)
    private String requestType; // ERASURE, ACCESS, PORTABILITY

    @Column(nullable = false, length = 50)
    @Builder.Default
    private String status = "PENDING"; // PENDING, PROCESSING, COMPLETED, REJECTED

    @Column(name = "requested_at", nullable = false)
    @Builder.Default
    private Instant requestedAt = Instant.now();

    @Column(name = "completed_at")
    private Instant completedAt;

    @PrePersist
    public void prePersist() {
        if (id == null) {
            id = UUID.randomUUID();
        }
        if (requestedAt == null) {
            requestedAt = Instant.now();
        }
    }
}
