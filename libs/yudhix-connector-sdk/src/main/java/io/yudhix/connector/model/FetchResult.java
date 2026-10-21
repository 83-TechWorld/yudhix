package io.yudhix.connector.model;

import lombok.Builder;

import java.util.List;

@Builder
public record FetchResult(
        List<PlatformCommentDto> comments,
        Watermark newWatermark,
        boolean hasMore,
        int unitsConsumed
) {}
