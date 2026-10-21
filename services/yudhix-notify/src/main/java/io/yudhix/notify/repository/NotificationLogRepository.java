package io.yudhix.notify.repository;

import io.yudhix.notify.entity.NotificationLog;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.UUID;

@Repository
public interface NotificationLogRepository extends JpaRepository<NotificationLog, Long> {

    Page<NotificationLog> findByTenantIdOrderByDispatchedAtDesc(UUID tenantId, Pageable pageable);
}
