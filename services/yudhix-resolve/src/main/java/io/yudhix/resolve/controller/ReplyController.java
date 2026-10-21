package io.yudhix.resolve.controller;

import io.yudhix.common.dto.ApiResponse;
import io.yudhix.common.dto.PageResponse;
import io.yudhix.resolve.dto.ApprovalDecisionRequest;
import io.yudhix.resolve.dto.CreateReplyRequest;
import io.yudhix.resolve.dto.ReplyResponse;
import io.yudhix.resolve.entity.Reply;
import io.yudhix.resolve.service.ReplyWorkflowService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/replies")
@RequiredArgsConstructor
public class ReplyController {

    private final ReplyWorkflowService workflowService;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<Reply> createDraft(@Valid @RequestBody CreateReplyRequest request) {
        Reply reply = workflowService.createDraft(request);
        return ApiResponse.success("Reply draft created successfully", reply);
    }

    @PostMapping("/{id}/submit")
    public ApiResponse<Reply> submitForReview(@PathVariable UUID id) {
        Reply reply = workflowService.submitForReview(id);
        return ApiResponse.success("Reply submitted for review", reply);
    }

    @PostMapping("/{id}/decision")
    public ApiResponse<Reply> recordDecision(@PathVariable UUID id,
                                             @Valid @RequestBody ApprovalDecisionRequest request) {
        Reply reply = workflowService.processApprovalDecision(id, request);
        return ApiResponse.success("Approval decision recorded", reply);
    }

    @PostMapping("/{id}/post")
    public ApiResponse<Reply> markPosted(@PathVariable UUID id,
                                        @RequestParam(name = "platform_reply_id", required = false) String platformReplyId) {
        Reply reply = workflowService.markPosted(id, platformReplyId != null ? platformReplyId : UUID.randomUUID().toString());
        return ApiResponse.success("Reply marked as posted to platform", reply);
    }

    @GetMapping("/{id}")
    public ApiResponse<ReplyResponse> getReply(@PathVariable UUID id) {
        ReplyResponse resp = workflowService.getReplyDetails(id);
        return ApiResponse.success(resp);
    }

    @GetMapping
    public ApiResponse<PageResponse<Reply>> listReplies(
            @RequestParam(required = false, defaultValue = "IN_REVIEW") String status,
            @PageableDefault(size = 20) Pageable pageable) {
        Page<Reply> page = workflowService.listReplies(status, pageable);
        PageResponse<Reply> response = PageResponse.<Reply>builder()
                .content(page.getContent())
                .page(page.getNumber())
                .size(page.getSize())
                .totalElements(page.getTotalElements())
                .totalPages(page.getTotalPages())
                .hasNext(page.hasNext())
                .build();
        return ApiResponse.success(response);
    }

    @GetMapping("/breaching")
    public ApiResponse<List<Reply>> getBreachingReplies(
            @RequestParam(required = false, defaultValue = "120") int minutesAhead) {
        List<Reply> replies = workflowService.getBreachingReplies(minutesAhead);
        return ApiResponse.success(replies);
    }
}
