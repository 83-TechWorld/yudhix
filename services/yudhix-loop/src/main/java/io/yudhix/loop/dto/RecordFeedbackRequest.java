package io.yudhix.loop.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RecordFeedbackRequest {

    @NotNull
    private UUID commentId;

    @NotNull
    private UUID reviewerId;

    @NotBlank
    private String originalSentiment;

    @NotBlank
    private String correctedSentiment;

    private boolean originalToxic;

    private boolean correctedToxic;

    private String reason;
}
