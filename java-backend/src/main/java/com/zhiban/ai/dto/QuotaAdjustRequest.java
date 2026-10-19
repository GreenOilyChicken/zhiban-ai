package com.zhiban.ai.dto;

import jakarta.validation.constraints.Min;
import lombok.Data;

/**
 * 配额调整请求 DTO（管理端）
 *
 * 附件一 §4.2 配额管理：用户配额查看与调整。
 * 三个字段均为可选，为 null 表示保持原值不变。
 *
 * @author zhiban
 */
@Data
public class QuotaAdjustRequest {

    /**
     * 新的总配额（null=不修改）
     */
    @Min(value = 0, message = "总配额不能为负数")
    private Integer totalAmount;

    /**
     * 新的已用配额（null=不修改）
     */
    @Min(value = 0, message = "已用配额不能为负数")
    private Integer usedAmount;

    /**
     * 新的免费配额（null=不修改）
     */
    @Min(value = 0, message = "免费配额不能为负数")
    private Integer freeAmount;
}
