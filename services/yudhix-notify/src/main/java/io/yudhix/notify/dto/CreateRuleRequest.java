package io.yudhix.notify.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CreateRuleRequest {

    @NotBlank
    private String name;

    @NotBlank
    private String ruleType; // CRISIS_SPIKE, P1_ALERT, SLA_BREACH

    private BigDecimal thresholdValue;

    @NotBlank
    private String channel; // EMAIL, WEBHOOK, SLACK

    @NotBlank
    private String targetDestination;
}
