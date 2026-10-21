package io.yudhix.pulse.controller;

import io.yudhix.common.dto.ApiResponse;
import io.yudhix.common.dto.PageResponse;
import io.yudhix.pulse.dto.AnalysisResultRequest;
import io.yudhix.pulse.dto.CommentResponse;
import io.yudhix.pulse.dto.IngestCommentRequest;
import io.yudhix.pulse.entity.Comment;
import io.yudhix.pulse.entity.CommentAnalysis;
import io.yudhix.pulse.service.CommentService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/api/v1/comments")
@RequiredArgsConstructor
public class CommentController {

    private final CommentService commentService;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<Comment> ingest(@Valid @RequestBody IngestCommentRequest request) {
        Comment comment = commentService.ingestComment(request);
        return ApiResponse.success("Comment ingested successfully", comment);
    }

    @GetMapping("/{id}")
    public ApiResponse<CommentResponse> getComment(@PathVariable UUID id) {
        CommentResponse resp = commentService.getCommentDetails(id);
        return ApiResponse.success(resp);
    }

    @PostMapping("/{id}/analysis")
    public ApiResponse<CommentAnalysis> saveAnalysis(@PathVariable UUID id,
                                                   @Valid @RequestBody AnalysisResultRequest request) {
        CommentAnalysis analysis = commentService.saveAnalysis(id, request);
        return ApiResponse.success("Analysis recorded successfully", analysis);
    }

    @GetMapping("/inbox")
    public ApiResponse<PageResponse<CommentAnalysis>> getInbox(
            @RequestParam(required = false) String priority,
            @RequestParam(required = false) Boolean needsReview,
            @PageableDefault(size = 20) Pageable pageable) {

        Page<CommentAnalysis> page = commentService.getInboxItems(priority, needsReview, pageable);
        PageResponse<CommentAnalysis> response = PageResponse.<CommentAnalysis>builder()
                .content(page.getContent())
                .page(page.getNumber())
                .size(page.getSize())
                .totalElements(page.getTotalElements())
                .totalPages(page.getTotalPages())
                .hasNext(page.hasNext())
                .build();

        return ApiResponse.success(response);
    }

    @PostMapping("/retention/enforce")
    public ApiResponse<Integer> enforceRetention() {
        int erased = commentService.enforceTextRetention();
        return ApiResponse.success("Retention enforced successfully", erased);
    }
}
