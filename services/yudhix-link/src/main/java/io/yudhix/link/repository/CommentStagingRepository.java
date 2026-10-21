package io.yudhix.link.repository;

import io.yudhix.link.entity.CommentStaging;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface CommentStagingRepository extends JpaRepository<CommentStaging, Long> {

    @Query("SELECT c FROM CommentStaging c WHERE c.processed = false ORDER BY c.id ASC")
    List<CommentStaging> findUnprocessed(Pageable pageable);
}
