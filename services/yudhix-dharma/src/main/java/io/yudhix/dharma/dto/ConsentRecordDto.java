package io.yudhix.dharma.dto;

import io.yudhix.dharma.entity.ConsentRecord;
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
public class ConsentRecordDto {

    private UUID id;
    private UUID tenantId;
    private UUID policyId;
    private String policyCode;
    private String policyTitle;
    private String contentHash;
    private String acceptedBy;
    private String signerName;
    private String signerTitle;
    private Instant acceptedAt;

    public static ConsentRecordDto from(ConsentRecord record) {
        return ConsentRecordDto.builder()
                .id(record.getId())
                .tenantId(record.getTenantId())
                .policyId(record.getPolicy().getId())
                .policyCode(record.getPolicy().getCode())
                .policyTitle(record.getPolicy().getTitle())
                .contentHash(record.getContentHash())
                .acceptedBy(record.getAcceptedBy())
                .signerName(record.getSignerName())
                .signerTitle(record.getSignerTitle())
                .acceptedAt(record.getAcceptedAt())
                .build();
    }
}
