package io.yudhix.dharma.dto;

import io.yudhix.dharma.entity.DsrRequest;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
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
public class DsrRequestDto {

    private UUID id;

    @NotNull(message = "tenantId is required")
    private UUID tenantId;

    @NotBlank(message = "platform is required")
    private String platform;

    @NotBlank(message = "authorHash is required")
    private String authorHash;

    @NotBlank(message = "requestType (ERASURE, ACCESS) is required")
    private String requestType;

    private String status;
    private Instant requestedAt;
    private Instant completedAt;

    public static DsrRequestDto from(DsrRequest entity) {
        return DsrRequestDto.builder()
                .id(entity.getId())
                .tenantId(entity.getTenantId())
                .platform(entity.getPlatform())
                .authorHash(entity.getAuthorHash())
                .requestType(entity.getRequestType())
                .status(entity.getStatus())
                .requestedAt(entity.getRequestedAt())
                .completedAt(entity.getCompletedAt())
                .build();
    }
}
