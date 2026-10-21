package io.yudhix.tenant.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Entity
@Table(name = "tenant")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Tenant {

    @Id
    private UUID id;

    @Column(nullable = false)
    private String name;

    @Column(nullable = false, unique = true, length = 100)
    private String slug;

    @Column(name = "hq_country", nullable = false, length = 10)
    private String hqCountry;

    @Column(name = "operating_countries", columnDefinition = "text[]")
    @Builder.Default
    private List<String> operatingCountries = new ArrayList<>();

    @Column(name = "data_region", nullable = false, length = 50)
    @Builder.Default
    private String dataRegion = "ap-south-1";

    @Column(nullable = false, length = 50)
    @Builder.Default
    private String status = "PENDING_CONSENT"; // PENDING_CONSENT, ACTIVE, SUSPENDED

    @Column(name = "plan_code", nullable = false, length = 50)
    @Builder.Default
    private String planCode = "FREE_DEMO";

    @Column(name = "created_at", nullable = false, updatable = false)
    @Builder.Default
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    @Builder.Default
    private Instant updatedAt = Instant.now();

    @PrePersist
    public void prePersist() {
        if (id == null) {
            id = UUID.randomUUID();
        }
        if (createdAt == null) {
            createdAt = Instant.now();
        }
        updatedAt = Instant.now();
    }

    @PreUpdate
    public void preUpdate() {
        updatedAt = Instant.now();
    }
}
