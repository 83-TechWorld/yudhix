package io.yudhix.tenant.dto;

import io.yudhix.tenant.entity.Tenant;
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
public class TenantResponse {

    private UUID id;
    private String name;
    private String slug;
    private String hqCountry;
    private List<String> operatingCountries;
    private String dataRegion;
    private String status;
    private String planCode;
    private Instant createdAt;

    public static TenantResponse from(Tenant tenant) {
        return TenantResponse.builder()
                .id(tenant.getId())
                .name(tenant.getName())
                .slug(tenant.getSlug())
                .hqCountry(tenant.getHqCountry())
                .operatingCountries(tenant.getOperatingCountries())
                .dataRegion(tenant.getDataRegion())
                .status(tenant.getStatus())
                .planCode(tenant.getPlanCode())
                .createdAt(tenant.getCreatedAt())
                .build();
    }
}
