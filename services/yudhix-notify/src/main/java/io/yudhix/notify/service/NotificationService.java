package io.yudhix.notify.service;

import io.yudhix.common.context.TenantContextHolder;
import io.yudhix.notify.dto.CreateRuleRequest;
import io.yudhix.notify.dto.SendAlertRequest;
import io.yudhix.notify.entity.NotificationLog;
import io.yudhix.notify.entity.NotificationRule;
import io.yudhix.notify.repository.NotificationLogRepository;
import io.yudhix.notify.repository.NotificationRuleRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class NotificationService {

    private final NotificationRuleRepository ruleRepository;
    private final NotificationLogRepository logRepository;
    private final JavaMailSender mailSender;

    @Transactional
    public NotificationRule createRule(CreateRuleRequest req) {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();

        NotificationRule rule = NotificationRule.builder()
                .id(UUID.randomUUID())
                .tenantId(tenantId)
                .name(req.getName())
                .ruleType(req.getRuleType().toUpperCase())
                .thresholdValue(req.getThresholdValue())
                .channel(req.getChannel().toUpperCase())
                .targetDestination(req.getTargetDestination())
                .active(true)
                .createdAt(Instant.now())
                .build();

        return ruleRepository.save(rule);
    }

    @Transactional(readOnly = true)
    public List<NotificationRule> listRules() {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();
        return ruleRepository.findByTenantIdAndActiveTrue(tenantId);
    }

    @Transactional
    public NotificationLog dispatchAlert(SendAlertRequest req) {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();

        NotificationLog nLog = NotificationLog.builder()
                .tenantId(tenantId)
                .ruleId(req.getRuleId())
                .eventType(req.getEventType())
                .severity(req.getSeverity())
                .recipient(req.getRecipient())
                .subject(req.getSubject())
                .body(req.getBody())
                .status("SENT")
                .dispatchedAt(Instant.now())
                .build();

        try {
            // Send email if recipient looks like email
            if (req.getRecipient().contains("@")) {
                SimpleMailMessage message = new SimpleMailMessage();
                message.setTo(req.getRecipient());
                message.setSubject("[" + req.getSeverity() + "] " + req.getSubject());
                message.setText(req.getBody());
                message.setFrom("alerts@yudhix.io");
                mailSender.send(message);
            }
            log.info("Alert dispatched to recipient: {} for event: {}", req.getRecipient(), req.getEventType());
        } catch (Exception e) {
            log.error("Failed to deliver alert to recipient {}: {}", req.getRecipient(), e.getMessage());
            nLog.setStatus("FAILED");
            nLog.setErrorMessage(e.getMessage());
        }

        return logRepository.save(nLog);
    }
}
