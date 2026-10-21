package io.yudhix.common.context;

import lombok.Builder;
import lombok.Getter;
import lombok.ToString;

import java.io.Serializable;
import java.util.Collections;
import java.util.Set;
import java.util.UUID;

/**
 * Encapsulates the authenticated tenant identity, user id, and authorized roles for the current request context.
 */
@Getter
@Builder
@ToString
public class TenantContext implements Serializable {

    private final UUID tenantId;
    private final UUID userId;
    private final String countryCode;
    @Builder.Default
    private final Set<String> roles = Collections.emptySet();

    public boolean hasRole(String role) {
        return roles != null && roles.contains(role);
    }
}
