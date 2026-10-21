package io.yudhix.dharma.service;

import io.yudhix.common.exception.ApiException;
import io.yudhix.dharma.dto.ConsentAcceptanceRequest;
import io.yudhix.dharma.dto.ConsentRecordDto;
import io.yudhix.dharma.entity.ConsentRecord;
import io.yudhix.dharma.entity.PolicyDocument;
import io.yudhix.dharma.repository.ConsentRecordRepository;
import io.yudhix.dharma.repository.DsrRequestRepository;
import io.yudhix.dharma.repository.PolicyDocumentRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ComplianceServiceTest {

    @Mock
    private PolicyDocumentRepository policyRepository;

    @Mock
    private ConsentRecordRepository consentRepository;

    @Mock
    private DsrRequestRepository dsrRepository;

    @InjectMocks
    private ComplianceService complianceService;

    @Test
    void testConsentRecordedWhenHashMatches() {
        UUID policyId = UUID.randomUUID();
        UUID tenantId = UUID.randomUUID();
        String hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

        PolicyDocument policy = PolicyDocument.builder()
                .id(policyId)
                .code("TOS")
                .title("Master TOS")
                .contentHash(hash)
                .build();

        when(policyRepository.findById(policyId)).thenReturn(Optional.of(policy));
        when(consentRepository.save(any(ConsentRecord.class))).thenAnswer(i -> {
            ConsentRecord r = i.getArgument(0);
            r.setId(UUID.randomUUID());
            return r;
        });

        ConsentAcceptanceRequest request = ConsentAcceptanceRequest.builder()
                .tenantId(tenantId)
                .policyId(policyId)
                .contentHash(hash)
                .acceptedBy("admin-usr")
                .signerName("Sathish Kumar")
                .signerTitle("CTO")
                .build();

        ConsentRecordDto result = complianceService.recordConsent(request);

        assertNotNull(result);
        assertEquals(tenantId, result.getTenantId());
        assertEquals("TOS", result.getPolicyCode());
        assertEquals(hash, result.getContentHash());
    }

    @Test
    void testConsentRejectedWhenHashMismatched() {
        UUID policyId = UUID.randomUUID();
        UUID tenantId = UUID.randomUUID();

        PolicyDocument policy = PolicyDocument.builder()
                .id(policyId)
                .code("TOS")
                .contentHash("correct-content-hash")
                .build();

        when(policyRepository.findById(policyId)).thenReturn(Optional.of(policy));

        ConsentAcceptanceRequest tamperedRequest = ConsentAcceptanceRequest.builder()
                .tenantId(tenantId)
                .policyId(policyId)
                .contentHash("tampered-content-hash")
                .acceptedBy("admin-usr")
                .signerName("Sathish Kumar")
                .build();

        ApiException ex = assertThrows(ApiException.class, () -> complianceService.recordConsent(tamperedRequest));
        assertEquals("POLICY_HASH_MISMATCH", ex.getErrorCode());
    }
}
