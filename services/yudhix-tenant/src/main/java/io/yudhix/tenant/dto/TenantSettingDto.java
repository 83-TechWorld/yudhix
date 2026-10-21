package io.yudhix.tenant.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TenantSettingDto {

    @NotBlank(message = "Setting key is required")
    private String key;

    @NotBlank(message = "Setting JSON value is required")
    private String value;

    private Instant updatedAt;
}
