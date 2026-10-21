package io.yudhix.notify.controller;

import io.yudhix.common.dto.ApiResponse;
import io.yudhix.notify.dto.CreateRuleRequest;
import io.yudhix.notify.dto.SendAlertRequest;
import io.yudhix.notify.entity.NotificationLog;
import io.yudhix.notify.entity.NotificationRule;
import io.yudhix.notify.service.NotificationService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/notify")
@RequiredArgsConstructor
public class NotificationController {

    private final NotificationService notificationService;

    @PostMapping("/rules")
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<NotificationRule> createRule(@Valid @RequestBody CreateRuleRequest request) {
        NotificationRule rule = notificationService.createRule(request);
        return ApiResponse.success("Notification rule created successfully", rule);
    }

    @GetMapping("/rules")
    public ApiResponse<List<NotificationRule>> listRules() {
        List<NotificationRule> rules = notificationService.listRules();
        return ApiResponse.success(rules);
    }

    @PostMapping("/alerts")
    public ApiResponse<NotificationLog> dispatchAlert(@Valid @RequestBody SendAlertRequest request) {
        NotificationLog log = notificationService.dispatchAlert(request);
        return ApiResponse.success("Alert processed", log);
    }
}
