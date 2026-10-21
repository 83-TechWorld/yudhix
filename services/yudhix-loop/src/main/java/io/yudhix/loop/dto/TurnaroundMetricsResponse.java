package io.yudhix.loop.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TurnaroundMetricsResponse {
    private long totalNegativeReplied;
    private long totalTurnedAround;
    private BigDecimal turnaroundRatePercent; // e.g. 64.50%
}
