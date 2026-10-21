package io.yudhix.meter.controller;

import io.yudhix.common.dto.ApiResponse;
import io.yudhix.common.dto.PageResponse;
import io.yudhix.meter.dto.QuotaStatusResponse;
import io.yudhix.meter.dto.RecordUsageRequest;
import io.yudhix.meter.dto.SubscribePlanRequest;
import io.yudhix.meter.entity.Invoice;
import io.yudhix.meter.entity.Subscription;
import io.yudhix.meter.entity.UsageEvent;
import io.yudhix.meter.service.BillingService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/meter")
@RequiredArgsConstructor
public class BillingController {

    private final BillingService billingService;

    @PostMapping("/usage")
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<UsageEvent> recordUsage(@Valid @RequestBody RecordUsageRequest request) {
        UsageEvent event = billingService.recordUsage(request);
        return ApiResponse.success("Usage event recorded", event);
    }

    @PostMapping("/subscribe")
    public ApiResponse<Subscription> subscribe(@Valid @RequestBody SubscribePlanRequest request) {
        Subscription sub = billingService.subscribe(request);
        return ApiResponse.success("Subscription updated successfully", sub);
    }

    @GetMapping("/quota")
    public ApiResponse<QuotaStatusResponse> checkQuota() {
        QuotaStatusResponse quota = billingService.checkQuota();
        return ApiResponse.success(quota);
    }

    @PostMapping("/invoices/generate")
    public ApiResponse<Invoice> generateInvoice(@RequestParam String period) {
        Invoice invoice = billingService.generateMonthlyInvoice(period);
        return ApiResponse.success("Invoice generated successfully", invoice);
    }

    @GetMapping("/invoices")
    public ApiResponse<PageResponse<Invoice>> listInvoices(@PageableDefault(size = 20) Pageable pageable) {
        Page<Invoice> page = billingService.listInvoices(pageable);
        PageResponse<Invoice> response = PageResponse.<Invoice>builder()
                .content(page.getContent())
                .page(page.getNumber())
                .size(page.getSize())
                .totalElements(page.getTotalElements())
                .totalPages(page.getTotalPages())
                .hasNext(page.hasNext())
                .build();
        return ApiResponse.success(response);
    }
}
