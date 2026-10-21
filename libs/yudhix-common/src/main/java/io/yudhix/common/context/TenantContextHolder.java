package io.yudhix.common.context;

import java.util.Optional;
import java.util.UUID;

/**
 * ThreadLocal-backed holder ensuring strict tenant isolation across service threads.
 */
public final class TenantContextHolder {

    private static final ThreadLocal<TenantContext> CONTEXT = new InheritableThreadLocal<>();

    private TenantContextHolder() {
    }

    public static void setContext(TenantContext context) {
        CONTEXT.set(context);
    }

    public static Optional<TenantContext> getContext() {
        return Optional.ofNullable(CONTEXT.get());
    }

    public static UUID getRequiredTenantId() {
        return getContext()
                .map(TenantContext::getTenantId)
                .orElseThrow(() -> new IllegalStateException("Missing required TenantContext in current thread execution."));
    }

    public static void clear() {
        CONTEXT.remove();
    }
}
