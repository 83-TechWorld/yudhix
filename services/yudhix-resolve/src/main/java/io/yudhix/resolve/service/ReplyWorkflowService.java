package io.yudhix.resolve.service;

import io.yudhix.common.context.TenantContextHolder;
import io.yudhix.common.exception.ApiException;
import io.yudhix.common.exception.ResourceNotFoundException;
import io.yudhix.resolve.dto.ApprovalDecisionRequest;
import io.yudhix.resolve.dto.CreateReplyRequest;
import io.yudhix.resolve.dto.ReplyResponse;
import io.yudhix.resolve.entity.ApprovalStep;
import io.yudhix.resolve.entity.Reply;
import io.yudhix.resolve.repository.ApprovalStepRepository;
import io.yudhix.resolve.repository.ReplyRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class ReplyWorkflowService {

    private final ReplyRepository replyRepository;
    private final ApprovalStepRepository approvalStepRepository;

    @Transactional
    public Reply createDraft(CreateReplyRequest req) {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();
        long slaMinutes = req.getSlaMinutes() != null && req.getSlaMinutes() > 0 ? req.getSlaMinutes() : 120L;

        Reply reply = Reply.builder()
                .id(UUID.randomUUID())
                .tenantId(tenantId)
                .commentId(req.getCommentId())
                .platform(req.getPlatform())
                .replyText(req.getReplyText())
                .status("DRAFT")
                .authorId(req.getAuthorId())
                .slaDueAt(Instant.now().plus(Duration.ofMinutes(slaMinutes)))
                .build();

        return replyRepository.save(reply);
    }

    @Transactional
    public Reply submitForReview(UUID replyId) {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();
        Reply reply = getReplyOrThrow(replyId, tenantId);

        if (!"DRAFT".equalsIgnoreCase(reply.getStatus()) && !"CHANGES_REQUESTED".equalsIgnoreCase(reply.getStatus())) {
            throw new ApiException("Reply cannot be submitted for review from status: " + reply.getStatus(),
                    HttpStatus.BAD_REQUEST, "INVALID_STATE_TRANSITION");
        }

        reply.setStatus("IN_REVIEW");
        reply.setUpdatedAt(Instant.now());
        return replyRepository.save(reply);
    }

    @Transactional
    public Reply processApprovalDecision(UUID replyId, ApprovalDecisionRequest req) {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();
        Reply reply = getReplyOrThrow(replyId, tenantId);

        if (!"IN_REVIEW".equalsIgnoreCase(reply.getStatus())) {
            throw new ApiException("Reply must be in IN_REVIEW state to evaluate decision",
                    HttpStatus.BAD_REQUEST, "INVALID_STATE_TRANSITION");
        }

        // Enforce Separation of Duties: Author cannot approve their own reply
        if (reply.getAuthorId().equals(req.getReviewerId())) {
            throw new ApiException("Separation of duties violation: Author cannot approve their own reply draft",
                    HttpStatus.FORBIDDEN, "SEPARATION_OF_DUTIES_VIOLATION");
        }

        String decision = req.getDecision().toUpperCase();
        if ("APPROVED".equals(decision)) {
            reply.setStatus("APPROVED");
            reply.setApproverId(req.getReviewerId());
        } else if ("REJECTED".equals(decision)) {
            reply.setStatus("REJECTED");
            reply.setRejectionReason(req.getComments());
        } else if ("CHANGES_REQUESTED".equals(decision)) {
            reply.setStatus("CHANGES_REQUESTED");
            reply.setRejectionReason(req.getComments());
        } else {
            throw new ApiException("Unknown decision: " + req.getDecision(), HttpStatus.BAD_REQUEST, "INVALID_DECISION");
        }

        reply.setUpdatedAt(Instant.now());
        Reply savedReply = replyRepository.save(reply);

        // Record approval audit step
        ApprovalStep step = ApprovalStep.builder()
                .tenantId(tenantId)
                .replyId(replyId)
                .stepName(req.getStepName() != null ? req.getStepName() : "MANAGEMENT_REVIEW")
                .reviewerId(req.getReviewerId())
                .decision(decision)
                .comments(req.getComments())
                .actionAt(Instant.now())
                .build();
        approvalStepRepository.save(step);

        return savedReply;
    }

    @Transactional
    public Reply markPosted(UUID replyId, String platformReplyId) {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();
        Reply reply = getReplyOrThrow(replyId, tenantId);

        if (!"APPROVED".equalsIgnoreCase(reply.getStatus())) {
            throw new ApiException("Only APPROVED replies can be marked as POSTED",
                    HttpStatus.BAD_REQUEST, "INVALID_STATE_TRANSITION");
        }

        reply.setStatus("POSTED");
        reply.setPlatformReplyId(platformReplyId);
        reply.setPostedAt(Instant.now());
        reply.setUpdatedAt(Instant.now());
        return replyRepository.save(reply);
    }

    @Transactional(readOnly = true)
    public ReplyResponse getReplyDetails(UUID replyId) {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();
        Reply reply = getReplyOrThrow(replyId, tenantId);
        List<ApprovalStep> history = approvalStepRepository.findByTenantIdAndReplyIdOrderByActionAtAsc(tenantId, replyId);
        return ReplyResponse.builder().reply(reply).history(history).build();
    }

    @Transactional(readOnly = true)
    public Page<Reply> listReplies(String status, Pageable pageable) {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();
        return replyRepository.findByTenantIdAndStatus(tenantId, status, pageable);
    }

    @Transactional(readOnly = true)
    public List<Reply> getBreachingReplies(int minutesAhead) {
        UUID tenantId = TenantContextHolder.getRequiredTenantId();
        Instant threshold = Instant.now().plus(Duration.ofMinutes(minutesAhead));
        return replyRepository.findBreachingReplies(tenantId, threshold);
    }

    private Reply getReplyOrThrow(UUID replyId, UUID tenantId) {
        return replyRepository.findByIdAndTenantId(replyId, tenantId)
                .orElseThrow(() -> new ResourceNotFoundException("Reply not found: " + replyId));
    }
}
