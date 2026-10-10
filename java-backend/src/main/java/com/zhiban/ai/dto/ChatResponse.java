package com.zhiban.ai.dto;

import lombok.Data;

import java.util.List;

/**
 * 对话响应 DTO
 *
 * @author zhiban
 */
@Data
public class ChatResponse {

    /**
     * 助手消息ID
     */
    private Long messageId;

    /**
     * 会话ID
     */
    private Long sessionId;

    /**
     * 回复内容
     */
    private String content;

    /**
     * 角色（固定 assistant）
     */
    private String role = "assistant";

    /**
     * 处理该消息的智能体
     */
    private String agentType;

    /**
     * 使用的模型
     */
    private String model;

    /**
     * 响应耗时（毫秒）
     */
    private Long responseTime;

    /**
     * 引用的知识来源（政策检索可追溯性）
     */
    private List<String> references;
}
