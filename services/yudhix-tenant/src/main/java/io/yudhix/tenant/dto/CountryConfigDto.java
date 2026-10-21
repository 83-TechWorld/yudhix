package io.yudhix.tenant.dto;

import io.yudhix.tenant.entity.CountryConfig;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CountryConfigDto {

    private String countryCode;
    private String countryName;
    private boolean enabled;
    private String currency;
    private String taxProfile;
    private String dataRegion;
    private int defaultRetentionDays;
    private boolean aiDisclosureRequired;
    private List<String> policyCodes;

    public static CountryConfigDto from(CountryConfig config) {
        return CountryConfigDto.builder()
                .countryCode(config.getCountryCode())
                .countryName(config.getCountryName())
                .enabled(config.isEnabled())
                .currency(config.getCurrency())
                .taxProfile(config.getTaxProfile())
                .dataRegion(config.getDataRegion())
                .defaultRetentionDays(config.getDefaultRetentionDays())
                .aiDisclosureRequired(config.isAiDisclosureRequired())
                .policyCodes(config.getPolicyCodes())
                .build();
    }
}
