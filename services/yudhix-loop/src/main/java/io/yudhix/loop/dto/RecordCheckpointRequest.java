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
public class RecordCheckpointRequest {

    @NotNull
    private UUID replyId;

    @NotNull
    private UUID commentId;

    @NotBlank
    private String initialSentiment;

    private String interval; // "24H", "72H", "7D"

    private String followUpSentiment;

    private String followUpCommentId;

    private String notes;
}
