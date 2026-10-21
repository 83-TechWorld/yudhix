package io.yudhix.loop.service;

import io.yudhix.common.context.TenantContext;
import io.yudhix.common.context.TenantContextHolder;
import io.yudhix.loop.dto.RecordCheckpointRequest;
import io.yudhix.loop.dto.TurnaroundMetricsResponse;
import io.yudhix.loop.entity.ReplyOutcome;
import io.yudhix.loop.repository.LabelFeedbackRepository;
import io.yudhix.loop.repository.ReplyOutcomeRepository;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class TurnaroundServiceTest {

    @Mock
    private ReplyOutcomeRepository replyOutcomeRepository;

    @Mock
    private LabelFeedbackRepository labelFeedbackRepository;

    @InjectMocks
    private TurnaroundService turnaroundService;

    private final UUID tenantId = UUID.randomUUID();

    @BeforeEach
    void setUp() {
        TenantContextHolder.setContext(TenantContext.builder()
                .tenantId(tenantId)
                .userId(UUID.randomUUID())
                .countryCode("US")
                .build());
    }

    @AfterEach
    void tearDown() {
        TenantContextHolder.clear();
    }

    @Test
    void testNegativeTurnedToPositiveAt24h() {
        UUID replyId = UUID.randomUUID();
        UUID commentId = UUID.randomUUID();

        RecordCheckpointRequest req = RecordCheckpointRequest.builder()
                .replyId(replyId)
                .commentId(commentId)
                .initialSentiment("NEGATIVE")
                .interval("24H")
                .followUpSentiment("POSITIVE")
                .followUpCommentId("c_999")
                .notes("User replied: 'Thanks for the quick refund! Great support!'")
                .build();

        when(replyOutcomeRepository.findByTenantIdAndReplyId(tenantId, replyId)).thenReturn(Optional.empty());
        when(replyOutcomeRepository.save(any(ReplyOutcome.class))).thenAnswer(i -> i.getArgument(0));

        ReplyOutcome outcome = turnaroundService.recordCheckpoint(req);

        assertNotNull(outcome);
        assertTrue(outcome.isTurnedAround(), "Should be marked as turned around when shifting from NEGATIVE to POSITIVE");
        assertEquals("POSITIVE", outcome.getCheckpoint24hSentiment());
    }

    @Test
    void testTurnaroundMetricsCalculation() {
        when(replyOutcomeRepository.countNegativeReplied(tenantId)).thenReturn(100L);
        when(replyOutcomeRepository.countTurnedAround(tenantId)).thenReturn(65L);

        TurnaroundMetricsResponse metrics = turnaroundService.getTurnaroundMetrics();

        assertEquals(100L, metrics.getTotalNegativeReplied());
        assertEquals(65L, metrics.getTotalTurnedAround());
        assertEquals(new BigDecimal("65.00"), metrics.getTurnaroundRatePercent());
    }
}
