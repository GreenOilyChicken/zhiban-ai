package com.zhiban.ai.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 对话消息实体
 * 对应数据库表: chat_message
 *
 * @author zhiban
 */
@Data
@TableName("chat_message")
public class ChatMessage {

    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 会话ID
     */
    @TableField("session_id")
    private Long sessionId;

    /**
     * 用户ID
     */
    @TableField("user_id")
    private Long userId;

    /**
     * 角色: user / assistant / system
     */
    @TableField("role")
    private String role;

    /**
     * 消息内容
     */
    @TableField("content")
    private String content;

    /**
     * 消息类型: text / voice
     */
    @TableField("message_type")
    private String messageType;

    /**
     * 处理该消息的智能体
     */
    @TableField("agent_type")
    private String agentType;

    /**
     * 使用的模型
     */
    @TableField("model")
    private String model;

    /**
     * Token 消耗
     */
    @TableField("token_usage")
    private Integer tokenUsage;

    /**
     * 响应耗时（毫秒）
     */
    @TableField("response_ms")
    private Long responseMs;

    /**
     * 引用的知识来源（JSON 数组）
     */
    @TableField("references")
    private String references;

    @TableField("create_time")
    private LocalDateTime createTime;

    @TableLogic
    @TableField("deleted")
    private Integer deleted;
}
