package io.yudhix.ledger.dto;

import io.yudhix.ledger.entity.AuditEvent;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AuditEventResponse {

    private Long id;
    private UUID tenantId;
    private Instant occurredAt;
    private String actorId;
    private String actorType;
    private String action;
    private String entityType;
    private String entityId;
    private String beforeState;
    private String afterState;
    private String prevHash;
    private String rowHash;

    public static AuditEventResponse from(AuditEvent event) {
        return AuditEventResponse.builder()
                .id(event.getId())
                .tenantId(event.getTenantId())
                .occurredAt(event.getOccurredAt())
                .actorId(event.getActorId())
                .actorType(event.getActorType())
                .action(event.getAction())
                .entityType(event.getEntityType())
                .entityId(event.getEntityId())
                .beforeState(event.getBeforeState())
                .afterState(event.getAfterState())
                .prevHash(event.getPrevHash())
                .rowHash(event.getRowHash())
                .build();
    }
}
