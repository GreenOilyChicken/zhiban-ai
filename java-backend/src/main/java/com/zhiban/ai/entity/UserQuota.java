package com.zhiban.ai.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 用户配额实体
 * 对应数据库表: user_quota
 * 字段与DDL列名严格对应
 *
 * @author zhiban
 */
@Data
@TableName("user_quota")
public class UserQuota {

    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 用户ID
     */
    @TableField("user_id")
    private Long userId;

    /**
     * 配额类型: POLICY_QA / HELP_SEARCH 等
     */
    @TableField("quota_type")
    private String quotaType;

    /**
     * 总配额
     */
    @TableField("total_amount")
    private Integer totalAmount;

    /**
     * 已使用配额
     */
    @TableField("used_amount")
    private Integer usedAmount;

    /**
     * 免费配额
     */
    @TableField("free_amount")
    private Integer freeAmount;

    /**
     * 创建时间
     */
    @TableField("create_time")
    private LocalDateTime createTime;

    /**
     * 更新时间
     */
    @TableField("update_time")
    private LocalDateTime updateTime;
}
