package io.yudhix.meter.service;

import io.yudhix.common.context.TenantContextHolder;
import io.yudhix.common.exception.ApiException;
import io.yudhix.common.exception.ResourceNotFoundException;
import io.yudhix.meter.dto.QuotaStatusResponse;
import io.yudhix.meter.dto.RecordUsageRequest;
import io.yudhix.meter.dto.SubscribePlanRequest;
import io.yudhix.meter.entity.Invoice;
import io.yudhix.meter.entity.Plan;
import io.yudhix.meter.entity.Subscription;
import io.yudhix.meter.entity.UsageEvent;
import io.yudhix.meter.repository.InvoiceRepository;
import io.yudhix.meter.repository.PlanRepository;
import io.yudhix.meter.repository.SubscriptionRepository;
import io.yudhix.meter.repository.UsageEventRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Optional;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class BillingService {

    private final PlanRepository planRepository;
    private final SubscriptionRepository subscriptionRepository;
    private final UsageEventRepository usageEventRepository;
    private final InvoiceRepository invoiceRepository;

    @Transactional
    public UsageEvent recordUsage(RecordUsageRequest req) {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();

        // Check idempotency
        Optional<UsageEvent> existing = usageEventRepository.findByTenantIdAndMetricTypeAndIdempotencyKey(
                tenantId, req.getMetricType(), req.getIdempotencyKey());

        if (existing.isPresent()) {
            return existing.get();
        }

        UsageEvent event = UsageEvent.builder()
                .id(UUID.randomUUID())
                .tenantId(tenantId)
                .metricType(req.getMetricType())
                .quantity(req.getQuantity() > 0 ? req.getQuantity() : 1)
                .idempotencyKey(req.getIdempotencyKey())
                .recordedAt(Instant.now())
                .build();

        return usageEventRepository.save(event);
    }

    @Transactional
    public Subscription subscribe(SubscribePlanRequest req) {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();

        Plan plan = planRepository.findById(req.getPlanId())
                .orElseThrow(() -> new ResourceNotFoundException("Plan not found: " + req.getPlanId()));

        Instant now = Instant.now();
        Instant periodEnd = now.plus(30, ChronoUnit.DAYS);

        Subscription sub = subscriptionRepository.findByTenantId(tenantId)
                .map(existing -> {
                    existing.setPlan(plan);
                    existing.setStatus("ACTIVE");
                    existing.setPaymentMethodId(req.getPaymentMethodId());
                    existing.setUpdatedAt(now);
                    return existing;
                })
                .orElse(Subscription.builder()
                        .tenantId(tenantId)
                        .plan(plan)
                        .status("ACTIVE")
                        .currentPeriodStart(now)
                        .currentPeriodEnd(periodEnd)
                        .paymentMethodId(req.getPaymentMethodId())
                        .createdAt(now)
                        .updatedAt(now)
                        .build());

        return subscriptionRepository.save(sub);
    }

    @Transactional(readOnly = true)
    public QuotaStatusResponse checkQuota() {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();
        Subscription sub = subscriptionRepository.findByTenantId(tenantId)
                .orElseThrow(() -> new ApiException("Tenant has no active subscription", HttpStatus.PAYMENT_REQUIRED, "NO_ACTIVE_SUBSCRIPTION"));

        Plan plan = sub.getPlan();
        Instant start = sub.getCurrentPeriodStart();
        Instant end = sub.getCurrentPeriodEnd();

        long comments = usageEventRepository.sumUsageInPeriod(tenantId, "comments_ingested", start, end);
        long llm = usageEventRepository.sumUsageInPeriod(tenantId, "comments_llm_analyzed", start, end);
        long replies = usageEventRepository.sumUsageInPeriod(tenantId, "replies_posted", start, end);

        boolean exceeded = (plan.getCommentQuota() > 0 && comments >= plan.getCommentQuota()) ||
                           (plan.getLlmQuota() > 0 && llm >= plan.getLlmQuota()) ||
                           (plan.getReplyQuota() > 0 && replies >= plan.getReplyQuota());

        return QuotaStatusResponse.builder()
                .planId(plan.getId())
                .planName(plan.getName())
                .commentsIngested(comments)
                .commentQuota(plan.getCommentQuota())
                .llmAnalyzed(llm)
                .llmQuota(plan.getLlmQuota())
                .repliesPosted(replies)
                .replyQuota(plan.getReplyQuota())
                .quotaExceeded(exceeded)
                .build();
    }

    @Transactional
    public Invoice generateMonthlyInvoice(String billingPeriod) {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();
        Subscription sub = subscriptionRepository.findByTenantId(tenantId)
                .orElseThrow(() -> new ApiException("No subscription found", HttpStatus.BAD_REQUEST, "NO_SUBSCRIPTION"));

        Plan plan = sub.getPlan();

        Invoice invoice = Invoice.builder()
                .id(UUID.randomUUID())
                .tenantId(tenantId)
                .billingPeriod(billingPeriod)
                .subtotal(plan.getMonthlyPrice())
                .tax(plan.getMonthlyPrice().multiply(java.math.BigDecimal.valueOf(0.18))) // 18% GST/VAT
                .total(plan.getMonthlyPrice().multiply(java.math.BigDecimal.valueOf(1.18)))
                .currency(plan.getCurrency())
                .status("ISSUED")
                .issuedAt(Instant.now())
                .build();

        return invoiceRepository.save(invoice);
    }

    @Transactional(readOnly = true)
    public Page<Invoice> listInvoices(Pageable pageable) {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();
        return invoiceRepository.findByTenantIdOrderByIssuedAtDesc(tenantId, pageable);
    }
}
