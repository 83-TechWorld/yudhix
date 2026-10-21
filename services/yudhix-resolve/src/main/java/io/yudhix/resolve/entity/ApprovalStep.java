package io.yudhix.resolve.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "approval_step")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ApprovalStep {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Column(name = "reply_id", nullable = false)
    private UUID replyId;

    @Column(name = "step_name", nullable = false, length = 100)
    private String stepName;

    @Column(name = "reviewer_id", nullable = false)
    private UUID reviewerId;

    @Column(nullable = false, length = 50)
    private String decision; // APPROVED, REJECTED, CHANGES_REQUESTED

    @Column(columnDefinition = "text")
    private String comments;

    @Column(name = "action_at", nullable = false)
    @Builder.Default
    private Instant actionAt = Instant.now();
}
