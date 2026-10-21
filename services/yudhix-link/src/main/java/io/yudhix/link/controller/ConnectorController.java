package io.yudhix.link.controller;

import io.yudhix.common.dto.ApiResponse;
import io.yudhix.link.entity.SourceWatermark;
import io.yudhix.link.repository.SourceWatermarkRepository;
import io.yudhix.link.service.ConnectorManagerService;
import io.yudhix.link.service.CredentialVaultService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/connectors")
@RequiredArgsConstructor
public class ConnectorController {

    private final ConnectorManagerService connectorManagerService;
    private final CredentialVaultService credentialVaultService;
    private final SourceWatermarkRepository watermarkRepository;

    @PostMapping("/{sourceId}/fetch")
    public ResponseEntity<ApiResponse<Integer>> triggerFetch(
            @PathVariable UUID sourceId,
            @RequestParam UUID tenantId,
            @RequestParam String platform,
            @RequestParam String externalRef) {

        int stagedCount = connectorManagerService.executeFetch(tenantId, sourceId, platform, externalRef);
        return ResponseEntity.ok(ApiResponse.success("Fetch completed successfully", stagedCount));
    }

    @PostMapping("/credentials")
    public ResponseEntity<ApiResponse<String>> storeCredential(
            @RequestParam UUID tenantId,
            @RequestParam String platform,
            @RequestBody String rawRefreshToken) {

        credentialVaultService.storeCredential(tenantId, platform, rawRefreshToken.trim());
        return ResponseEntity.ok(ApiResponse.success("Credential encrypted and stored securely", platform));
    }

    @GetMapping("/watermarks/{tenantId}")
    public ResponseEntity<ApiResponse<List<SourceWatermark>>> getWatermarks(@PathVariable UUID tenantId) {
        List<SourceWatermark> watermarks = watermarkRepository.findByTenantId(tenantId);
        return ResponseEntity.ok(ApiResponse.success(watermarks));
    }
}
