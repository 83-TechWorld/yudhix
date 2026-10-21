package io.yudhix.connector.model;

import lombok.Builder;

/**
 * Declares the feature capabilities of a platform connector.
 */
@Builder
public record ConnectorCapabilities(
        boolean canRead,
        boolean canReply,
        boolean hasDislikes,
        boolean hasReplyCount,
        boolean requiresOwnedPageAuth,
        int maxRetentionDays
) {}
