package io.yudhix.resolve.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "reply")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Reply {

    @Id
    @Column(nullable = false)
    private UUID id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Column(name = "comment_id", nullable = false)
    private UUID commentId;

    @Column(nullable = false, length = 50)
    private String platform;

    @Column(name = "reply_text", nullable = false, columnDefinition = "text")
    private String replyText;

    @Column(nullable = false, length = 50)
    @Builder.Default
    private String status = "DRAFT"; // DRAFT, IN_REVIEW, APPROVED, REJECTED, POSTED

    @Column(name = "author_id", nullable = false)
    private UUID authorId;

    @Column(name = "approver_id")
    private UUID approverId;

    @Column(name = "sla_due_at", nullable = false)
    private Instant slaDueAt;

    @Column(name = "posted_at")
    private Instant postedAt;

    @Column(name = "platform_reply_id")
    private String platformReplyId;

    @Column(name = "rejection_reason", columnDefinition = "text")
    private String rejectionReason;

    @Column(name = "created_at", nullable = false)
    @Builder.Default
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    @Builder.Default
    private Instant updatedAt = Instant.now();
}
