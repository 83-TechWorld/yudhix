package io.yudhix.catalog.repository;

import io.yudhix.catalog.entity.OwnedSource;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface OwnedSourceRepository extends JpaRepository<OwnedSource, UUID> {
    List<OwnedSource> findByTenantId(UUID tenantId);
    List<OwnedSource> findByTenantIdAndPlatform(UUID tenantId, String platform);
    List<OwnedSource> findByEnabledTrue();
}
