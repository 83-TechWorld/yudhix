package io.yudhix.ledger.repository;

import io.yudhix.ledger.entity.AuditEvent;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface AuditEventRepository extends JpaRepository<AuditEvent, Long> {

    Optional<AuditEvent> findTopByTenantIdOrderByIdDesc(UUID tenantId);

    List<AuditEvent> findByTenantIdOrderByIdAsc(UUID tenantId);

    Page<AuditEvent> findByTenantIdOrderByOccurredAtDesc(UUID tenantId, Pageable pageable);
}
