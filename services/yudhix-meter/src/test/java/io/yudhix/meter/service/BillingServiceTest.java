package io.yudhix.meter.service;

import io.yudhix.common.context.TenantContext;
import io.yudhix.common.context.TenantContextHolder;
import io.yudhix.meter.dto.QuotaStatusResponse;
import io.yudhix.meter.dto.RecordUsageRequest;
import io.yudhix.meter.dto.SubscribePlanRequest;
import io.yudhix.meter.entity.Plan;
import io.yudhix.meter.entity.Subscription;
import io.yudhix.meter.entity.UsageEvent;
import io.yudhix.meter.repository.InvoiceRepository;
import io.yudhix.meter.repository.PlanRepository;
import io.yudhix.meter.repository.SubscriptionRepository;
import io.yudhix.meter.repository.UsageEventRepository;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class BillingServiceTest {

    @Mock
    private PlanRepository planRepository;

    @Mock
    private SubscriptionRepository subscriptionRepository;

    @Mock
    private UsageEventRepository usageEventRepository;

    @Mock
    private InvoiceRepository invoiceRepository;

    @InjectMocks
    private BillingService billingService;

    private final UUID tenantId = UUID.randomUUID();

    @BeforeEach
    void setUp() {
        TenantContextHolder.setContext(TenantContext.builder()
                .tenantId(tenantId)
                .userId(UUID.randomUUID())
                .countryCode("US")
                .build());
    }

    @AfterEach
    void tearDown() {
        TenantContextHolder.clear();
    }

    @Test
    void testIdempotentUsageRecording() {
        RecordUsageRequest req = RecordUsageRequest.builder()
                .metricType("comments_ingested")
                .quantity(5)
                .idempotencyKey("batch_abc_123")
                .build();

        UsageEvent existing = UsageEvent.builder()
                .id(UUID.randomUUID())
                .tenantId(tenantId)
                .metricType(req.getMetricType())
                .quantity(5)
                .idempotencyKey(req.getIdempotencyKey())
                .build();

        when(usageEventRepository.findByTenantIdAndMetricTypeAndIdempotencyKey(tenantId, "comments_ingested", "batch_abc_123"))
                .thenReturn(Optional.of(existing));

        UsageEvent result = billingService.recordUsage(req);

        assertEquals(existing.getId(), result.getId());
        verify(usageEventRepository, never()).save(any());
    }

    @Test
    void testQuotaCheckDetectsExceededLimit() {
        Plan starter = Plan.builder()
                .id("STARTER")
                .name("Starter Tier")
                .monthlyPrice(new BigDecimal("99.00"))
                .commentQuota(1000)
                .llmQuota(200)
                .replyQuota(50)
                .build();

        Subscription sub = Subscription.builder()
                .tenantId(tenantId)
                .plan(starter)
                .status("ACTIVE")
                .currentPeriodStart(Instant.now().minusSeconds(86400 * 10))
                .currentPeriodEnd(Instant.now().plusSeconds(86400 * 20))
                .build();

        when(subscriptionRepository.findByTenantId(tenantId)).thenReturn(Optional.of(sub));
        when(usageEventRepository.sumUsageInPeriod(eq(tenantId), eq("comments_ingested"), any(), any())).thenReturn(1050L);
        when(usageEventRepository.sumUsageInPeriod(eq(tenantId), eq("comments_llm_analyzed"), any(), any())).thenReturn(50L);
        when(usageEventRepository.sumUsageInPeriod(eq(tenantId), eq("replies_posted"), any(), any())).thenReturn(10L);

        QuotaStatusResponse quota = billingService.checkQuota();

        assertTrue(quota.isQuotaExceeded(), "Quota should be marked as exceeded when comment usage (1050) exceeds quota (1000)");
        assertEquals(1050L, quota.getCommentsIngested());
    }
}
