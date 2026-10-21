package io.yudhix.dharma.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "consent_record")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ConsentRecord {

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "policy_id", nullable = false)
    private PolicyDocument policy;

    @Column(name = "content_hash", nullable = false, length = 64)
    private String contentHash;

    @Column(name = "accepted_by", nullable = false, length = 100)
    private String acceptedBy;

    @Column(name = "signer_name", nullable = false)
    private String signerName;

    @Column(name = "signer_title")
    private String signerTitle;

    @Column(name = "accepted_at", nullable = false)
    @Builder.Default
    private Instant acceptedAt = Instant.now();

    @Column(name = "ip_hash", length = 100)
    private String ipHash;

    @Column(name = "withdrawn_at")
    private Instant withdrawnAt;

    @PrePersist
    public void prePersist() {
        if (id == null) {
            id = UUID.randomUUID();
        }
        if (acceptedAt == null) {
            acceptedAt = Instant.now();
        }
    }
}
