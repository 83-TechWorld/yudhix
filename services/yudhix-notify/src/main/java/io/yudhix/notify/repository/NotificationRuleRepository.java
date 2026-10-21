package io.yudhix.notify.repository;

import io.yudhix.notify.entity.NotificationRule;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface NotificationRuleRepository extends JpaRepository<NotificationRule, UUID> {

    Optional<NotificationRule> findByIdAndTenantId(UUID id, UUID tenantId);

    List<NotificationRule> findByTenantIdAndActiveTrue(UUID tenantId);

    List<NotificationRule> findByTenantIdAndRuleTypeAndActiveTrue(UUID tenantId, String ruleType);
}
