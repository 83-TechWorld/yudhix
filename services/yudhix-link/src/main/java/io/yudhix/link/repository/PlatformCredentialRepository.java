package io.yudhix.link.repository;

import io.yudhix.link.entity.PlatformCredential;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface PlatformCredentialRepository extends JpaRepository<PlatformCredential, UUID> {
    Optional<PlatformCredential> findByTenantIdAndPlatform(UUID tenantId, String platform);
}
