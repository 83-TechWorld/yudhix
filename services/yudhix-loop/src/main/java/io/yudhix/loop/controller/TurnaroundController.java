package io.yudhix.loop.controller;

import io.yudhix.common.dto.ApiResponse;
import io.yudhix.common.dto.PageResponse;
import io.yudhix.loop.dto.RecordCheckpointRequest;
import io.yudhix.loop.dto.RecordFeedbackRequest;
import io.yudhix.loop.dto.TurnaroundMetricsResponse;
import io.yudhix.loop.entity.LabelFeedback;
import io.yudhix.loop.entity.ReplyOutcome;
import io.yudhix.loop.service.TurnaroundService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/loop")
@RequiredArgsConstructor
public class TurnaroundController {

    private final TurnaroundService turnaroundService;

    @PostMapping("/checkpoints")
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<ReplyOutcome> recordCheckpoint(@Valid @RequestBody RecordCheckpointRequest request) {
        ReplyOutcome outcome = turnaroundService.recordCheckpoint(request);
        return ApiResponse.success("Checkpoint recorded successfully", outcome);
    }

    @GetMapping("/metrics")
    public ApiResponse<TurnaroundMetricsResponse> getMetrics() {
        TurnaroundMetricsResponse metrics = turnaroundService.getTurnaroundMetrics();
        return ApiResponse.success(metrics);
    }

    @PostMapping("/feedback")
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<LabelFeedback> recordFeedback(@Valid @RequestBody RecordFeedbackRequest request) {
        LabelFeedback feedback = turnaroundService.recordLabelFeedback(request);
        return ApiResponse.success("Label feedback recorded for AI calibration", feedback);
    }

    @GetMapping("/feedback")
    public ApiResponse<PageResponse<LabelFeedback>> listFeedback(@PageableDefault(size = 20) Pageable pageable) {
        Page<LabelFeedback> page = turnaroundService.listFeedback(pageable);
        PageResponse<LabelFeedback> response = PageResponse.<LabelFeedback>builder()
                .content(page.getContent())
                .page(page.getNumber())
                .size(page.getSize())
                .totalElements(page.getTotalElements())
                .totalPages(page.getTotalPages())
                .hasNext(page.hasNext())
                .build();
        return ApiResponse.success(response);
    }
}
