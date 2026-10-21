package io.yudhix.connector.model;

import lombok.Builder;

import java.util.UUID;

@Builder
public record ReplyRequest(
        UUID tenantId,
        UUID replyId,
        String platformCommentId,
        String replyText,
        String externalSourceRef
) {}
