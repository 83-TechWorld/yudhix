package io.yudhix.meter.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "usage_event", uniqueConstraints = {
        @UniqueConstraint(columnNames = {"tenant_id", "metric_type", "idempotency_key"})
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UsageEvent {

    @Id
    @Column(nullable = false)
    private UUID id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Column(name = "metric_type", nullable = false, length = 50)
    private String metricType; // comments_ingested, comments_llm_analyzed, replies_posted

    @Column(nullable = false)
    @Builder.Default
    private int quantity = 1;

    @Column(name = "idempotency_key", nullable = false, length = 120)
    private String idempotencyKey;

    @Column(name = "recorded_at", nullable = false)
    @Builder.Default
    private Instant recordedAt = Instant.now();
}
