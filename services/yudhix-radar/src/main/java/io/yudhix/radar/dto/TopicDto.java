package io.yudhix.radar.dto;

import io.yudhix.radar.entity.Topic;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
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
public class TopicDto {

    private UUID id;

    @NotNull(message = "tenantId is required")
    private UUID tenantId;

    @NotBlank(message = "Topic name is required (e.g. battery-quality)")
    private String name;

    private String description;
    private UUID parentTopicId;
    private boolean autoDiscovered;
    private Instant createdAt;

    public static TopicDto from(Topic topic) {
        return TopicDto.builder()
                .id(topic.getId())
                .tenantId(topic.getTenantId())
                .name(topic.getName())
                .description(topic.getDescription())
                .parentTopicId(topic.getParentTopicId())
                .autoDiscovered(topic.isAutoDiscovered())
                .createdAt(topic.getCreatedAt())
                .build();
    }
}
