package io.yudhix.pulse.service;

import io.yudhix.common.context.TenantContextHolder;
import io.yudhix.common.exception.ResourceNotFoundException;
import io.yudhix.pulse.dto.AnalysisResultRequest;
import io.yudhix.pulse.dto.CommentResponse;
import io.yudhix.pulse.dto.IngestCommentRequest;
import io.yudhix.pulse.entity.Comment;
import io.yudhix.pulse.entity.CommentAnalysis;
import io.yudhix.pulse.entity.CommentAspect;
import io.yudhix.pulse.entity.DailyProductSentiment;
import io.yudhix.pulse.repository.CommentAnalysisRepository;
import io.yudhix.pulse.repository.CommentAspectRepository;
import io.yudhix.pulse.repository.CommentRepository;
import io.yudhix.pulse.repository.DailyProductSentimentRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class CommentService {

    private final CommentRepository commentRepository;
    private final CommentAnalysisRepository commentAnalysisRepository;
    private final CommentAspectRepository commentAspectRepository;
    private final DailyProductSentimentRepository dailySentimentRepository;
    private final ImpactScoringService impactScoringService;

    @Transactional
    public Comment ingestComment(IngestCommentRequest req) {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();

        Optional<Comment> existingOpt = commentRepository.findByTenantIdAndPlatformAndPlatformCommentId(
                tenantId, req.getPlatform(), req.getPlatformCommentId());

        if (existingOpt.isPresent()) {
            Comment existing = existingOpt.get();
            existing.setLikeCount(req.getLikeCount());
            existing.setReplyCount(req.getReplyCount());
            existing.setDislikeCount(req.getDislikeCount());
            existing.setLastSeenAt(Instant.now());
            // If masked text changed
            if (req.getMaskedText() != null && !req.getContentHash().equals(existing.getContentHash())) {
                existing.setMaskedText(req.getMaskedText());
                existing.setContentHash(req.getContentHash());
                existing.setStatus("EDITED");
            }
            return commentRepository.save(existing);
        }

        Comment newComment = Comment.builder()
                .id(UUID.randomUUID())
                .tenantId(tenantId)
                .platform(req.getPlatform())
                .platformCommentId(req.getPlatformCommentId())
                .parentCommentId(req.getParentCommentId())
                .sourceId(req.getSourceId())
                .productId(req.getProductId())
                .authorHash(req.getAuthorHash())
                .authorKeyVersion(req.getAuthorKeyVersion() > 0 ? req.getAuthorKeyVersion() : 1)
                .maskedText(req.getMaskedText())
                .textExpiresAt(req.getTextExpiresAt() != null ? req.getTextExpiresAt() : Instant.now().plusSeconds(30L * 24 * 3600))
                .language(req.getLanguage())
                .countryHint(req.getCountryHint())
                .likeCount(req.getLikeCount())
                .replyCount(req.getReplyCount())
                .dislikeCount(req.getDislikeCount())
                .platformCreatedAt(req.getPlatformCreatedAt())
                .firstSeenAt(Instant.now())
                .lastSeenAt(Instant.now())
                .contentHash(req.getContentHash())
                .status("ACTIVE")
                .customAttributes(req.getCustomAttributes() != null ? req.getCustomAttributes() : "{}")
                .build();

        return commentRepository.save(newComment);
    }

    @Transactional
    public CommentAnalysis saveAnalysis(UUID commentId, AnalysisResultRequest req) {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();
        Comment comment = commentRepository.findById(new Comment.CommentId(tenantId, commentId))
                .orElseThrow(() -> new ResourceNotFoundException("Comment not found: " + commentId));

        ImpactScoringService.ImpactResult impact = impactScoringService.calculateImpact(
                comment, req.getSentiment(), req.getSentimentScore(), req.isToxic(), req.getChurnRisk());

        CommentAnalysis analysis = CommentAnalysis.builder()
                .tenantId(tenantId)
                .commentId(commentId)
                .analyzedAt(Instant.now())
                .modelVersion(req.getModelVersion())
                .sentiment(req.getSentiment().toUpperCase())
                .sentimentScore(req.getSentimentScore())
                .intent(req.getIntent())
                .topicId(req.getTopicId())
                .toxic(req.isToxic())
                .churnRisk(req.getChurnRisk())
                .impactScore(impact.score())
                .priority(impact.priority())
                .needsReview(impact.needsReview())
                .suggestedReply(req.getSuggestedReply())
                .build();

        CommentAnalysis savedAnalysis = commentAnalysisRepository.save(analysis);

        // Aspect breakdown
        if (req.getAspects() != null && !req.getAspects().isEmpty()) {
            commentAspectRepository.deleteByTenantIdAndCommentId(tenantId, commentId);
            for (AnalysisResultRequest.AspectItem item : req.getAspects()) {
                CommentAspect aspect = CommentAspect.builder()
                        .tenantId(tenantId)
                        .commentId(commentId)
                        .aspect(item.getAspect())
                        .sentiment(item.getSentiment().toUpperCase())
                        .score(item.getScore())
                        .evidence(item.getEvidence())
                        .build();
                commentAspectRepository.save(aspect);
            }
        }

        // Daily aggregate update
        if (comment.getProductId() != null) {
            updateDailyAggregate(tenantId, comment, savedAnalysis);
        }

        return savedAnalysis;
    }

    private void updateDailyAggregate(UUID tenantId, Comment comment, CommentAnalysis analysis) {
        LocalDate day = comment.getPlatformCreatedAt().atZone(ZoneOffset.UTC).toLocalDate();
        String country = comment.getCountryHint() != null ? comment.getCountryHint() : "GLOBAL";
        DailyProductSentiment.DailyProductSentimentId key = new DailyProductSentiment.DailyProductSentimentId(
                tenantId, day, comment.getProductId(), comment.getPlatform(), country);

        DailyProductSentiment agg = dailySentimentRepository.findById(key)
                .orElse(DailyProductSentiment.builder()
                        .tenantId(tenantId)
                        .day(day)
                        .productId(comment.getProductId())
                        .platform(comment.getPlatform())
                        .countryCode(country)
                        .build());

        switch (analysis.getSentiment().toUpperCase()) {
            case "POSITIVE" -> agg.setPositiveCount(agg.getPositiveCount() + 1);
            case "NEGATIVE" -> agg.setNegativeCount(agg.getNegativeCount() + 1);
            case "NEUTRAL" -> agg.setNeutralCount(agg.getNeutralCount() + 1);
            case "MIXED" -> agg.setMixedCount(agg.getMixedCount() + 1);
        }

        agg.setTotalLikes(agg.getTotalLikes() + comment.getLikeCount());
        agg.setTotalReplies(agg.getTotalReplies() + comment.getReplyCount());
        dailySentimentRepository.save(agg);
    }

    @Transactional(readOnly = true)
    public CommentResponse getCommentDetails(UUID commentId) {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();
        Comment comment = commentRepository.findById(new Comment.CommentId(tenantId, commentId))
                .orElseThrow(() -> new ResourceNotFoundException("Comment not found: " + commentId));

        CommentAnalysis analysis = commentAnalysisRepository.findByTenantIdAndCommentId(tenantId, commentId).orElse(null);
        List<CommentAspect> aspects = commentAspectRepository.findByTenantIdAndCommentId(tenantId, commentId);

        return CommentResponse.builder()
                .id(comment.getId())
                .tenantId(comment.getTenantId())
                .platform(comment.getPlatform())
                .platformCommentId(comment.getPlatformCommentId())
                .parentCommentId(comment.getParentCommentId())
                .sourceId(comment.getSourceId())
                .productId(comment.getProductId())
                .authorHash(comment.getAuthorHash())
                .maskedText(comment.getMaskedText())
                .textExpiresAt(comment.getTextExpiresAt())
                .language(comment.getLanguage())
                .countryHint(comment.getCountryHint())
                .likeCount(comment.getLikeCount())
                .replyCount(comment.getReplyCount())
                .platformCreatedAt(comment.getPlatformCreatedAt())
                .firstSeenAt(comment.getFirstSeenAt())
                .lastSeenAt(comment.getLastSeenAt())
                .status(comment.getStatus())
                .analysis(analysis)
                .aspects(aspects)
                .build();
    }

    @Transactional(readOnly = true)
    public Page<CommentAnalysis> getInboxItems(String priority, Boolean needsReview, Pageable pageable) {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();
        return commentAnalysisRepository.findInboxItems(tenantId, priority, needsReview, pageable);
    }

    @Transactional
    public int enforceTextRetention() {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();
        Page<Comment> expired = commentRepository.findExpiredComments(tenantId, Instant.now(), Pageable.ofSize(500));
        int erased = 0;
        for (Comment c : expired) {
            c.setMaskedText("[REDACTED_BY_RETENTION_POLICY]");
            commentRepository.save(c);
            erased++;
        }
        return erased;
    }
}
