package io.yudhix.pulse.entity;

import jakarta.persistence.*;
import lombok.*;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.UUID;

@Entity
@Table(name = "daily_product_sentiment")
@IdClass(DailyProductSentiment.DailyProductSentimentId.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DailyProductSentiment {

    @Id
    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Id
    @Column(nullable = false)
    private LocalDate day;

    @Id
    @Column(name = "product_id", nullable = false)
    private UUID productId;

    @Id
    @Column(nullable = false, length = 50)
    private String platform;

    @Id
    @Column(name = "country_code", nullable = false, length = 10)
    @Builder.Default
    private String countryCode = "GLOBAL";

    @Column(name = "positive_cnt", nullable = false)
    @Builder.Default
    private int positiveCount = 0;

    @Column(name = "negative_cnt", nullable = false)
    @Builder.Default
    private int negativeCount = 0;

    @Column(name = "neutral_cnt", nullable = false)
    @Builder.Default
    private int neutralCount = 0;

    @Column(name = "mixed_cnt", nullable = false)
    @Builder.Default
    private int mixedCount = 0;

    @Column(name = "total_likes", nullable = false)
    @Builder.Default
    private long totalLikes = 0L;

    @Column(name = "total_replies", nullable = false)
    @Builder.Default
    private long totalReplies = 0L;

    @Column(name = "avg_impact", precision = 5, scale = 2)
    @Builder.Default
    private BigDecimal avgImpact = BigDecimal.ZERO;

    @Column(name = "replied_cnt", nullable = false)
    @Builder.Default
    private int repliedCount = 0;

    @Column(name = "improved_cnt", nullable = false)
    @Builder.Default
    private int improvedCount = 0;

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DailyProductSentimentId implements Serializable {
        private UUID tenantId;
        private LocalDate day;
        private UUID productId;
        private String platform;
        private String countryCode;
    }
}
