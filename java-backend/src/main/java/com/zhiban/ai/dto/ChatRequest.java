package com.zhiban.ai.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 发送对话消息请求 DTO
 *
 * @author zhiban
 */
@Data
public class ChatRequest {

    /**
     * 会话ID（为空则自动创建新会话）
     */
    private Long sessionId;

    /**
     * 消息内容
     */
    @NotBlank(message = "消息内容不能为空")
    @Size(max = 2000, message = "消息内容不能超过2000字")
    private String content;

    /**
     * 消息类型: text / voice
     */
    private String messageType = "text";

    /**
     * 智能体类型: elderly / govpolicy / tourism（为空则使用会话默认）
     */
    private String agentType;
}
