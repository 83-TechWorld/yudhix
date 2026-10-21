package io.yudhix.pulse.repository;

import io.yudhix.pulse.entity.CommentAnalysis;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface CommentAnalysisRepository extends JpaRepository<CommentAnalysis, CommentAnalysis.CommentAnalysisId> {

    Optional<CommentAnalysis> findByTenantIdAndCommentId(UUID tenantId, UUID commentId);

    Page<CommentAnalysis> findByTenantIdAndPriority(UUID tenantId, String priority, Pageable pageable);

    Page<CommentAnalysis> findByTenantIdAndNeedsReviewTrue(UUID tenantId, Pageable pageable);

    @Query("SELECT ca FROM CommentAnalysis ca WHERE ca.tenantId = :tenantId AND (:priority IS NULL OR ca.priority = :priority) AND (:needsReview IS NULL OR ca.needsReview = :needsReview)")
    Page<CommentAnalysis> findInboxItems(@Param("tenantId") UUID tenantId,
                                        @Param("priority") String priority,
                                        @Param("needsReview") Boolean needsReview,
                                        Pageable pageable);
}
