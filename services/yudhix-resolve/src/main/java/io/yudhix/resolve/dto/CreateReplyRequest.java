package io.yudhix.resolve.dto;

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
public class CreateReplyRequest {

    @NotNull
    private UUID commentId;

    @NotBlank
    private String platform;

    @NotBlank
    private String replyText;

    @NotNull
    private UUID authorId;

    private Long slaMinutes; // default 120 (2h)
}
