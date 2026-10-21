package io.yudhix.ledger.service;

import io.yudhix.ledger.dto.AuditEventRequest;
import io.yudhix.ledger.dto.AuditEventResponse;
import io.yudhix.ledger.dto.ChainVerificationResult;
import io.yudhix.ledger.entity.AuditEvent;
import io.yudhix.ledger.repository.AuditEventRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AuditChainingServiceTest {

    @Mock
    private AuditEventRepository auditRepository;

    @InjectMocks
    private AuditChainingService auditService;

    @Test
    void testAuditChainingGeneratesValidLinks() {
        UUID tenantId = UUID.randomUUID();

        when(auditRepository.findTopByTenantIdOrderByIdDesc(tenantId)).thenReturn(Optional.empty());
        when(auditRepository.save(any(AuditEvent.class))).thenAnswer(i -> {
            AuditEvent e = i.getArgument(0);
            e.setId(1L);
            return e;
        });

        AuditEventRequest request = AuditEventRequest.builder()
                .tenantId(tenantId)
                .actorId("user-123")
                .actorType("USER")
                .action("TENANT_ONBOARDED")
                .entityType("TENANT")
                .entityId(tenantId.toString())
                .afterState("{\"status\":\"ACTIVE\"}")
                .build();

        AuditEventResponse response = auditService.recordEvent(request);

        assertNotNull(response);
        assertEquals(AuditChainingService.GENESIS_HASH, response.getPrevHash());
        assertNotNull(response.getRowHash());
        assertEquals(64, response.getRowHash().length());
    }

    @Test
    void testVerificationDetectsIntactChain() {
        UUID tenantId = UUID.randomUUID();
        Instant now = Instant.now();

        String prevHash = AuditChainingService.GENESIS_HASH;
        String rowHash1 = AuditChainingService.calculateRowHash(
                prevHash, tenantId, now, "admin-1", "LOGIN", "session-1", "{}"
        );

        AuditEvent event1 = AuditEvent.builder()
                .id(1L)
                .tenantId(tenantId)
                .occurredAt(now)
                .actorId("admin-1")
                .action("LOGIN")
                .entityId("session-1")
                .afterState("{}")
                .prevHash(prevHash)
                .rowHash(rowHash1)
                .build();

        when(auditRepository.findByTenantIdOrderByIdAsc(tenantId)).thenReturn(List.of(event1));

        ChainVerificationResult result = auditService.verifyChain(tenantId);
        assertTrue(result.isValid());
        assertEquals(1, result.getTotalEventsVerified());
    }

    @Test
    void testVerificationDetectsTamperedData() {
        UUID tenantId = UUID.randomUUID();
        Instant now = Instant.now();

        String prevHash = AuditChainingService.GENESIS_HASH;
        String validRowHash = AuditChainingService.calculateRowHash(
                prevHash, tenantId, now, "admin-1", "LOGIN", "session-1", "{}"
        );

        // Record with altered afterState without recomputing row_hash
        AuditEvent tamperedEvent = AuditEvent.builder()
                .id(1L)
                .tenantId(tenantId)
                .occurredAt(now)
                .actorId("admin-1")
                .action("LOGIN")
                .entityId("session-1")
                .afterState("{\"TAMPERED\": true}")
                .prevHash(prevHash)
                .rowHash(validRowHash)
                .build();

        when(auditRepository.findByTenantIdOrderByIdAsc(tenantId)).thenReturn(List.of(tamperedEvent));

        ChainVerificationResult result = auditService.verifyChain(tenantId);
        assertFalse(result.isValid());
        assertEquals(1L, result.getCorruptedEventId());
        assertTrue(result.getDetails().contains("Data tampering detected"));
    }
}
