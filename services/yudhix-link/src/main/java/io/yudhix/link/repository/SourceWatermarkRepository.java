package io.yudhix.link.repository;

import io.yudhix.link.entity.SourceWatermark;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface SourceWatermarkRepository extends JpaRepository<SourceWatermark, UUID> {
    List<SourceWatermark> findByTenantId(UUID tenantId);
    Optional<SourceWatermark> findByTenantIdAndSourceIdAndPlatform(UUID tenantId, UUID sourceId, String platform);
}
