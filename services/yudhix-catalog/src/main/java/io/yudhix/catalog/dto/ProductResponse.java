package io.yudhix.catalog.dto;

import io.yudhix.catalog.entity.Product;
import io.yudhix.catalog.entity.ProductAlias;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ProductResponse {

    private UUID id;
    private UUID tenantId;
    private String code;
    private String name;
    private String category;
    private boolean competitor;
    private String customAttributes;
    private boolean active;
    private List<String> aliases;
    private Instant createdAt;

    public static ProductResponse from(Product product) {
        List<String> aliasList = product.getAliases() != null
                ? product.getAliases().stream().map(ProductAlias::getAlias).collect(Collectors.toList())
                : List.of();

        return ProductResponse.builder()
                .id(product.getId())
                .tenantId(product.getTenantId())
                .code(product.getCode())
                .name(product.getName())
                .category(product.getCategory())
                .competitor(product.isCompetitor())
                .customAttributes(product.getCustomAttributes())
                .active(product.isActive())
                .aliases(aliasList)
                .createdAt(product.getCreatedAt())
                .build();
    }
}
