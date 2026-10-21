package io.yudhix.resolve.dto;

import io.yudhix.resolve.entity.ApprovalStep;
import io.yudhix.resolve.entity.Reply;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReplyResponse {
    private Reply reply;
    private List<ApprovalStep> history;
}
