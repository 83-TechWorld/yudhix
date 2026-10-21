package io.yudhix.pulse.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class IngestCommentRequest {

    @NotBlank
    private String platform;

    @NotBlank
    private String platformCommentId;

    private String parentCommentId;

    @NotNull
    private UUID sourceId;

    private UUID productId;

    @NotBlank
    private String authorHash;

    private short authorKeyVersion;

    private String maskedText;

    private Instant textExpiresAt;

    private String language;

    private String countryHint;

    private int likeCount;

    private int replyCount;

    private Integer dislikeCount;

    @NotNull
    private Instant platformCreatedAt;

    @NotBlank
    private String contentHash;

    private String customAttributes;
}
