package io.yudhix.ledger.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "audit_event")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class AuditEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Column(name = "occurred_at", nullable = false)
    @Builder.Default
    private Instant occurredAt = Instant.now();

    @Column(name = "actor_id")
    private String actorId;

    @Column(name = "actor_type", nullable = false, length = 50)
    private String actorType; // USER, SYSTEM, SERVICE

    @Column(nullable = false, length = 100)
    private String action; // e.g. REPLY_APPROVED, POLICY_ACCEPTED

    @Column(name = "entity_type", nullable = false, length = 100)
    private String entityType;

    @Column(name = "entity_id", nullable = false, length = 100)
    private String entityId;

    @Column(name = "before_state", columnDefinition = "jsonb")
    private String beforeState;

    @Column(name = "after_state", columnDefinition = "jsonb")
    private String afterState;

    @Column(name = "ip_hash", length = 100)
    private String ipHash;

    @Column(name = "user_agent", columnDefinition = "text")
    private String userAgent;

    @Column(name = "prev_hash", nullable = false, length = 64)
    private String prevHash;

    @Column(name = "row_hash", nullable = false, length = 64)
    private String rowHash;
}
