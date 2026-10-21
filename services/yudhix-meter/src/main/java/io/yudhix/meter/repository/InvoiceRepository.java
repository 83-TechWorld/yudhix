package io.yudhix.meter.repository;

import io.yudhix.meter.entity.Invoice;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface InvoiceRepository extends JpaRepository<Invoice, UUID> {

    Optional<Invoice> findByTenantIdAndBillingPeriod(UUID tenantId, String billingPeriod);

    Page<Invoice> findByTenantIdOrderByIssuedAtDesc(UUID tenantId, Pageable pageable);
}
