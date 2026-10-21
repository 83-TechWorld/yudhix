package io.yudhix.connector.model;

import lombok.Builder;

import java.util.UUID;

@Builder
public record FetchRequest(
        UUID tenantId,
        UUID sourceId,
        String externalSourceRef, // e.g. YouTube Channel ID or LinkedIn Organization URN
        Watermark watermark,
        DiscoveryRuleSet rules,
        int maxItems
) {}
