package io.yudhix.resolve.repository;

import io.yudhix.resolve.entity.ApprovalStep;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface ApprovalStepRepository extends JpaRepository<ApprovalStep, Long> {

    List<ApprovalStep> findByTenantIdAndReplyIdOrderByActionAtAsc(UUID tenantId, UUID replyId);
}
