package io.yudhix.tenant.repository;

import io.yudhix.tenant.entity.TenantUser;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface TenantUserRepository extends JpaRepository<TenantUser, UUID> {
    List<TenantUser> findByTenantId(UUID tenantId);
    Optional<TenantUser> findByTenantIdAndKeycloakUserId(UUID tenantId, String keycloakUserId);
    Optional<TenantUser> findByTenantIdAndEmail(UUID tenantId, String email);
}
