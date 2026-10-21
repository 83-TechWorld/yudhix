package io.yudhix.connector.model;

import lombok.Builder;

import java.time.Instant;

/**
 * Tracks the incremental cursor position for a given source.
 */
@Builder
public record Watermark(
        Instant lastCommentTimestamp,
        String pageToken,
        Instant lastRunAt,
        String status
) {
    public static Watermark initial() {
        return new Watermark(null, null, null, "INITIAL");
    }
}
