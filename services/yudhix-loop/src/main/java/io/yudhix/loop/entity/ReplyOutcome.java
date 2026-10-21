package io.yudhix.loop.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "reply_outcome")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ReplyOutcome {

    @Id
    @Column(nullable = false)
    private UUID id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Column(name = "reply_id", nullable = false)
    private UUID replyId;

    @Column(name = "comment_id", nullable = false)
    private UUID commentId;

    @Column(name = "initial_sentiment", nullable = false, length = 20)
    private String initialSentiment;

    @Column(name = "checkpoint_24h_sentiment", length = 20)
    private String checkpoint24hSentiment;

    @Column(name = "checkpoint_72h_sentiment", length = 20)
    private String checkpoint72hSentiment;

    @Column(name = "checkpoint_7d_sentiment", length = 20)
    private String checkpoint7dSentiment;

    @Column(name = "turned_around", nullable = false)
    @Builder.Default
    private boolean turnedAround = false;

    @Column(name = "follow_up_comment_id")
    private String followUpCommentId;

    @Column(columnDefinition = "text")
    private String notes;

    @Column(name = "evaluated_at", nullable = false)
    @Builder.Default
    private Instant evaluatedAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    @Builder.Default
    private Instant updatedAt = Instant.now();
}
