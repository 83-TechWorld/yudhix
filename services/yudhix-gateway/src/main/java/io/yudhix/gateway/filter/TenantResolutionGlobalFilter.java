package io.yudhix.gateway.filter;

import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.security.core.context.ReactiveSecurityContextHolder;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.UUID;

/**
 * High-priority Global Filter that extracts tenant identity from JWT claims or client headers,
 * enforces UUID validation, and injects X-Tenant-Id, X-User-Id, and X-User-Roles into downstream requests.
 */
@Component
public class TenantResolutionGlobalFilter implements GlobalFilter, Ordered {

    public static final String HEADER_TENANT_ID = "X-Tenant-Id";
    public static final String HEADER_USER_ID = "X-User-Id";
    public static final String HEADER_USER_ROLES = "X-User-Roles";

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getURI().getPath();

        // Skip tenant extraction for public or health check routes
        if (path.startsWith("/actuator") || path.startsWith("/api/v1/countries") || path.equals("/api/v1/tenants/register")) {
            return chain.filter(exchange);
        }

        return ReactiveSecurityContextHolder.getContext()
                .map(SecurityContext::getAuthentication)
                .filter(auth -> auth instanceof JwtAuthenticationToken)
                .cast(JwtAuthenticationToken.class)
                .flatMap(jwtAuth -> {
                    Jwt jwt = jwtAuth.getToken();

                    // Extract tenant_id from JWT claims (Keycloak custom attribute or org attribute)
                    String tenantClaim = jwt.getClaimAsString("tenant_id");
                    if (!StringUtils.hasText(tenantClaim)) {
                        // Fallback to client request header if provided in development/internal calls
                        tenantClaim = exchange.getRequest().getHeaders().getFirst(HEADER_TENANT_ID);
                    }

                    if (!StringUtils.hasText(tenantClaim)) {
                        exchange.getResponse().setStatusCode(HttpStatus.FORBIDDEN);
                        return exchange.getResponse().setComplete();
                    }

                    try {
                        UUID.fromString(tenantClaim.trim()); // Validate valid UUID format
                    } catch (IllegalArgumentException e) {
                        exchange.getResponse().setStatusCode(HttpStatus.BAD_REQUEST);
                        return exchange.getResponse().setComplete();
                    }

                    String userId = jwt.getSubject();
                    String roles = String.join(",", jwtAuth.getAuthorities().stream()
                            .map(Object::toString)
                            .toList());

                    // Mutate request with verified security headers for downstream microservices
                    ServerHttpRequest mutatedRequest = exchange.getRequest().mutate()
                            .header(HEADER_TENANT_ID, tenantClaim.trim())
                            .header(HEADER_USER_ID, userId != null ? userId : "")
                            .header(HEADER_USER_ROLES, roles)
                            .build();

                    return chain.filter(exchange.mutate().request(mutatedRequest).build());
                })
                .switchIfEmpty(Mono.defer(() -> {
                    // If no JWT was provided and endpoint is not permitted, return 401
                    String tenantHeader = exchange.getRequest().getHeaders().getFirst(HEADER_TENANT_ID);
                    if (StringUtils.hasText(tenantHeader)) {
                        // Allow internal service-to-service calls that supply X-Tenant-Id
                        return chain.filter(exchange);
                    }
                    exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
                    return exchange.getResponse().setComplete();
                }));
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE + 10;
    }
}
