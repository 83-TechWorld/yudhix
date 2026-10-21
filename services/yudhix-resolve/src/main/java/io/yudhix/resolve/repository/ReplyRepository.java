package io.yudhix.resolve.repository;

import io.yudhix.resolve.entity.Reply;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface ReplyRepository extends JpaRepository<Reply, UUID> {

    Optional<Reply> findByIdAndTenantId(UUID id, UUID tenantId);

    List<Reply> findByTenantIdAndCommentId(UUID tenantId, UUID commentId);

    Page<Reply> findByTenantIdAndStatus(UUID tenantId, String status, Pageable pageable);

    @Query("SELECT r FROM Reply r WHERE r.tenantId = :tenantId AND r.status IN ('DRAFT', 'IN_REVIEW') AND r.slaDueAt <= :threshold")
    List<Reply> findBreachingReplies(@Param("tenantId") UUID tenantId, @Param("threshold") Instant threshold);
}
