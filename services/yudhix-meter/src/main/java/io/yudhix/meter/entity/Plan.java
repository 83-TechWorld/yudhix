package io.yudhix.meter.entity;

import jakarta.persistence.*;
import lombok.*;

import java.math.BigDecimal;

@Entity
@Table(name = "plan")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Plan {

    @Id
    @Column(nullable = false, length = 50)
    private String id; // STARTER, PROFESSIONAL, ENTERPRISE

    @Column(nullable = false, length = 100)
    private String name;

    @Column(name = "monthly_price", nullable = false, precision = 10, scale = 2)
    private BigDecimal monthlyPrice;

    @Column(nullable = false, length = 10)
    @Builder.Default
    private String currency = "USD";

    @Column(name = "comment_quota", nullable = false)
    private int commentQuota;

    @Column(name = "llm_quota", nullable = false)
    private int llmQuota;

    @Column(name = "reply_quota", nullable = false)
    private int replyQuota;

    @Column(nullable = false)
    @Builder.Default
    private boolean active = true;
}
