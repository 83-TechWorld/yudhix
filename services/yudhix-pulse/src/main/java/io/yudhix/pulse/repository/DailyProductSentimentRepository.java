package io.yudhix.pulse.repository;

import io.yudhix.pulse.entity.DailyProductSentiment;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

@Repository
public interface DailyProductSentimentRepository extends JpaRepository<DailyProductSentiment, DailyProductSentiment.DailyProductSentimentId> {

    List<DailyProductSentiment> findByTenantIdAndProductIdAndDayBetweenOrderByDayAsc(
            UUID tenantId, UUID productId, LocalDate from, LocalDate to);

    List<DailyProductSentiment> findByTenantIdAndDay(UUID tenantId, LocalDate day);
}
