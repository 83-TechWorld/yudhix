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
public class YouTubeConnector implements PlatformConnector {

    @Override
    public PlatformType type() {
        return PlatformType.YOUTUBE;
    }

    @Override
    public ConnectorCapabilities capabilities() {
        return ConnectorCapabilities.builder()
                .canRead(true)
                .canReply(true)
                .hasDislikes(false) // YouTube removed public dislikes in 2021
                .hasReplyCount(true)
                .requiresOwnedPageAuth(false)
                .maxRetentionDays(30)
                .build();
    }

    @Override
    public FetchResult fetchComments(FetchRequest request) {
        log.info("Fetching comments from YouTube for source: {}", request.externalSourceRef());

        // Standard simulated API fetch structure (ready for YouTube Data API v3 Google Client)
        List<PlatformCommentDto> comments = new ArrayList<>();
        Instant now = Instant.now();

        // Sample harvested comment simulating live social activity
        PlatformCommentDto comment = PlatformCommentDto.builder()
                .platformCommentId("yt_c_" + UUID.randomUUID())
                .platformAuthorId("UC_author_" + Math.abs(request.externalSourceRef().hashCode() % 1000))
                .rawText("The battery life on this DualSense controller is terrible, dies in 2 hours! Please fix.")
                .createdAt(now.minusSeconds(1800))
                .likeCount(14)
                .replyCount(3)
                .dislikeCount(null)
                .languageHint("en")
                .platformMetadata(Map.of("videoId", "v_sample_123", "channelId", request.externalSourceRef()))
                .build();

        comments.add(comment);

        Watermark nextWatermark = Watermark.builder()
                .lastCommentTimestamp(now)
                .pageToken("yt_token_" + System.currentTimeMillis())
                .lastRunAt(now)
                .status("ACTIVE")
                .build();

        return FetchResult.builder()
                .comments(comments)
                .newWatermark(nextWatermark)
                .hasMore(false)
                .unitsConsumed(1) // 1 quota unit
                .build();
    }

    @Override
    public CommentStatus checkStatus(String platformCommentId) {
        return CommentStatus.ACTIVE;
    }

    @Override
    public PostResult postReply(ReplyRequest request) {
        log.info("Posting reply to YouTube comment: {}", request.platformCommentId());
        String replyId = "yt_r_" + UUID.randomUUID();
        return PostResult.success(replyId, 50); // comments.insert consumes 50 quota units
    }

    @Override
    public EngagementSnapshot fetchEngagement(String platformCommentId) {
        return EngagementSnapshot.builder()
                .platformCommentId(platformCommentId)
                .likeCount(25)
                .replyCount(5)
                .dislikeCount(null)
                .capturedAt(Instant.now())
                .build();
    }
}
