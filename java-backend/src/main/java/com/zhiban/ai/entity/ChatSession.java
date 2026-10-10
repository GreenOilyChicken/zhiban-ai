package com.zhiban.ai.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 对话会话实体
 * 对应数据库表: chat_session
 *
 * @author zhiban
 */
@Data
@TableName("chat_session")
public class ChatSession {

    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 用户ID
     */
    @TableField("user_id")
    private Long userId;

    /**
     * 会话标题
     */
    @TableField("title")
    private String title;

    /**
     * 智能体类型: elderly / govpolicy / tourism
     */
    @TableField("agent_type")
    private String agentType;

    /**
     * 最后一条消息摘要
     */
    @TableField("last_message")
    private String lastMessage;

    /**
     * 消息数量
     */
    @TableField("message_count")
    private Integer messageCount;

    @TableField("create_time")
    private LocalDateTime createTime;

    @TableField("update_time")
    private LocalDateTime updateTime;

    @TableLogic
    @TableField("deleted")
    private Integer deleted;
}
