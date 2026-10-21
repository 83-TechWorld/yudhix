package io.yudhix.tenant.repository;

import io.yudhix.tenant.entity.CountryConfig;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface CountryConfigRepository extends JpaRepository<CountryConfig, String> {
    List<CountryConfig> findByEnabledTrue();
}
