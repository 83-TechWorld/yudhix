package io.yudhix.connector.model;

import lombok.Builder;

import java.util.List;
import java.util.Set;

/**
 * Filter rules applied during ingestion to minimize noise at the connector level.
 */
@Builder
public record DiscoveryRuleSet(
        Set<String> keywords,
        Set<String> excludeKeywords,
        int minLikes,
        int minReplies,
        Integer minDislikes,
        List<String> targetLanguages
) {
    public static DiscoveryRuleSet empty() {
        return new DiscoveryRuleSet(Set.of(), Set.of(), 0, 0, null, List.of());
    }
}
