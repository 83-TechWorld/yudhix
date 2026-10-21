package io.yudhix.meter.repository;

import io.yudhix.meter.entity.UsageEvent;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface UsageEventRepository extends JpaRepository<UsageEvent, UUID> {

    Optional<UsageEvent> findByTenantIdAndMetricTypeAndIdempotencyKey(UUID tenantId, String metricType, String idempotencyKey);

    @Query("SELECT COALESCE(SUM(u.quantity), 0) FROM UsageEvent u WHERE u.tenantId = :tenantId AND u.metricType = :metricType AND u.recordedAt >= :start AND u.recordedAt < :end")
    long sumUsageInPeriod(@Param("tenantId") UUID tenantId,
                          @Param("metricType") String metricType,
                          @Param("start") Instant start,
                          @Param("end") Instant end);
}
