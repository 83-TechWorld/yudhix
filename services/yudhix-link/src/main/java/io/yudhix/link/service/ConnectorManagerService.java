package io.yudhix.link.service;

import io.yudhix.common.security.AuthorHasher;
import io.yudhix.common.security.InMemoryAuthorKeyProvider;
import io.yudhix.connector.model.*;
import io.yudhix.connector.spi.PlatformConnector;
import io.yudhix.link.entity.CommentStaging;
import io.yudhix.link.entity.SourceWatermark;
import io.yudhix.link.repository.CommentStagingRepository;
import io.yudhix.link.repository.SourceWatermarkRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
@Slf4j
public class ConnectorManagerService {

    private final Map<PlatformType, PlatformConnector> connectorMap;
    private final SourceWatermarkRepository watermarkRepository;
    private final CommentStagingRepository stagingRepository;
    private final AuthorHasher authorHasher;

    public ConnectorManagerService(
            List<PlatformConnector> connectors,
            SourceWatermarkRepository watermarkRepository,
            CommentStagingRepository stagingRepository) {
        this.connectorMap = connectors.stream()
                .collect(Collectors.toMap(PlatformConnector::type, Function.identity()));
        this.watermarkRepository = watermarkRepository;
        this.stagingRepository = stagingRepository;
        this.authorHasher = new AuthorHasher(new InMemoryAuthorKeyProvider());
    }

    @Transactional
    public int executeFetch(UUID tenantId, UUID sourceId, String platformName, String externalRef) {
        PlatformType platformType = PlatformType.valueOf(platformName.toUpperCase());
        PlatformConnector connector = connectorMap.get(platformType);

        if (connector == null) {
            throw new IllegalArgumentException("No connector available for platform: " + platformName);
        }

        // 1. Get or create watermark
        SourceWatermark watermarkEntity = watermarkRepository.findByTenantIdAndSourceIdAndPlatform(tenantId, sourceId, platformName)
                .orElseGet(() -> SourceWatermark.builder()
                        .tenantId(tenantId)
                        .sourceId(sourceId)
                        .platform(platformName)
                        .status("ACTIVE")
                        .build());

        Watermark currentWatermark = Watermark.builder()
                .lastCommentTimestamp(watermarkEntity.getLastCommentTs())
                .pageToken(watermarkEntity.getPageToken())
                .status(watermarkEntity.getStatus())
                .build();

        FetchRequest request = FetchRequest.builder()
                .tenantId(tenantId)
                .sourceId(sourceId)
                .externalSourceRef(externalRef)
                .watermark(currentWatermark)
                .rules(DiscoveryRuleSet.empty())
                .maxItems(100)
                .build();

        // 2. Fetch comments from platform API
        FetchResult result = connector.fetchComments(request);

        // 3. Hash author IDs and write to encrypted 24h comment_staging table
        for (PlatformCommentDto dto : result.comments()) {
            String authorHash = authorHasher.hash(tenantId, platformName, dto.platformAuthorId());

            CommentStaging staging = CommentStaging.builder()
                    .tenantId(tenantId)
                    .platform(platformName)
                    .platformCommentId(dto.platformCommentId())
                    .parentCommentId(dto.parentCommentId())
                    .sourceId(sourceId)
                    .authorHash(authorHash)
                    .rawText(dto.rawText())
                    .likeCount(dto.likeCount())
                    .replyCount(dto.replyCount())
                    .dislikeCount(dto.dislikeCount())
                    .platformCreatedAt(dto.createdAt())
                    .processed(false)
                    .build();

            stagingRepository.save(staging);
        }

        // 4. Update watermark
        if (result.newWatermark() != null) {
            watermarkEntity.setLastCommentTs(result.newWatermark().lastCommentTimestamp());
            watermarkEntity.setPageToken(result.newWatermark().pageToken());
            watermarkEntity.setLastRunAt(result.newWatermark().lastRunAt());
            watermarkRepository.save(watermarkEntity);
        }

        log.info("Fetched and staged {} comments for tenant {} on platform {}", result.comments().size(), tenantId, platformName);
        return result.comments().size();
    }
}
