package io.yudhix.notify.entity;

import jakarta.persistence.*;
import lombok.*;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "notification_rule")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class NotificationRule {

    @Id
    @Column(nullable = false)
    private UUID id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Column(nullable = false, length = 150)
    private String name;

    @Column(name = "rule_type", nullable = false, length = 50)
    private String ruleType; // CRISIS_SPIKE, P1_ALERT, SLA_BREACH

    @Column(name = "threshold_value", precision = 5, scale = 2)
    private BigDecimal thresholdValue;

    @Column(nullable = false, length = 50)
    private String channel; // EMAIL, WEBHOOK, SLACK

    @Column(name = "target_destination", nullable = false)
    private String targetDestination;

    @Column(nullable = false)
    @Builder.Default
    private boolean active = true;

    @Column(name = "created_at", nullable = false)
    @Builder.Default
    private Instant createdAt = Instant.now();
}
