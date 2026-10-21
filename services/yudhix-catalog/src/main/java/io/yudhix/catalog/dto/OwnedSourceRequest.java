package io.yudhix.catalog.dto;

import io.yudhix.catalog.entity.OwnedSource;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
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
public class OwnedSourceRequest {

    @NotNull(message = "tenantId is required")
    private UUID tenantId;

    @NotBlank(message = "Platform is required (e.g. YOUTUBE, LINKEDIN)")
    private String platform;

    @NotBlank(message = "Source type is required (e.g. CHANNEL, PAGE, SEARCH_QUERY)")
    private String sourceType;

    @NotBlank(message = "External reference is required (e.g. Channel ID or Page URN)")
    private String externalRef;

    private List<UUID> productIds;
    private String scheduleCron;
    private Boolean enabled;
}
