package io.yudhix.connector.spi;

import io.yudhix.connector.model.*;

/**
 * Service Provider Interface (SPI) implemented by every social platform connector.
 */
public interface PlatformConnector {

    /**
     * The platform identifier (YOUTUBE, LINKEDIN, etc.)
     */
    PlatformType type();

    /**
     * Declares supported read/reply capabilities and retention parameters.
     */
    ConnectorCapabilities capabilities();

    /**
     * Incrementally fetches comments since the previous watermark cursor.
     */
    FetchResult fetchComments(FetchRequest request);

    /**
     * Verifies if a comment is still ACTIVE or has been EDITED / DELETED on the platform.
     */
    CommentStatus checkStatus(String platformCommentId);

    /**
     * Posts an approved reply to a target comment thread.
     */
    PostResult postReply(ReplyRequest request);

    /**
     * Refreshes likes, replies, and reactions for comments undergoing velocity calculation.
     */
    EngagementSnapshot fetchEngagement(String platformCommentId);
}
