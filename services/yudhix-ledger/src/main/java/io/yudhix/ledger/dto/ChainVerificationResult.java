package io.yudhix.ledger.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ChainVerificationResult {

    private UUID tenantId;
    private boolean valid;
    private long totalEventsVerified;
    private Long corruptedEventId;
    private String details;
    @Builder.Default
    private Instant verifiedAt = Instant.now();

    public static ChainVerificationResult success(UUID tenantId, long totalEvents) {
        return ChainVerificationResult.builder()
                .tenantId(tenantId)
                .valid(true)
                .totalEventsVerified(totalEvents)
                .details("Cryptographic hash chain is intact and fully verified from genesis.")
                .build();
    }

    public static ChainVerificationResult tampered(UUID tenantId, long eventId, String details) {
        return ChainVerificationResult.builder()
                .tenantId(tenantId)
                .valid(false)
                .corruptedEventId(eventId)
                .details(details)
                .build();
    }
}
