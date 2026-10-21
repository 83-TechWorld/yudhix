package io.yudhix.loop.service;

import io.yudhix.common.context.TenantContextHolder;
import io.yudhix.loop.dto.RecordCheckpointRequest;
import io.yudhix.loop.dto.RecordFeedbackRequest;
import io.yudhix.loop.dto.TurnaroundMetricsResponse;
import io.yudhix.loop.entity.LabelFeedback;
import io.yudhix.loop.entity.ReplyOutcome;
import io.yudhix.loop.repository.LabelFeedbackRepository;
import io.yudhix.loop.repository.ReplyOutcomeRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class TurnaroundService {

    private final ReplyOutcomeRepository replyOutcomeRepository;
    private final LabelFeedbackRepository labelFeedbackRepository;

    @Transactional
    public ReplyOutcome recordCheckpoint(RecordCheckpointRequest req) {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();

        ReplyOutcome outcome = replyOutcomeRepository.findByTenantIdAndReplyId(tenantId, req.getReplyId())
                .orElse(ReplyOutcome.builder()
                        .id(UUID.randomUUID())
                        .tenantId(tenantId)
                        .replyId(req.getReplyId())
                        .commentId(req.getCommentId())
                        .initialSentiment(req.getInitialSentiment().toUpperCase())
                        .build());

        String interval = req.getInterval() != null ? req.getInterval().toUpperCase() : "24H";
        String followUpSentiment = req.getFollowUpSentiment() != null ? req.getFollowUpSentiment().toUpperCase() : null;

        switch (interval) {
            case "24H" -> outcome.setCheckpoint24hSentiment(followUpSentiment);
            case "72H" -> outcome.setCheckpoint72hSentiment(followUpSentiment);
            case "7D" -> outcome.setCheckpoint7dSentiment(followUpSentiment);
        }

        if (req.getFollowUpCommentId() != null) {
            outcome.setFollowUpCommentId(req.getFollowUpCommentId());
        }
        if (req.getNotes() != null) {
            outcome.setNotes(req.getNotes());
        }

        // Check if turned around: was negative, now positive or neutral in ANY checkpoint
        boolean isTurned = isPositiveOrNeutral(outcome.getCheckpoint24hSentiment()) ||
                          isPositiveOrNeutral(outcome.getCheckpoint72hSentiment()) ||
                          isPositiveOrNeutral(outcome.getCheckpoint7dSentiment());

        outcome.setTurnedAround(isTurned && "NEGATIVE".equalsIgnoreCase(outcome.getInitialSentiment()));
        outcome.setUpdatedAt(Instant.now());

        return replyOutcomeRepository.save(outcome);
    }

    private boolean isPositiveOrNeutral(String sentiment) {
        return "POSITIVE".equalsIgnoreCase(sentiment) || "NEUTRAL".equalsIgnoreCase(sentiment);
    }

    @Transactional(readOnly = true)
    public TurnaroundMetricsResponse getTurnaroundMetrics() {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();
        long totalNeg = replyOutcomeRepository.countNegativeReplied(tenantId);
        long totalTurned = replyOutcomeRepository.countTurnedAround(tenantId);

        BigDecimal rate = BigDecimal.ZERO;
        if (totalNeg > 0) {
            rate = BigDecimal.valueOf((double) totalTurned / totalNeg * 100.0)
                    .setScale(2, RoundingMode.HALF_UP);
        }

        return TurnaroundMetricsResponse.builder()
                .totalNegativeReplied(totalNeg)
                .totalTurnedAround(totalTurned)
                .turnaroundRatePercent(rate)
                .build();
    }

    @Transactional
    public LabelFeedback recordLabelFeedback(RecordFeedbackRequest req) {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();

        LabelFeedback feedback = LabelFeedback.builder()
                .tenantId(tenantId)
                .commentId(req.getCommentId())
                .reviewerId(req.getReviewerId())
                .originalSentiment(req.getOriginalSentiment().toUpperCase())
                .correctedSentiment(req.getCorrectedSentiment().toUpperCase())
                .originalToxic(req.isOriginalToxic())
                .correctedToxic(req.isCorrectedToxic())
                .reason(req.getReason())
                .createdAt(Instant.now())
                .build();

        return labelFeedbackRepository.save(feedback);
    }

    @Transactional(readOnly = true)
    public Page<LabelFeedback> listFeedback(Pageable pageable) {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();
        return labelFeedbackRepository.findByTenantId(tenantId, pageable);
    }
}
