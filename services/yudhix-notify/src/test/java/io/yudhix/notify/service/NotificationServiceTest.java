package io.yudhix.notify.service;

import io.yudhix.common.context.TenantContext;
import io.yudhix.common.context.TenantContextHolder;
import io.yudhix.notify.dto.CreateRuleRequest;
import io.yudhix.notify.dto.SendAlertRequest;
import io.yudhix.notify.entity.NotificationLog;
import io.yudhix.notify.entity.NotificationRule;
import io.yudhix.notify.repository.NotificationLogRepository;
import io.yudhix.notify.repository.NotificationRuleRepository;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;

import java.math.BigDecimal;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class NotificationServiceTest {

    @Mock
    private NotificationRuleRepository ruleRepository;

    @Mock
    private NotificationLogRepository logRepository;

    @Mock
    private JavaMailSender mailSender;

    @InjectMocks
    private NotificationService notificationService;

    private final UUID tenantId = UUID.randomUUID();

    @BeforeEach
    void setUp() {
        TenantContextHolder.setContext(TenantContext.builder()
                .tenantId(tenantId)
                .userId(UUID.randomUUID())
                .countryCode("IN")
                .build());
    }

    @AfterEach
    void tearDown() {
        TenantContextHolder.clear();
    }

    @Test
    void testCreateRule() {
        CreateRuleRequest req = CreateRuleRequest.builder()
                .name("Crisis Alert - Viral Negative Spike")
                .ruleType("CRISIS_SPIKE")
                .thresholdValue(new BigDecimal("30.00"))
                .channel("EMAIL")
                .targetDestination("incident-team@example.com")
                .build();

        when(ruleRepository.save(any(NotificationRule.class))).thenAnswer(i -> i.getArgument(0));

        NotificationRule rule = notificationService.createRule(req);

        assertNotNull(rule);
        assertEquals("CRISIS_SPIKE", rule.getRuleType());
        assertEquals(tenantId, rule.getTenantId());
    }

    @Test
    void testDispatchAlertSendsEmail() {
        SendAlertRequest req = SendAlertRequest.builder()
                .eventType("CRISIS_SPIKE")
                .severity("CRITICAL")
                .recipient("security-ops@example.com")
                .subject("Immediate Action: Viral Negative Spike detected on YouTube")
                .body("Negative sentiment jumped 45% in the last hour on Product PS5.")
                .build();

        when(logRepository.save(any(NotificationLog.class))).thenAnswer(i -> i.getArgument(0));

        NotificationLog log = notificationService.dispatchAlert(req);

        assertNotNull(log);
        assertEquals("SENT", log.getStatus());
        verify(mailSender, times(1)).send(any(SimpleMailMessage.class));
    }
}
