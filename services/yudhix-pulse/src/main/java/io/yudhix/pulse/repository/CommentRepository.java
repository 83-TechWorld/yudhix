package io.yudhix.pulse.repository;

import io.yudhix.pulse.entity.Comment;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface CommentRepository extends JpaRepository<Comment, Comment.CommentId> {

    Optional<Comment> findByTenantIdAndPlatformAndPlatformCommentId(UUID tenantId, String platform, String platformCommentId);

    Page<Comment> findByTenantId(UUID tenantId, Pageable pageable);

    Page<Comment> findByTenantIdAndProductId(UUID tenantId, UUID productId, Pageable pageable);

    @Query("SELECT c FROM Comment c WHERE c.tenantId = :tenantId AND c.textExpiresAt <= :now AND c.maskedText IS NOT NULL")
    Page<Comment> findExpiredComments(@Param("tenantId") UUID tenantId, @Param("now") Instant now, Pageable pageable);
}
