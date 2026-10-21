package io.yudhix.meter.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class QuotaStatusResponse {
    private String planId;
    private String planName;
    private long commentsIngested;
    private int commentQuota;
    private long llmAnalyzed;
    private int llmQuota;
    private long repliesPosted;
    private int replyQuota;
    private boolean quotaExceeded;
}
