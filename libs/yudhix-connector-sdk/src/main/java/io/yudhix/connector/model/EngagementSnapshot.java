package io.yudhix.connector.model;

import lombok.Builder;

import java.time.Instant;

@Builder
public record EngagementSnapshot(
        String platformCommentId,
        int likeCount,
        int replyCount,
        Integer dislikeCount,
        Instant capturedAt
) {}
