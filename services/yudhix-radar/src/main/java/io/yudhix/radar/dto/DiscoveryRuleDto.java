package io.yudhix.radar.dto;

import io.yudhix.radar.entity.DiscoveryRule;
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
public class DiscoveryRuleDto {

    private UUID id;

    @NotNull(message = "tenantId is required")
    private UUID tenantId;

    @NotBlank(message = "Rule name is required")
    private String name;

    private boolean enabled;

    @NotBlank(message = "Rule config JSON is required")
    private String ruleConfig;

    private Instant createdAt;
    private Instant updatedAt;

    public static DiscoveryRuleDto from(DiscoveryRule rule) {
        return DiscoveryRuleDto.builder()
                .id(rule.getId())
                .tenantId(rule.getTenantId())
                .name(rule.getName())
                .enabled(rule.isEnabled())
                .ruleConfig(rule.getRuleConfig())
                .createdAt(rule.getCreatedAt())
                .updatedAt(rule.getUpdatedAt())
                .build();
    }
}
