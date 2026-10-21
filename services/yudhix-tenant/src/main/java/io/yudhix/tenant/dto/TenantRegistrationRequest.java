package io.yudhix.tenant.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Pattern;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TenantRegistrationRequest {

    @NotBlank(message = "Company name is required")
    private String name;

    @NotBlank(message = "Slug is required")
    @Pattern(regexp = "^[a-z0-9-]+$", message = "Slug must contain only lowercase letters, numbers, and hyphens")
    private String slug;

    @NotBlank(message = "HQ country code is required")
    private String hqCountry;

    @NotEmpty(message = "At least one operating country must be selected")
    private List<String> operatingCountries;

    private String planCode;
}
