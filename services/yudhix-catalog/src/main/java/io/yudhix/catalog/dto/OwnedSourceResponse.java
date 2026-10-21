package io.yudhix.catalog.dto;

import io.yudhix.catalog.entity.OwnedSource;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OwnedSourceResponse {

    private UUID id;
    private UUID tenantId;
    private String platform;
    private String sourceType;
    private String externalRef;
    private List<UUID> productIds;
    private String scheduleCron;
    private boolean enabled;
    private Instant createdAt;

    public static OwnedSourceResponse from(OwnedSource source) {
        return OwnedSourceResponse.builder()
                .id(source.getId())
                .tenantId(source.getTenantId())
                .platform(source.getPlatform())
                .sourceType(source.getSourceType())
                .externalRef(source.getExternalRef())
                .productIds(source.getProductIds())
                .scheduleCron(source.getScheduleCron())
                .enabled(source.isEnabled())
                .createdAt(source.getCreatedAt())
                .build();
    }
}
