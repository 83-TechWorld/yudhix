package io.yudhix.ledger.controller;

import io.yudhix.common.dto.ApiResponse;
import io.yudhix.ledger.dto.AuditEventRequest;
import io.yudhix.ledger.dto.AuditEventResponse;
import io.yudhix.ledger.dto.ChainVerificationResult;
import io.yudhix.ledger.service.AuditChainingService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/api/v1/audit")
@RequiredArgsConstructor
public class AuditController {

    private final AuditChainingService auditService;

    @PostMapping("/events")
    public ResponseEntity<ApiResponse<AuditEventResponse>> recordAuditEvent(
            @Valid @RequestBody AuditEventRequest request) {
        AuditEventResponse response = auditService.recordEvent(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success("Audit event recorded", response));
    }

    @GetMapping("/events/{tenantId}")
    public ResponseEntity<ApiResponse<Page<AuditEventResponse>>> getAuditEvents(
            @PathVariable UUID tenantId,
            @PageableDefault(size = 50) Pageable pageable) {
        Page<AuditEventResponse> page = auditService.getAuditEvents(tenantId, pageable);
        return ResponseEntity.ok(ApiResponse.success(page));
    }

    @GetMapping("/verify/{tenantId}")
    public ResponseEntity<ApiResponse<ChainVerificationResult>> verifyChain(@PathVariable UUID tenantId) {
        ChainVerificationResult result = auditService.verifyChain(tenantId);
        return ResponseEntity.ok(ApiResponse.success("Chain verification complete", result));
    }
}
