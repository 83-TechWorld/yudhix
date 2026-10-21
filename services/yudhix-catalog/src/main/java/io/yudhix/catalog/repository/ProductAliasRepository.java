package io.yudhix.catalog.repository;

import io.yudhix.catalog.entity.ProductAlias;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface ProductAliasRepository extends JpaRepository<ProductAlias, UUID> {
    List<ProductAlias> findByTenantId(UUID tenantId);
    List<ProductAlias> findByTenantIdAndProductId(UUID tenantId, UUID productId);
}
