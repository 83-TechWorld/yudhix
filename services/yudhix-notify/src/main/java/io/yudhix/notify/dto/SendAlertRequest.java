package io.yudhix.notify.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SendAlertRequest {

    private UUID ruleId;

    @NotBlank
    private String eventType; // P1_ARRIVED, SLA_BREACH_WARNING, NEGATIVE_SPIKE

    @NotBlank
    private String severity; // CRITICAL, HIGH, MEDIUM

    @NotBlank
    private String recipient;

    @NotBlank
    private String subject;

    @NotBlank
    private String body;
}
