package io.yudhix.loop.repository;

import io.yudhix.loop.entity.ReplyOutcome;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface ReplyOutcomeRepository extends JpaRepository<ReplyOutcome, UUID> {

    Optional<ReplyOutcome> findByTenantIdAndReplyId(UUID tenantId, UUID replyId);

    @Query("SELECT COUNT(ro) FROM ReplyOutcome ro WHERE ro.tenantId = :tenantId AND ro.initialSentiment = 'NEGATIVE'")
    long countNegativeReplied(@Param("tenantId") UUID tenantId);

    @Query("SELECT COUNT(ro) FROM ReplyOutcome ro WHERE ro.tenantId = :tenantId AND ro.initialSentiment = 'NEGATIVE' AND ro.turnedAround = true")
    long countTurnedAround(@Param("tenantId") UUID tenantId);
}
