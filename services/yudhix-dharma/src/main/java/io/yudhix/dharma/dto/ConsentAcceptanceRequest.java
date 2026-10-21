package io.yudhix.dharma.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ConsentAcceptanceRequest {

    @NotNull(message = "tenantId is required")
    private UUID tenantId;

    @NotNull(message = "policyId is required")
    private UUID policyId;

    @NotBlank(message = "contentHash is required to prove what version was displayed")
    private String contentHash;

    @NotBlank(message = "acceptedBy (Keycloak user ID) is required")
    private String acceptedBy;

    @NotBlank(message = "Signer name is required")
    private String signerName;

    private String signerTitle;
    private String ipHash;
}
