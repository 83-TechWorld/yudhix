package io.yudhix.pulse.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AnalysisResultRequest {

    @NotBlank
    private String modelVersion;

    @NotBlank
    private String sentiment;

    @NotNull
    private BigDecimal sentimentScore;

    private String intent;

    private UUID topicId;

    private boolean toxic;

    private BigDecimal churnRisk;

    private String suggestedReply;

    private List<AspectItem> aspects;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class AspectItem {
        private String aspect;
        private String sentiment;
        private BigDecimal score;
        private String evidence;
    }
}
