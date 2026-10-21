package io.yudhix.connector.model;

import lombok.Builder;

import java.time.Instant;
import java.util.Map;

/**
 * Normalized comment payload produced by all connectors before PII masking.
 * Note: authorId is the raw platform author identifier, which will be hashed into author_hash before persistence.
 */
@Builder
public record PlatformCommentDto(
        String platformCommentId,
        String parentCommentId,
        String platformAuthorId,
        String rawText,
        Instant createdAt,
        int likeCount,
        int replyCount,
        Integer dislikeCount,
        String languageHint,
        Map<String, Object> platformMetadata
) {}
