package io.yudhix.catalog.service;

import io.yudhix.catalog.dto.OwnedSourceRequest;
import io.yudhix.catalog.dto.OwnedSourceResponse;
import io.yudhix.catalog.dto.ProductRequest;
import io.yudhix.catalog.dto.ProductResponse;
import io.yudhix.catalog.entity.OwnedSource;
import io.yudhix.catalog.entity.Product;
import io.yudhix.catalog.entity.ProductAlias;
import io.yudhix.catalog.repository.OwnedSourceRepository;
import io.yudhix.catalog.repository.ProductAliasRepository;
import io.yudhix.catalog.repository.ProductRepository;
import io.yudhix.common.exception.ApiException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class CatalogService {

    private final ProductRepository productRepository;
    private final ProductAliasRepository aliasRepository;
    private final OwnedSourceRepository sourceRepository;

    @Transactional
    public ProductResponse createProduct(ProductRequest request) {
        log.info("Creating product '{}' ({}) for tenant {}", request.getName(), request.getCode(), request.getTenantId());

        if (productRepository.existsByTenantIdAndCode(request.getTenantId(), request.getCode())) {
            throw new ApiException("Product with code '" + request.getCode() + "' already exists for this tenant",
                    HttpStatus.CONFLICT, "PRODUCT_CODE_CONFLICT");
        }

        Product product = Product.builder()
                .tenantId(request.getTenantId())
                .code(request.getCode().trim().toLowerCase())
                .name(request.getName().trim())
                .category(request.getCategory())
                .competitor(request.isCompetitor())
                .customAttributes(request.getCustomAttributes() != null ? request.getCustomAttributes() : "{}")
                .active(true)
                .build();

        if (request.getAliases() != null) {
            for (String aliasText : request.getAliases()) {
                if (aliasText != null && !aliasText.isBlank()) {
                    ProductAlias alias = ProductAlias.builder()
                            .tenantId(request.getTenantId())
                            .product(product)
                            .alias(aliasText.trim())
                            .build();
                    product.getAliases().add(alias);
                }
            }
        }

        Product saved = productRepository.save(product);
        return ProductResponse.from(saved);
    }

    @Transactional(readOnly = true)
    public List<ProductResponse> getProductsByTenant(UUID tenantId) {
        return productRepository.findByTenantId(tenantId).stream()
                .map(ProductResponse::from)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public ProductResponse getProductById(UUID productId) {
        return productRepository.findById(productId)
                .map(ProductResponse::from)
                .orElseThrow(() -> new ApiException("Product not found: " + productId, HttpStatus.NOT_FOUND, "PRODUCT_NOT_FOUND"));
    }

    @Transactional
    public OwnedSourceResponse createOwnedSource(OwnedSourceRequest request) {
        log.info("Adding owned source {} ({}) for tenant {}", request.getExternalRef(), request.getPlatform(), request.getTenantId());

        OwnedSource source = OwnedSource.builder()
                .tenantId(request.getTenantId())
                .platform(request.getPlatform().toUpperCase())
                .sourceType(request.getSourceType().toUpperCase())
                .externalRef(request.getExternalRef().trim())
                .productIds(request.getProductIds() != null ? request.getProductIds() : new ArrayList<>())
                .scheduleCron(request.getScheduleCron() != null ? request.getScheduleCron() : "0 */6 * * *")
                .enabled(request.getEnabled() != null ? request.getEnabled() : true)
                .build();

        OwnedSource saved = sourceRepository.save(source);
        return OwnedSourceResponse.from(saved);
    }

    @Transactional(readOnly = true)
    public List<OwnedSourceResponse> getOwnedSources(UUID tenantId) {
        return sourceRepository.findByTenantId(tenantId).stream()
                .map(OwnedSourceResponse::from)
                .collect(Collectors.toList());
    }
}
