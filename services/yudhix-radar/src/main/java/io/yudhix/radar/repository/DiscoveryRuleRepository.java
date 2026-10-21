package io.yudhix.radar.repository;

import io.yudhix.radar.entity.DiscoveryRule;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface DiscoveryRuleRepository extends JpaRepository<DiscoveryRule, UUID> {
    List<DiscoveryRule> findByTenantId(UUID tenantId);
    List<DiscoveryRule> findByTenantIdAndEnabledTrue(UUID tenantId);
}
