package io.yudhix.radar.controller;

import io.yudhix.common.dto.ApiResponse;
import io.yudhix.radar.dto.DiscoveryRuleDto;
import io.yudhix.radar.dto.TopicDto;
import io.yudhix.radar.service.RadarService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/rules")
@RequiredArgsConstructor
public class RadarController {

    private final RadarService radarService;

    @PostMapping("/topics")
    public ResponseEntity<ApiResponse<TopicDto>> createTopic(@Valid @RequestBody TopicDto dto) {
        TopicDto response = radarService.createTopic(dto);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success("Topic created", response));
    }

    @GetMapping("/topics/tenant/{tenantId}")
    public ResponseEntity<ApiResponse<List<TopicDto>>> getTopics(@PathVariable UUID tenantId) {
        List<TopicDto> topics = radarService.getTopics(tenantId);
        return ResponseEntity.ok(ApiResponse.success(topics));
    }

    @PostMapping
    public ResponseEntity<ApiResponse<DiscoveryRuleDto>> createRule(@Valid @RequestBody DiscoveryRuleDto dto) {
        DiscoveryRuleDto response = radarService.createRule(dto);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success("Rule created", response));
    }

    @GetMapping("/tenant/{tenantId}")
    public ResponseEntity<ApiResponse<List<DiscoveryRuleDto>>> getRules(@PathVariable UUID tenantId) {
        List<DiscoveryRuleDto> rules = radarService.getRules(tenantId);
        return ResponseEntity.ok(ApiResponse.success(rules));
    }

    @GetMapping("/tenant/{tenantId}/active")
    public ResponseEntity<ApiResponse<List<DiscoveryRuleDto>>> getActiveRules(@PathVariable UUID tenantId) {
        List<DiscoveryRuleDto> rules = radarService.getActiveRules(tenantId);
        return ResponseEntity.ok(ApiResponse.success(rules));
    }
}
