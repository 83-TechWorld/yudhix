package io.yudhix.pulse.repository;

import io.yudhix.pulse.entity.CommentAspect;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface CommentAspectRepository extends JpaRepository<CommentAspect, Long> {

    List<CommentAspect> findByTenantIdAndCommentId(UUID tenantId, UUID commentId);

    void deleteByTenantIdAndCommentId(UUID tenantId, UUID commentId);
}
