package io.yudhix.dharma.controller;

import io.yudhix.common.dto.ApiResponse;
import io.yudhix.dharma.dto.ConsentAcceptanceRequest;
import io.yudhix.dharma.dto.ConsentRecordDto;
import io.yudhix.dharma.dto.PolicyDocumentDto;
import io.yudhix.dharma.service.ComplianceService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/compliance")
@RequiredArgsConstructor
public class ComplianceController {

    private final ComplianceService complianceService;

    @GetMapping("/policies")
    public ResponseEntity<ApiResponse<List<PolicyDocumentDto>>> getApplicablePolicies(
            @RequestParam(required = false) List<String> countries) {
        List<PolicyDocumentDto> policies = complianceService.getApplicablePolicies(countries);
        return ResponseEntity.ok(ApiResponse.success(policies));
    }

    @PostMapping("/consent")
    public ResponseEntity<ApiResponse<ConsentRecordDto>> recordConsent(
            @Valid @RequestBody ConsentAcceptanceRequest request) {
        ConsentRecordDto record = complianceService.recordConsent(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success("Consent recorded successfully", record));
    }

    @GetMapping("/consent/{tenantId}")
    public ResponseEntity<ApiResponse<List<ConsentRecordDto>>> getConsentHistory(@PathVariable UUID tenantId) {
        List<ConsentRecordDto> history = complianceService.getConsentHistory(tenantId);
        return ResponseEntity.ok(ApiResponse.success(history));
    }

    @GetMapping("/status/{tenantId}")
    public ResponseEntity<ApiResponse<Boolean>> checkCompliance(
            @PathVariable UUID tenantId,
            @RequestParam List<String> countries) {
        boolean compliant = complianceService.isTenantCompliant(tenantId, countries);
        return ResponseEntity.ok(ApiResponse.success("Compliance verification status", compliant));
    }
}
