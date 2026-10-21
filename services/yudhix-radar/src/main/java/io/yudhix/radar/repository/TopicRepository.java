package io.yudhix.radar.repository;

import io.yudhix.radar.entity.Topic;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface TopicRepository extends JpaRepository<Topic, UUID> {
    List<Topic> findByTenantId(UUID tenantId);
    Optional<Topic> findByTenantIdAndName(UUID tenantId, String name);
    boolean existsByTenantIdAndName(UUID tenantId, String name);
}
