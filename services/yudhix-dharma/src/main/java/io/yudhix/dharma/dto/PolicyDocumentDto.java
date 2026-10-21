package io.yudhix.dharma.dto;

import io.yudhix.dharma.entity.PolicyDocument;
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
public class PolicyDocumentDto {

    private UUID id;
    private String code;
    private String countryCode;
    private String platform;
    private String version;
    private String title;
    private String bodyMd;
    private String contentHash;
    private Instant effectiveFrom;
    private boolean mandatory;

    public static PolicyDocumentDto from(PolicyDocument doc) {
        return PolicyDocumentDto.builder()
                .id(doc.getId())
                .code(doc.getCode())
                .countryCode(doc.getCountryCode())
                .platform(doc.getPlatform())
                .version(doc.getVersion())
                .title(doc.getTitle())
                .bodyMd(doc.getBodyMd())
                .contentHash(doc.getContentHash())
                .effectiveFrom(doc.getEffectiveFrom())
                .mandatory(doc.isMandatory())
                .build();
    }
}
