package io.yudhix.dharma.controller;

import io.yudhix.common.dto.ApiResponse;
import io.yudhix.dharma.dto.DsrRequestDto;
import io.yudhix.dharma.service.ComplianceService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/dsr")
@RequiredArgsConstructor
public class DsrController {

    private final ComplianceService complianceService;

    @PostMapping("/requests")
    public ResponseEntity<ApiResponse<DsrRequestDto>> createDsrRequest(@Valid @RequestBody DsrRequestDto dto) {
        DsrRequestDto created = complianceService.createDsrRequest(dto);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success("DSR request registered", created));
    }

    @GetMapping("/requests/{tenantId}")
    public ResponseEntity<ApiResponse<List<DsrRequestDto>>> getDsrRequests(@PathVariable UUID tenantId) {
        List<DsrRequestDto> requests = complianceService.getDsrRequests(tenantId);
        return ResponseEntity.ok(ApiResponse.success(requests));
    }

    @PatchMapping("/requests/{dsrId}/complete")
    public ResponseEntity<ApiResponse<DsrRequestDto>> completeDsrRequest(@PathVariable UUID dsrId) {
        DsrRequestDto completed = complianceService.completeDsrRequest(dsrId);
        return ResponseEntity.ok(ApiResponse.success("DSR request completed", completed));
    }
}
