package io.yudhix.link.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "comment_staging")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CommentStaging {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Column(nullable = false, length = 50)
    private String platform;

    @Column(name = "platform_comment_id", nullable = false)
    private String platformCommentId;

    @Column(name = "parent_comment_id")
    private String parentCommentId;

    @Column(name = "source_id", nullable = false)
    private UUID sourceId;

    @Column(name = "author_hash", nullable = false, length = 100)
    private String authorHash;

    @Column(name = "raw_text", nullable = false, columnDefinition = "text")
    private String rawText;

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

    @Column(name = "created_at", nullable = false, updatable = false)
    @Builder.Default
    private Instant createdAt = Instant.now();

    @Column(name = "expires_at", nullable = false)
    private Instant expiresAt;

    @Column(nullable = false)
    @Builder.Default
    private boolean processed = false;

    @PrePersist
    public void prePersist() {
        if (createdAt == null) {
            createdAt = Instant.now();
        }
        if (expiresAt == null) {
            expiresAt = Instant.now().plusSeconds(86400); // 24 hours TTL
        }
    }
}
