package io.yudhix.loop.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "label_feedback")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class LabelFeedback {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Column(name = "comment_id", nullable = false)
    private UUID commentId;

    @Column(name = "reviewer_id", nullable = false)
    private UUID reviewerId;

    @Column(name = "original_sentiment", nullable = false, length = 20)
    private String originalSentiment;

    @Column(name = "corrected_sentiment", nullable = false, length = 20)
    private String correctedSentiment;

    @Column(name = "original_toxic", nullable = false)
    @Builder.Default
    private boolean originalToxic = false;

    @Column(name = "corrected_toxic", nullable = false)
    @Builder.Default
    private boolean correctedToxic = false;

    @Column(columnDefinition = "text")
    private String reason;

    @Column(name = "created_at", nullable = false)
    @Builder.Default
    private Instant createdAt = Instant.now();
}
