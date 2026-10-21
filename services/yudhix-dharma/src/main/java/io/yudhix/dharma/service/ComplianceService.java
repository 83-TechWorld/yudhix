package io.yudhix.dharma.service;

import io.yudhix.common.exception.ApiException;
import io.yudhix.dharma.dto.ConsentAcceptanceRequest;
import io.yudhix.dharma.dto.ConsentRecordDto;
import io.yudhix.dharma.dto.DsrRequestDto;
import io.yudhix.dharma.dto.PolicyDocumentDto;
import io.yudhix.dharma.entity.ConsentRecord;
import io.yudhix.dharma.entity.DsrRequest;
import io.yudhix.dharma.entity.PolicyDocument;
import io.yudhix.dharma.repository.ConsentRecordRepository;
import io.yudhix.dharma.repository.DsrRequestRepository;
import io.yudhix.dharma.repository.PolicyDocumentRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class ComplianceService {

    private final PolicyDocumentRepository policyRepository;
    private final ConsentRecordRepository consentRepository;
    private final DsrRequestRepository dsrRepository;

    @Transactional(readOnly = true)
    public List<PolicyDocumentDto> getApplicablePolicies(List<String> countryCodes) {
        List<String> codes = (countryCodes == null || countryCodes.isEmpty()) ? List.of() : countryCodes;
        return policyRepository.findApplicablePolicies(codes).stream()
                .map(PolicyDocumentDto::from)
                .collect(Collectors.toList());
    }

    @Transactional
    public ConsentRecordDto recordConsent(ConsentAcceptanceRequest request) {
        log.info("Recording consent for tenant: {}, policy: {}", request.getTenantId(), request.getPolicyId());

        PolicyDocument policy = policyRepository.findById(request.getPolicyId())
                .orElseThrow(() -> new ApiException("Policy document not found: " + request.getPolicyId(),
                        HttpStatus.NOT_FOUND, "POLICY_NOT_FOUND"));

        // Cryptographic proof: Ensure hash of presented document matches backend content hash
        if (!policy.getContentHash().equalsIgnoreCase(request.getContentHash().trim())) {
            log.error("Content hash mismatch for policy {}. Expected: {}, Received: {}",
                    policy.getCode(), policy.getContentHash(), request.getContentHash());
            throw new ApiException("Tampered or outdated policy document version rejected",
                    HttpStatus.BAD_REQUEST, "POLICY_HASH_MISMATCH");
        }

        ConsentRecord record = ConsentRecord.builder()
                .tenantId(request.getTenantId())
                .policy(policy)
                .contentHash(policy.getContentHash())
                .acceptedBy(request.getAcceptedBy())
                .signerName(request.getSignerName().trim())
                .signerTitle(request.getSignerTitle())
                .ipHash(request.getIpHash())
                .build();

        ConsentRecord saved = consentRepository.save(record);
        log.info("Consent record stored: id={}, tenant={}", saved.getId(), request.getTenantId());
        return ConsentRecordDto.from(saved);
    }

    @Transactional(readOnly = true)
    public List<ConsentRecordDto> getConsentHistory(UUID tenantId) {
        return consentRepository.findByTenantIdAndWithdrawnAtIsNull(tenantId).stream()
                .map(ConsentRecordDto::from)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public boolean isTenantCompliant(UUID tenantId, List<String> operatingCountries) {
        List<PolicyDocument> mandatoryPolicies = policyRepository.findApplicablePolicies(operatingCountries).stream()
                .filter(PolicyDocument::isMandatory)
                .toList();

        Set<UUID> acceptedPolicyIds = consentRepository.findByTenantIdAndWithdrawnAtIsNull(tenantId).stream()
                .map(c -> c.getPolicy().getId())
                .collect(Collectors.toSet());

        return mandatoryPolicies.stream()
                .allMatch(p -> acceptedPolicyIds.contains(p.getId()));
    }

    @Transactional
    public DsrRequestDto createDsrRequest(DsrRequestDto dto) {
        DsrRequest request = DsrRequest.builder()
                .tenantId(dto.getTenantId())
                .platform(dto.getPlatform().toUpperCase())
                .authorHash(dto.getAuthorHash().trim())
                .requestType(dto.getRequestType().toUpperCase())
                .status("PENDING")
                .build();

        DsrRequest saved = dsrRepository.save(request);
        log.info("Created DSR request id={} for tenant={}", saved.getId(), saved.getTenantId());
        return DsrRequestDto.from(saved);
    }

    @Transactional
    public DsrRequestDto completeDsrRequest(UUID dsrId) {
        DsrRequest request = dsrRepository.findById(dsrId)
                .orElseThrow(() -> new ApiException("DSR request not found: " + dsrId, HttpStatus.NOT_FOUND, "DSR_NOT_FOUND"));

        request.setStatus("COMPLETED");
        request.setCompletedAt(Instant.now());
        DsrRequest saved = dsrRepository.save(request);
        log.info("DSR request id={} completed", dsrId);
        return DsrRequestDto.from(saved);
    }

    @Transactional(readOnly = true)
    public List<DsrRequestDto> getDsrRequests(UUID tenantId) {
        return dsrRepository.findByTenantId(tenantId).stream()
                .map(DsrRequestDto::from)
                .collect(Collectors.toList());
    }
}
