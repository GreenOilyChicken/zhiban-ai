package com.zhiban.ai.dto;

import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 创建会话请求 DTO
 *
 * @author zhiban
 */
@Data
public class SessionCreateRequest {

    /**
     * 会话标题（可空，默认「新对话」）
     */
    @Size(max = 120, message = "标题不能超过120字")
    private String title;

    /**
     * 智能体类型: elderly / govpolicy / tourism
     */
    private String agentType;
}
