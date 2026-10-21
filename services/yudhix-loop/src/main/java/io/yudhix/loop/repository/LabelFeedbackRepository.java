package io.yudhix.loop.repository;

import io.yudhix.loop.entity.LabelFeedback;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.UUID;

@Repository
public interface LabelFeedbackRepository extends JpaRepository<LabelFeedback, Long> {

    Page<LabelFeedback> findByTenantId(UUID tenantId, Pageable pageable);
}
