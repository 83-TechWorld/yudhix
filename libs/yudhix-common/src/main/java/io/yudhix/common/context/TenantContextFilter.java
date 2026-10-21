package io.yudhix.common.context;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.lang.NonNull;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Filter that populates TenantContext from incoming Gateway headers:
 * - X-Tenant-Id (required for tenant-isolated endpoints)
 * - X-User-Id (optional/contextual)
 * - X-User-Roles (comma-separated Keycloak roles)
 */
public class TenantContextFilter extends OncePerRequestFilter {

    public static final String HEADER_TENANT_ID = "X-Tenant-Id";
    public static final String HEADER_USER_ID = "X-User-Id";
    public static final String HEADER_USER_ROLES = "X-User-Roles";
    public static final String HEADER_COUNTRY_CODE = "X-Country-Code";

    @Override
    protected void doFilterInternal(
            @NonNull HttpServletRequest request,
            @NonNull HttpServletResponse response,
            @NonNull FilterChain filterChain) throws ServletException, IOException {

        try {
            String tenantHeader = request.getHeader(HEADER_TENANT_ID);
            if (StringUtils.hasText(tenantHeader)) {
                UUID tenantId = UUID.fromString(tenantHeader.trim());
                UUID userId = parseUuid(request.getHeader(HEADER_USER_ID));
                String country = request.getHeader(HEADER_COUNTRY_CODE);
                Set<String> roles = parseRoles(request.getHeader(HEADER_USER_ROLES));

                TenantContext context = TenantContext.builder()
                        .tenantId(tenantId)
                        .userId(userId)
                        .countryCode(country)
                        .roles(roles)
                        .build();

                TenantContextHolder.setContext(context);
            }

            filterChain.doFilter(request, response);
        } finally {
            TenantContextHolder.clear();
        }
    }

    private UUID parseUuid(String value) {
        if (!StringUtils.hasText(value)) {
            return null;
        }
        try {
            return UUID.fromString(value.trim());
        } catch (IllegalArgumentException e) {
            return null;
        }
    }

    private Set<String> parseRoles(String rolesHeader) {
        if (!StringUtils.hasText(rolesHeader)) {
            return Collections.emptySet();
        }
        return Arrays.stream(rolesHeader.split(","))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .collect(Collectors.toUnmodifiableSet());
    }
}
