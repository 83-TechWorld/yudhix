package io.yudhix.radar.service;

import io.yudhix.common.exception.ApiException;
import io.yudhix.radar.dto.DiscoveryRuleDto;
import io.yudhix.radar.dto.TopicDto;
import io.yudhix.radar.entity.DiscoveryRule;
import io.yudhix.radar.entity.Topic;
import io.yudhix.radar.repository.DiscoveryRuleRepository;
import io.yudhix.radar.repository.TopicRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class RadarService {

    private final TopicRepository topicRepository;
    private final DiscoveryRuleRepository ruleRepository;

    @Transactional
    public TopicDto createTopic(TopicDto dto) {
        log.info("Creating topic '{}' for tenant {}", dto.getName(), dto.getTenantId());

        if (topicRepository.existsByTenantIdAndName(dto.getTenantId(), dto.getName())) {
            throw new ApiException("Topic '" + dto.getName() + "' already exists for this tenant",
                    HttpStatus.CONFLICT, "TOPIC_NAME_CONFLICT");
        }

        Topic topic = Topic.builder()
                .tenantId(dto.getTenantId())
                .name(dto.getName().trim().toLowerCase())
                .description(dto.getDescription())
                .parentTopicId(dto.getParentTopicId())
                .autoDiscovered(dto.isAutoDiscovered())
                .build();

        Topic saved = topicRepository.save(topic);
        return TopicDto.from(saved);
    }

    @Transactional(readOnly = true)
    public List<TopicDto> getTopics(UUID tenantId) {
        return topicRepository.findByTenantId(tenantId).stream()
                .map(TopicDto::from)
                .collect(Collectors.toList());
    }

    @Transactional
    public DiscoveryRuleDto createRule(DiscoveryRuleDto dto) {
        log.info("Creating discovery rule '{}' for tenant {}", dto.getName(), dto.getTenantId());

        DiscoveryRule rule = DiscoveryRule.builder()
                .tenantId(dto.getTenantId())
                .name(dto.getName().trim())
                .enabled(dto.isEnabled())
                .ruleConfig(dto.getRuleConfig())
                .build();

        DiscoveryRule saved = ruleRepository.save(rule);
        return DiscoveryRuleDto.from(saved);
    }

    @Transactional(readOnly = true)
    public List<DiscoveryRuleDto> getRules(UUID tenantId) {
        return ruleRepository.findByTenantId(tenantId).stream()
                .map(DiscoveryRuleDto::from)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public List<DiscoveryRuleDto> getActiveRules(UUID tenantId) {
        return ruleRepository.findByTenantIdAndEnabledTrue(tenantId).stream()
                .map(DiscoveryRuleDto::from)
                .collect(Collectors.toList());
    }
}
