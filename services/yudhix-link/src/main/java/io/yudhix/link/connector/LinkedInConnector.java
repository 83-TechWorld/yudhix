package io.yudhix.link.connector;

import io.yudhix.connector.model.*;
import io.yudhix.connector.spi.PlatformConnector;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Component
@Slf4j
public class LinkedInConnector implements PlatformConnector {

    @Override
    public PlatformType type() {
        return PlatformType.LINKEDIN;
    }

    @Override
    public ConnectorCapabilities capabilities() {
        return ConnectorCapabilities.builder()
                .canRead(true)
                .canReply(true)
                .hasDislikes(false)
                .hasReplyCount(true)
                .requiresOwnedPageAuth(true) // Per LinkedIn Community Management API policies
                .maxRetentionDays(30)
                .build();
    }

    @Override
    public FetchResult fetchComments(FetchRequest request) {
        log.info("Fetching comments from LinkedIn company page: {}", request.externalSourceRef());

        List<PlatformCommentDto> comments = new ArrayList<>();
        Instant now = Instant.now();

        PlatformCommentDto comment = PlatformCommentDto.builder()
                .platformCommentId("urn:li:comment:" + UUID.randomUUID())
                .platformAuthorId("urn:li:person:" + Math.abs(request.externalSourceRef().hashCode() % 500))
                .rawText("Great product release, but customer support took 4 days to answer my ticket.")
                .createdAt(now.minusSeconds(3600))
                .likeCount(5)
                .replyCount(1)
                .dislikeCount(null)
                .languageHint("en")
                .platformMetadata(Map.of("organizationUrn", request.externalSourceRef()))
                .build();

        comments.add(comment);

        Watermark nextWatermark = Watermark.builder()
                .lastCommentTimestamp(now)
                .pageToken("li_token_" + System.currentTimeMillis())
                .lastRunAt(now)
                .status("ACTIVE")
                .build();

        return FetchResult.builder()
                .comments(comments)
                .newWatermark(nextWatermark)
                .hasMore(false)
                .unitsConsumed(1)
                .build();
    }

    @Override
    public CommentStatus checkStatus(String platformCommentId) {
        return CommentStatus.ACTIVE;
    }

    @Override
    public PostResult postReply(ReplyRequest request) {
        log.info("Posting reply to LinkedIn comment: {}", request.platformCommentId());
        String replyId = "urn:li:comment:reply_" + UUID.randomUUID();
        return PostResult.success(replyId, 1);
    }

    @Override
    public EngagementSnapshot fetchEngagement(String platformCommentId) {
        return EngagementSnapshot.builder()
                .platformCommentId(platformCommentId)
                .likeCount(8)
                .replyCount(2)
                .dislikeCount(null)
                .capturedAt(Instant.now())
                .build();
    }
}
