package io.yudhix.pulse.dto;

import io.yudhix.pulse.entity.CommentAnalysis;
import io.yudhix.pulse.entity.CommentAspect;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CommentResponse {
    private UUID id;
    private UUID tenantId;
    private String platform;
    private String platformCommentId;
    private String parentCommentId;
    private UUID sourceId;
    private UUID productId;
    private String authorHash;
    private String maskedText;
    private Instant textExpiresAt;
    private String language;
    private String countryHint;
    private int likeCount;
    private int replyCount;
    private Instant platformCreatedAt;
    private Instant firstSeenAt;
    private Instant lastSeenAt;
    private String status;
    private CommentAnalysis analysis;
    private List<CommentAspect> aspects;
}
