package io.yudhix.dharma.repository;

import io.yudhix.dharma.entity.PolicyDocument;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface PolicyDocumentRepository extends JpaRepository<PolicyDocument, UUID> {

    Optional<PolicyDocument> findByCodeAndCountryCodeAndVersion(String code, String countryCode, String version);

    @Query("SELECT p FROM PolicyDocument p WHERE p.countryCode IS NULL OR p.countryCode IN :countryCodes")
    List<PolicyDocument> findApplicablePolicies(@Param("countryCodes") List<String> countryCodes);
}
