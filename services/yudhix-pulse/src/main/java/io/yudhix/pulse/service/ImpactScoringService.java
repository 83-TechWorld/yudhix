package io.yudhix.pulse.service;

import io.yudhix.pulse.entity.Comment;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Duration;
import java.time.Instant;

@Service
public class ImpactScoringService {

    private static final double ALPHA_ENGAGEMENT = 0.6;
    private static final double GAMMA_VELOCITY = 0.4;
    private static final double HALF_LIFE_HOURS = 48.0;
    private static final double LAMBDA = Math.log(2.0) / HALF_LIFE_HOURS;

    public record ImpactResult(BigDecimal score, String priority, boolean needsReview) {}

    public ImpactResult calculateImpact(Comment comment, String sentiment, BigDecimal sentimentScore,
                                       boolean toxic, BigDecimal churnRisk) {
        // 1. Severity factor
        double severity = 0.3;
        String upperSentiment = sentiment != null ? sentiment.toUpperCase() : "NEUTRAL";
        switch (upperSentiment) {
            case "NEGATIVE" -> severity = 1.0;
            case "MIXED" -> severity = 0.6;
            case "NEUTRAL" -> severity = 0.3;
            case "POSITIVE" -> severity = 0.1;
        }

        if (toxic) {
            severity += 0.5;
        }
        if (churnRisk != null && churnRisk.doubleValue() > 0.6) {
            severity += 0.3;
        }

        // 2. Engagement score: log10(1 + likes + 2 * replies)
        long likes = Math.max(0, comment.getLikeCount());
        long replies = Math.max(0, comment.getReplyCount());
        double engagement = Math.log10(1.0 + likes + (2.0 * replies));

        // 3. Velocity factor: engagement per hour since created
        Instant now = Instant.now();
        Instant createdAt = comment.getPlatformCreatedAt() != null ? comment.getPlatformCreatedAt() : comment.getFirstSeenAt();
        long hoursSinceCreation = Math.max(1, Duration.between(createdAt, now).toHours());
        double velocity = (likes + (replies * 2.0)) / (double) hoursSinceCreation;
        double normalizedVelocity = Math.log10(1.0 + velocity);

        // 4. Recency decay: exp(-lambda * delta_hours)
        double recency = Math.exp(-LAMBDA * hoursSinceCreation);

        // 5. Raw Impact = severity * (alpha * engagement + gamma * velocity) * recency * 100
        double rawImpact = severity * (ALPHA_ENGAGEMENT * engagement + GAMMA_VELOCITY * normalizedVelocity) * recency * 50.0;
        
        // Scale to 0-100
        double finalScore = Math.min(100.0, Math.max(0.0, rawImpact));
        BigDecimal roundedScore = BigDecimal.valueOf(finalScore).setScale(2, RoundingMode.HALF_UP);

        // 6. Priority classification (P1, P2, P3)
        String priority;
        boolean needsReview;

        if (finalScore >= 50.0 || (toxic && churnRisk != null && churnRisk.doubleValue() > 0.5)) {
            priority = "P1";
            needsReview = true;
        } else if (finalScore >= 20.0 || "NEGATIVE".equals(upperSentiment)) {
            priority = "P2";
            needsReview = true;
        } else {
            priority = "P3";
            needsReview = false;
        }

        return new ImpactResult(roundedScore, priority, needsReview);
    }
}
