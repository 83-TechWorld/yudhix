package io.yudhix.connector.model;

import lombok.Builder;

import java.time.Instant;

@Builder
public record PostResult(
        boolean success,
        String platformReplyId,
        Instant postedAt,
        String errorMessage,
        int unitsConsumed
) {
    public static PostResult success(String platformReplyId, int unitsConsumed) {
        return new PostResult(true, platformReplyId, Instant.now(), null, unitsConsumed);
    }

    public static PostResult failure(String errorMessage, int unitsConsumed) {
        return new PostResult(false, null, null, errorMessage, unitsConsumed);
    }
}
