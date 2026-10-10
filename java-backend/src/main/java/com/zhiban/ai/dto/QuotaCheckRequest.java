package com.zhiban.ai.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 配额检查请求 DTO
 *
 * @author zhiban
 */
@Data
public class QuotaCheckRequest {

    /**
     * 配额类型: POLICY_QA / HELP_SEARCH 等
     */
    @NotBlank(message = "配额类型不能为空")
    private String quotaType;
}
