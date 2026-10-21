package io.yudhix.resolve.repository;

import io.yudhix.resolve.entity.ReplyTemplate;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface ReplyTemplateRepository extends JpaRepository<ReplyTemplate, UUID> {

    Optional<ReplyTemplate> findByIdAndTenantId(UUID id, UUID tenantId);

    List<ReplyTemplate> findByTenantIdAndActiveTrue(UUID tenantId);

    List<ReplyTemplate> findByTenantIdAndCategoryAndActiveTrue(UUID tenantId, String category);
}
