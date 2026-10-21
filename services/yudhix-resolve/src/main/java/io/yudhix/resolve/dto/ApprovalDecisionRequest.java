package io.yudhix.resolve.dto;

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
public class ApprovalDecisionRequest {

    @NotNull
    private UUID reviewerId;

    @NotBlank
    private String decision; // APPROVED, REJECTED, CHANGES_REQUESTED

    private String stepName; // e.g. "LEGAL_REVIEW", "BRAND_LEAD_REVIEW"

    private String comments;
}
