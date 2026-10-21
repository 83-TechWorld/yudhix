package io.yudhix.ledger.service;

import io.yudhix.ledger.dto.AuditEventRequest;
import io.yudhix.ledger.dto.AuditEventResponse;
import io.yudhix.ledger.dto.ChainVerificationResult;
import io.yudhix.ledger.entity.AuditEvent;
import io.yudhix.ledger.repository.AuditEventRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.HexFormat;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class AuditChainingService {

    public static final String GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000";
    private final AuditEventRepository auditRepository;

    @Transactional
    public synchronized AuditEventResponse recordEvent(AuditEventRequest request) {
        UUID tenantId = request.getTenantId();

        // 1. Determine previous hash in the tenant chain
        String prevHash = auditRepository.findTopByTenantIdOrderByIdDesc(tenantId)
                .map(AuditEvent::getRowHash)
                .orElse(GENESIS_HASH);

        Instant occurredAt = Instant.now();

        // 2. Compute SHA-256 cryptographic row hash
        String rowHash = calculateRowHash(
                prevHash,
                tenantId,
                occurredAt,
                request.getActorId(),
                request.getAction(),
                request.getEntityId(),
                request.getAfterState()
        );

        AuditEvent event = AuditEvent.builder()
                .tenantId(tenantId)
                .occurredAt(occurredAt)
                .actorId(request.getActorId())
                .actorType(request.getActorType())
                .action(request.getAction())
                .entityType(request.getEntityType())
                .entityId(request.getEntityId())
                .beforeState(request.getBeforeState())
                .afterState(request.getAfterState())
                .ipHash(request.getIpHash())
                .userAgent(request.getUserAgent())
                .prevHash(prevHash)
                .rowHash(rowHash)
                .build();

        AuditEvent saved = auditRepository.save(event);
        log.info("Recorded audit event id={} action={} for tenant={}", saved.getId(), saved.getAction(), tenantId);
        return AuditEventResponse.from(saved);
    }

    @Transactional(readOnly = true)
    public ChainVerificationResult verifyChain(UUID tenantId) {
        log.info("Verifying cryptographic audit chain for tenant: {}", tenantId);
        List<AuditEvent> events = auditRepository.findByTenantIdOrderByIdAsc(tenantId);

        if (events.isEmpty()) {
            return ChainVerificationResult.success(tenantId, 0);
        }

        String expectedPrevHash = GENESIS_HASH;

        for (AuditEvent event : events) {
            // Check linkage: Does this event's prev_hash match the previous event's row_hash?
            if (!event.getPrevHash().equals(expectedPrevHash)) {
                log.error("Broken chain link at event id={}. Expected prevHash={}, but found {}",
                        event.getId(), expectedPrevHash, event.getPrevHash());
                return ChainVerificationResult.tampered(
                        tenantId,
                        event.getId(),
                        "Broken chain linkage: prev_hash does not match previous block hash."
                );
            }

            // Check integrity: Recompute row_hash from raw fields
            String recomputedHash = calculateRowHash(
                    event.getPrevHash(),
                    event.getTenantId(),
                    event.getOccurredAt(),
                    event.getActorId(),
                    event.getAction(),
                    event.getEntityId(),
                    event.getAfterState()
            );

            if (!event.getRowHash().equals(recomputedHash)) {
                log.error("Tampered content detected at event id={}. Stored rowHash={}, but recomputed={}",
                        event.getId(), event.getRowHash(), recomputedHash);
                return ChainVerificationResult.tampered(
                        tenantId,
                        event.getId(),
                        "Data tampering detected: record content has been modified after hashing."
                );
            }

            expectedPrevHash = event.getRowHash();
        }

        log.info("Audit chain successfully verified for tenant {} ({} events).", tenantId, events.size());
        return ChainVerificationResult.success(tenantId, events.size());
    }

    @Transactional(readOnly = true)
    public Page<AuditEventResponse> getAuditEvents(UUID tenantId, Pageable pageable) {
        return auditRepository.findByTenantIdOrderByOccurredAtDesc(tenantId, pageable)
                .map(AuditEventResponse::from);
    }

    public static String calculateRowHash(
            String prevHash,
            UUID tenantId,
            Instant occurredAt,
            String actorId,
            String action,
            String entityId,
            String afterState) {

        String payload = (prevHash != null ? prevHash : "") + "|"
                + (tenantId != null ? tenantId.toString() : "") + "|"
                + (occurredAt != null ? occurredAt.toEpochMilli() : 0) + "|"
                + (actorId != null ? actorId : "") + "|"
                + (action != null ? action : "") + "|"
                + (entityId != null ? entityId : "") + "|"
                + (afterState != null ? afterState.trim() : "");

        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hashBytes = digest.digest(payload.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hashBytes);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 algorithm missing", e);
        }
    }
}
