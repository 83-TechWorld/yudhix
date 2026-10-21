package io.yudhix.common.exception;

import org.springframework.http.HttpStatus;

import java.util.UUID;

public class TenantNotFoundException extends ApiException {

    public TenantNotFoundException(UUID tenantId) {
        super("Tenant with id '" + tenantId + "' not found or inactive", HttpStatus.NOT_FOUND, "TENANT_NOT_FOUND");
    }

    public TenantNotFoundException(String message) {
        super(message, HttpStatus.NOT_FOUND, "TENANT_NOT_FOUND");
    }
}
