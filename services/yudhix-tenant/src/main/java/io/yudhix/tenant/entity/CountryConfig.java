package io.yudhix.tenant.entity;

import jakarta.persistence.*;
import lombok.*;

import java.util.List;

@Entity
@Table(name = "country_config")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CountryConfig {

    @Id
    @Column(name = "country_code", length = 10)
    private String countryCode;

    @Column(name = "country_name", nullable = false)
    private String countryName;

    @Column(nullable = false)
    private boolean enabled;

    @Column(nullable = false, length = 10)
    private String currency;

    @Column(name = "tax_profile", nullable = false, length = 50)
    private String taxProfile;

    @Column(name = "data_region", nullable = false, length = 50)
    private String dataRegion;

    @Column(name = "default_retention_days", nullable = false)
    private int defaultRetentionDays;

    @Column(name = "ai_disclosure_required", nullable = false)
    private boolean aiDisclosureRequired;

    @Column(name = "policy_codes", columnDefinition = "text[]")
    private List<String> policyCodes;
}
