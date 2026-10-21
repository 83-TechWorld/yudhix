package io.yudhix.tenant.service;

import io.yudhix.common.exception.ApiException;
import io.yudhix.common.exception.TenantNotFoundException;
import io.yudhix.tenant.dto.TenantRegistrationRequest;
import io.yudhix.tenant.dto.TenantResponse;
import io.yudhix.tenant.dto.TenantSettingDto;
import io.yudhix.tenant.entity.CountryConfig;
import io.yudhix.tenant.entity.Tenant;
import io.yudhix.tenant.entity.TenantSetting;
import io.yudhix.tenant.repository.CountryConfigRepository;
import io.yudhix.tenant.repository.TenantRepository;
import io.yudhix.tenant.repository.TenantSettingRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class TenantService {

    private final TenantRepository tenantRepository;
    private final TenantSettingRepository settingRepository;
    private final CountryConfigRepository countryConfigRepository;

    @Transactional
    public TenantResponse registerTenant(TenantRegistrationRequest request) {
        log.info("Registering new tenant: {}", request.getName());

        if (tenantRepository.existsBySlug(request.getSlug())) {
            throw new ApiException("Tenant with slug '" + request.getSlug() + "' already exists",
                    HttpStatus.CONFLICT, "TENANT_SLUG_CONFLICT");
        }

        CountryConfig hqConfig = countryConfigRepository.findById(request.getHqCountry())
                .orElseThrow(() -> new ApiException("Invalid HQ country code: " + request.getHqCountry(),
                        HttpStatus.BAD_REQUEST, "INVALID_COUNTRY_CODE"));

        Tenant tenant = Tenant.builder()
                .name(request.getName().trim())
                .slug(request.getSlug().trim().toLowerCase())
                .hqCountry(hqConfig.getCountryCode())
                .operatingCountries(request.getOperatingCountries())
                .dataRegion(hqConfig.getDataRegion())
                .status("PENDING_CONSENT")
                .planCode(request.getPlanCode() != null ? request.getPlanCode() : "FREE_DEMO")
                .build();

        Tenant saved = tenantRepository.save(tenant);
        log.info("Tenant created with id: {}", saved.getId());
        return TenantResponse.from(saved);
    }

    @Transactional(readOnly = true)
    public TenantResponse getTenantById(UUID tenantId) {
        return tenantRepository.findById(tenantId)
                .map(TenantResponse::from)
                .orElseThrow(() -> new TenantNotFoundException(tenantId));
    }

    @Transactional(readOnly = true)
    public TenantResponse getTenantBySlug(String slug) {
        return tenantRepository.findBySlug(slug)
                .map(TenantResponse::from)
                .orElseThrow(() -> new ApiException("Tenant not found for slug: " + slug, HttpStatus.NOT_FOUND, "TENANT_NOT_FOUND"));
    }

    @Transactional
    public TenantResponse updateStatus(UUID tenantId, String newStatus) {
        Tenant tenant = tenantRepository.findById(tenantId)
                .orElseThrow(() -> new TenantNotFoundException(tenantId));

        tenant.setStatus(newStatus.toUpperCase());
        Tenant updated = tenantRepository.save(tenant);
        log.info("Tenant {} status updated to {}", tenantId, newStatus);
        return TenantResponse.from(updated);
    }

    @Transactional(readOnly = true)
    public List<TenantSettingDto> getSettings(UUID tenantId) {
        return settingRepository.findByTenantId(tenantId).stream()
                .map(s -> new TenantSettingDto(s.getSettingKey(), s.getSettingValue(), s.getUpdatedAt()))
                .collect(Collectors.toList());
    }

    @Transactional
    public TenantSettingDto saveSetting(UUID tenantId, TenantSettingDto dto) {
        TenantSetting setting = settingRepository.findByTenantIdAndSettingKey(tenantId, dto.getKey())
                .orElseGet(() -> TenantSetting.builder()
                        .tenantId(tenantId)
                        .settingKey(dto.getKey())
                        .build());

        setting.setSettingValue(dto.getValue());
        TenantSetting saved = settingRepository.save(setting);
        return new TenantSettingDto(saved.getSettingKey(), saved.getSettingValue(), saved.getUpdatedAt());
    }
}
