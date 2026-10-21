package io.yudhix.pulse.entity;

import jakarta.persistence.*;
import lombok.*;

import java.io.Serializable;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "comment", uniqueConstraints = {
        @UniqueConstraint(columnNames = {"tenant_id", "platform", "platform_comment_id"})
})
@IdClass(Comment.CommentId.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Comment {

    @Id
    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Id
    @Column(nullable = false)
    private UUID id;

    @Column(nullable = false, length = 50)
    private String platform;

    @Column(name = "platform_comment_id", nullable = false)
    private String platformCommentId;

    @Column(name = "parent_comment_id")
    private String parentCommentId;

    @Column(name = "source_id", nullable = false)
    private UUID sourceId;

    @Column(name = "product_id")
    private UUID productId;

    @Column(name = "author_hash", nullable = false, length = 100)
    private String authorHash;

    @Column(name = "author_key_version", nullable = false)
    @Builder.Default
    private short authorKeyVersion = 1;

    @Column(name = "masked_text", columnDefinition = "text")
    private String maskedText;

    @Column(name = "text_expires_at", nullable = false)
    private Instant textExpiresAt;

    @Column(length = 10)
    private String language;

    @Column(name = "country_hint", length = 10)
    private String countryHint;

    @Column(name = "like_count", nullable = false)
    @Builder.Default
    private int likeCount = 0;

    @Column(name = "reply_count", nullable = false)
    @Builder.Default
    private int replyCount = 0;

    @Column(name = "dislike_count")
    private Integer dislikeCount;

    @Column(name = "platform_created_at", nullable = false)
    private Instant platformCreatedAt;

    @Column(name = "first_seen_at", nullable = false)
    @Builder.Default
    private Instant firstSeenAt = Instant.now();

    @Column(name = "last_seen_at", nullable = false)
    @Builder.Default
    private Instant lastSeenAt = Instant.now();

    @Column(name = "content_hash", nullable = false, length = 64)
    private String contentHash;

    @Column(nullable = false, length = 50)
    @Builder.Default
    private String status = "ACTIVE"; // ACTIVE, EDITED, DELETED_ON_PLATFORM

    @Column(name = "custom_attributes", nullable = false, columnDefinition = "jsonb")
    @Builder.Default
    private String customAttributes = "{}";

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CommentId implements Serializable {
        private UUID tenantId;
        private UUID id;
    }
}
