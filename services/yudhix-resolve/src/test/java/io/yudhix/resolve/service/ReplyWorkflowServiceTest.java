package io.yudhix.resolve.service;

import io.yudhix.common.context.TenantContext;
import io.yudhix.common.context.TenantContextHolder;
import io.yudhix.common.exception.ApiException;
import io.yudhix.resolve.dto.ApprovalDecisionRequest;
import io.yudhix.resolve.dto.CreateReplyRequest;
import io.yudhix.resolve.entity.Reply;
import io.yudhix.resolve.repository.ApprovalStepRepository;
import io.yudhix.resolve.repository.ReplyRepository;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class ReplyWorkflowServiceTest {

    @Mock
    private ReplyRepository replyRepository;

    @Mock
    private ApprovalStepRepository approvalStepRepository;

    @InjectMocks
    private ReplyWorkflowService workflowService;

    private final UUID tenantId = UUID.randomUUID();
    private final UUID authorId = UUID.randomUUID();
    private final UUID reviewerId = UUID.randomUUID();

    @BeforeEach
    void setUp() {
        TenantContextHolder.setContext(TenantContext.builder()
                .tenantId(tenantId)
                .userId(UUID.randomUUID())
                .countryCode("IN")
                .build());
    }

    @AfterEach
    void tearDown() {
        TenantContextHolder.clear();
    }

    @Test
    void testCreateDraftAndSubmitForReview() {
        UUID commentId = UUID.randomUUID();
        CreateReplyRequest req = CreateReplyRequest.builder()
                .commentId(commentId)
                .platform("LINKEDIN")
                .replyText("Thank you for your valuable feedback.")
                .authorId(authorId)
                .slaMinutes(120L)
                .build();

        Reply draft = Reply.builder()
                .id(UUID.randomUUID())
                .tenantId(tenantId)
                .commentId(commentId)
                .platform("LINKEDIN")
                .replyText(req.getReplyText())
                .status("DRAFT")
                .authorId(authorId)
                .slaDueAt(Instant.now().plusSeconds(7200))
                .build();

        when(replyRepository.save(any(Reply.class))).thenReturn(draft);

        Reply created = workflowService.createDraft(req);
        assertEquals("DRAFT", created.getStatus());

        when(replyRepository.findByIdAndTenantId(draft.getId(), tenantId)).thenReturn(Optional.of(draft));
        Reply submitted = workflowService.submitForReview(draft.getId());
        assertEquals("IN_REVIEW", submitted.getStatus());
    }

    @Test
    void testSeparationOfDutiesPreventsAuthorFromApproving() {
        UUID replyId = UUID.randomUUID();
        Reply inReviewReply = Reply.builder()
                .id(replyId)
                .tenantId(tenantId)
                .authorId(authorId)
                .status("IN_REVIEW")
                .build();

        when(replyRepository.findByIdAndTenantId(replyId, tenantId)).thenReturn(Optional.of(inReviewReply));

        // Author attempting to approve their own reply
        ApprovalDecisionRequest decision = ApprovalDecisionRequest.builder()
                .reviewerId(authorId) // SAME AS AUTHOR
                .decision("APPROVED")
                .build();

        ApiException exception = assertThrows(ApiException.class, () ->
                workflowService.processApprovalDecision(replyId, decision)
        );

        assertEquals("SEPARATION_OF_DUTIES_VIOLATION", exception.getErrorCode());
        verify(approvalStepRepository, never()).save(any());
    }

    @Test
    void testIndependentReviewerApprovalSucceeds() {
        UUID replyId = UUID.randomUUID();
        Reply inReviewReply = Reply.builder()
                .id(replyId)
                .tenantId(tenantId)
                .authorId(authorId)
                .status("IN_REVIEW")
                .build();

        when(replyRepository.findByIdAndTenantId(replyId, tenantId)).thenReturn(Optional.of(inReviewReply));
        when(replyRepository.save(any(Reply.class))).thenAnswer(i -> i.getArgument(0));

        ApprovalDecisionRequest decision = ApprovalDecisionRequest.builder()
                .reviewerId(reviewerId) // DIFFERENT FROM AUTHOR
                .decision("APPROVED")
                .comments("Approved for publishing")
                .build();

        Reply approved = workflowService.processApprovalDecision(replyId, decision);

        assertEquals("APPROVED", approved.getStatus());
        assertEquals(reviewerId, approved.getApproverId());
        verify(approvalStepRepository, times(1)).save(any());
    }
}
