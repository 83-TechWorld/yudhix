package io.yudhix.dharma.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "policy_document")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class PolicyDocument {

    @Id
    private UUID id;

    @Column(nullable = false, length = 50)
    private String code;

    @Column(name = "country_code", length = 10)
    private String countryCode;

    @Column(length = 50)
    private String platform;

    @Column(nullable = false, length = 20)
    private String version;

    @Column(nullable = false)
    private String title;

    @Column(name = "body_md", nullable = false, columnDefinition = "text")
    private String bodyMd;

    @Column(name = "content_hash", nullable = false, length = 64)
    private String contentHash;

    @Column(name = "effective_from", nullable = false)
    @Builder.Default
    private Instant effectiveFrom = Instant.now();

    @Column(nullable = false)
    @Builder.Default
    private boolean mandatory = true;
}
