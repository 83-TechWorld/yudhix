package io.yudhix.catalog.controller;

import io.yudhix.catalog.dto.OwnedSourceRequest;
import io.yudhix.catalog.dto.OwnedSourceResponse;
import io.yudhix.catalog.dto.ProductRequest;
import io.yudhix.catalog.dto.ProductResponse;
import io.yudhix.catalog.service.CatalogService;
import io.yudhix.common.dto.ApiResponse;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/catalog")
@RequiredArgsConstructor
public class CatalogController {

    private final CatalogService catalogService;

    @PostMapping("/products")
    public ResponseEntity<ApiResponse<ProductResponse>> createProduct(@Valid @RequestBody ProductRequest request) {
        ProductResponse response = catalogService.createProduct(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success("Product created", response));
    }

    @GetMapping("/products/tenant/{tenantId}")
    public ResponseEntity<ApiResponse<List<ProductResponse>>> getProducts(@PathVariable UUID tenantId) {
        List<ProductResponse> products = catalogService.getProductsByTenant(tenantId);
        return ResponseEntity.ok(ApiResponse.success(products));
    }

    @GetMapping("/products/{productId}")
    public ResponseEntity<ApiResponse<ProductResponse>> getProduct(@PathVariable UUID productId) {
        ProductResponse product = catalogService.getProductById(productId);
        return ResponseEntity.ok(ApiResponse.success(product));
    }

    @PostMapping("/sources")
    public ResponseEntity<ApiResponse<OwnedSourceResponse>> createOwnedSource(@Valid @RequestBody OwnedSourceRequest request) {
        OwnedSourceResponse response = catalogService.createOwnedSource(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success("Source configured", response));
    }

    @GetMapping("/sources/tenant/{tenantId}")
    public ResponseEntity<ApiResponse<List<OwnedSourceResponse>>> getOwnedSources(@PathVariable UUID tenantId) {
        List<OwnedSourceResponse> sources = catalogService.getOwnedSources(tenantId);
        return ResponseEntity.ok(ApiResponse.success(sources));
    }
}
