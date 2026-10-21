package io.yudhix.link.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "source_watermark", uniqueConstraints = {
        @UniqueConstraint(columnNames = {"tenant_id", "source_id", "platform"})
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class SourceWatermark {

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Column(name = "source_id", nullable = false)
    private UUID sourceId;

    @Column(nullable = false, length = 50)
    private String platform;

    @Column(name = "last_comment_ts")
    private Instant lastCommentTs;

    @Column(name = "page_token", columnDefinition = "text")
    private String pageToken;

    @Column(name = "last_run_at", nullable = false)
    @Builder.Default
    private Instant lastRunAt = Instant.now();

    @Column(nullable = false, length = 50)
    @Builder.Default
    private String status = "ACTIVE";

    @PrePersist
    public void prePersist() {
        if (id == null) {
            id = UUID.randomUUID();
        }
        if (lastRunAt == null) {
            lastRunAt = Instant.now();
        }
    }
}
