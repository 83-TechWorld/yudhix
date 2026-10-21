package io.yudhix.tenant.controller;

import io.yudhix.common.dto.ApiResponse;
import io.yudhix.tenant.dto.CountryConfigDto;
import io.yudhix.tenant.repository.CountryConfigRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/v1/countries")
@RequiredArgsConstructor
public class CountryController {

    private final CountryConfigRepository countryConfigRepository;

    @GetMapping
    public ResponseEntity<ApiResponse<List<CountryConfigDto>>> getEnabledCountries() {
        List<CountryConfigDto> countries = countryConfigRepository.findByEnabledTrue().stream()
                .map(CountryConfigDto::from)
                .collect(Collectors.toList());

        return ResponseEntity.ok(ApiResponse.success(countries));
    }
}
