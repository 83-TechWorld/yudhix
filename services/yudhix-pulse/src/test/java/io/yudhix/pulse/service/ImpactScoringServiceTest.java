package io.yudhix.pulse.service;

import io.yudhix.pulse.entity.Comment;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class ImpactScoringServiceTest {

    private ImpactScoringService scoringService;

    @BeforeEach
    void setUp() {
        scoringService = new ImpactScoringService();
    }

    @Test
    void testHighImpactCrisisComment() {
        Comment comment = Comment.builder()
                .id(UUID.randomUUID())
                .tenantId(UUID.randomUUID())
                .platform("YOUTUBE")
                .platformCommentId("yt_123")
                .sourceId(UUID.randomUUID())
                .authorHash("hash123")
                .likeCount(5000)
                .replyCount(1200)
                .platformCreatedAt(Instant.now().minusSeconds(3600)) // 1 hour ago
                .contentHash("hash")
                .build();

        ImpactScoringService.ImpactResult result = scoringService.calculateImpact(
                comment, "NEGATIVE", new BigDecimal("0.95"), true, new BigDecimal("0.85"));

        assertNotNull(result);
        assertTrue(result.score().doubleValue() > 50.0);
        assertEquals("P1", result.priority());
        assertTrue(result.needsReview());
    }

    @Test
    void testLowImpactPositiveComment() {
        Comment comment = Comment.builder()
                .id(UUID.randomUUID())
                .tenantId(UUID.randomUUID())
                .platform("LINKEDIN")
                .platformCommentId("li_456")
                .sourceId(UUID.randomUUID())
                .authorHash("hash456")
                .likeCount(2)
                .replyCount(0)
                .platformCreatedAt(Instant.now().minusSeconds(86400 * 5)) // 5 days ago
                .contentHash("hash")
                .build();

        ImpactScoringService.ImpactResult result = scoringService.calculateImpact(
                comment, "POSITIVE", new BigDecimal("0.80"), false, BigDecimal.ZERO);

        assertNotNull(result);
        assertEquals("P3", result.priority());
        assertFalse(result.needsReview());
    }
}
