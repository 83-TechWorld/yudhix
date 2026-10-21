package io.yudhix.pulse.entity;

import jakarta.persistence.*;
import lombok.*;

import java.math.BigDecimal;
import java.util.UUID;

@Entity
@Table(name = "comment_aspect")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CommentAspect {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Column(name = "comment_id", nullable = false)
    private UUID commentId;

    @Column(nullable = false, length = 100)
    private String aspect;

    @Column(nullable = false, length = 20)
    private String sentiment; // POSITIVE, NEGATIVE, NEUTRAL, MIXED

    @Column(precision = 4, scale = 3)
    private BigDecimal score;

    @Column(columnDefinition = "text")
    private String evidence;
}
