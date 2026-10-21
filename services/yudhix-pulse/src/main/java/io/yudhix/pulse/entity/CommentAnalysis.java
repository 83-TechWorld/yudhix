package io.yudhix.pulse.entity;

import jakarta.persistence.*;
import lombok.*;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "comment_analysis")
@IdClass(CommentAnalysis.CommentAnalysisId.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CommentAnalysis {

    @Id
    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Id
    @Column(name = "comment_id", nullable = false)
    private UUID commentId;

    @Column(name = "analyzed_at", nullable = false)
    @Builder.Default
    private Instant analyzedAt = Instant.now();

    @Column(name = "model_version", nullable = false, length = 100)
    private String modelVersion;

    @Column(nullable = false, length = 20)
    private String sentiment; // POSITIVE, NEGATIVE, NEUTRAL, MIXED

    @Column(name = "sentiment_score", nullable = false, precision = 4, scale = 3)
    private BigDecimal sentimentScore;

    @Column(length = 50)
    private String intent;

    @Column(name = "topic_id")
    private UUID topicId;

    @Column(nullable = false)
    @Builder.Default
    private boolean toxic = false;

    @Column(name = "churn_risk", precision = 3, scale = 2)
    private BigDecimal churnRisk;

    @Column(name = "impact_score", nullable = false, precision = 5, scale = 2)
    private BigDecimal impactScore;

    @Column(nullable = false, length = 10)
    private String priority; // P1, P2, P3

    @Column(name = "needs_review", nullable = false)
    @Builder.Default
    private boolean needsReview = false;

    @Column(name = "suggested_reply", columnDefinition = "text")
    private String suggestedReply;

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CommentAnalysisId implements Serializable {
        private UUID tenantId;
        private UUID commentId;
    }
}
