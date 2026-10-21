package io.yudhix.ledger.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AuditEventRequest {

    @NotNull(message = "tenantId is required")
    private UUID tenantId;

    private String actorId;

    @NotBlank(message = "actorType is required")
    private String actorType; // USER, SYSTEM, SERVICE

    @NotBlank(message = "action is required")
    private String action; // e.g. REPLY_APPROVED, TENANT_ONBOARDED, DSR_COMPLETED

    @NotBlank(message = "entityType is required")
    private String entityType;

    @NotBlank(message = "entityId is required")
    private String entityId;

    private String beforeState;
    private String afterState;
    private String ipHash;
    private String userAgent;
}
