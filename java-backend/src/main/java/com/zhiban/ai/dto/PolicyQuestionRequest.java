package com.zhiban.ai.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 政策问答请求 DTO
 *
 * @author zhiban
 */
@Data
public class PolicyQuestionRequest {

    @NotBlank(message = "问题不能为空")
    private String question;

    /**
     * 政策类型（可选筛选）
     */
    private String policyType;
}
