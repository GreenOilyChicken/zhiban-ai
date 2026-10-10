package com.zhiban.ai.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.Data;

/**
 * 政策文档分页查询 DTO
 * 页码和分页大小有严格校验，防止恶意超大分页请求
 *
 * @author zhiban
 */
@Data
public class GovPolicyQuery {

    @Min(value = 1, message = "页码最小为1")
    private int page = 1;

    @Min(value = 1, message = "每页条数最小为1")
    @Max(value = 100, message = "每页条数最大为100")
    private int size = 10;

    /**
     * 政策类型（可选）
     */
    private String policyType;

    /**
     * 关键词（标题/摘要模糊搜索，可选）
     */
    private String keyword;

    /**
     * 状态（可选）
     */
    private Integer status;

    /**
     * 地区（可选）
     */
    private String region;
}
