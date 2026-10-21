package io.yudhix.tenant.controller;

import io.yudhix.common.dto.ApiResponse;
import io.yudhix.tenant.dto.TenantRegistrationRequest;
import io.yudhix.tenant.dto.TenantResponse;
import io.yudhix.tenant.dto.TenantSettingDto;
import io.yudhix.tenant.service.TenantService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/tenants")
@RequiredArgsConstructor
public class TenantController {

    private final TenantService tenantService;

    @PostMapping("/register")
    public ResponseEntity<ApiResponse<TenantResponse>> registerTenant(@Valid @RequestBody TenantRegistrationRequest request) {
        TenantResponse response = tenantService.registerTenant(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success("Tenant registered successfully", response));
    }

    @GetMapping("/{tenantId}")
    public ResponseEntity<ApiResponse<TenantResponse>> getTenant(@PathVariable UUID tenantId) {
        TenantResponse response = tenantService.getTenantById(tenantId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @GetMapping("/by-slug/{slug}")
    public ResponseEntity<ApiResponse<TenantResponse>> getTenantBySlug(@PathVariable String slug) {
        TenantResponse response = tenantService.getTenantBySlug(slug);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @PatchMapping("/{tenantId}/status")
    public ResponseEntity<ApiResponse<TenantResponse>> updateStatus(@PathVariable UUID tenantId, @RequestParam String status) {
        TenantResponse response = tenantService.updateStatus(tenantId, status);
        return ResponseEntity.ok(ApiResponse.success("Tenant status updated", response));
    }

    @GetMapping("/{tenantId}/settings")
    public ResponseEntity<ApiResponse<List<TenantSettingDto>>> getSettings(@PathVariable UUID tenantId) {
        List<TenantSettingDto> settings = tenantService.getSettings(tenantId);
        return ResponseEntity.ok(ApiResponse.success(settings));
    }

    @PutMapping("/{tenantId}/settings")
    public ResponseEntity<ApiResponse<TenantSettingDto>> updateSetting(
            @PathVariable UUID tenantId,
            @Valid @RequestBody TenantSettingDto dto) {
        TenantSettingDto saved = tenantService.saveSetting(tenantId, dto);
        return ResponseEntity.ok(ApiResponse.success("Setting updated", saved));
    }
}
