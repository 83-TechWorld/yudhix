package io.yudhix.dharma.repository;

import io.yudhix.dharma.entity.ConsentRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface ConsentRecordRepository extends JpaRepository<ConsentRecord, UUID> {
    List<ConsentRecord> findByTenantIdAndWithdrawnAtIsNull(UUID tenantId);
    Optional<ConsentRecord> findByTenantIdAndPolicyIdAndWithdrawnAtIsNull(UUID tenantId, UUID policyId);
}
