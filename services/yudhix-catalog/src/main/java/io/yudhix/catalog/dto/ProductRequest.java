package io.yudhix.catalog.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ProductRequest {

    @NotNull(message = "tenantId is required")
    private UUID tenantId;

    @NotBlank(message = "Product code is required (e.g. ps5)")
    private String code;

    @NotBlank(message = "Product name is required (e.g. PlayStation 5)")
    private String name;

    private String category;
    private boolean competitor;
    private String customAttributes;
    private List<String> aliases;
}
