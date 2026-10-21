package io.yudhix.dharma.repository;

import io.yudhix.dharma.entity.DsrRequest;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface DsrRequestRepository extends JpaRepository<DsrRequest, UUID> {
    List<DsrRequest> findByTenantId(UUID tenantId);
    List<DsrRequest> findByTenantIdAndStatus(UUID tenantId, String status);
}
