package com.zhiban.ai.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 智能体人设实体
 * 对应数据库表: agent_persona
 *
 * @author zhiban
 */
@Data
@TableName("agent_persona")
public class AgentPersona {

    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 智能体标识: elderly / govpolicy / tourism
     */
    @TableField("agent_type")
    private String agentType;

    /**
     * 智能体名称
     */
    @TableField("name")
    private String name;

    /**
     * 人设描述
     */
    @TableField("personality")
    private String personality;

    /**
     * 欢迎语
     */
    @TableField("greeting")
    private String greeting;

    /**
     * 能力说明
     */
    @TableField("description")
    private String description;

    /**
     * 是否启用: 0=否 1=是
     */
    @TableField("enabled")
    private Integer enabled;

    /**
     * 排序
     */
    @TableField("sort_order")
    private Integer sortOrder;

    @TableField("create_time")
    private LocalDateTime createTime;

    @TableField("update_time")
    private LocalDateTime updateTime;
}
