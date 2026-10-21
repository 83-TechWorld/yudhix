package io.yudhix.meter.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RecordUsageRequest {

    @NotBlank
    private String metricType; // comments_ingested, comments_llm_analyzed, replies_posted

    @Positive
    @Builder.Default
    private int quantity = 1;

    @NotBlank
    private String idempotencyKey;
}
