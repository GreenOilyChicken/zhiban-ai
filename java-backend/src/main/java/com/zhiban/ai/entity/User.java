package com.zhiban.ai.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 用户实体
 * 对应数据库表: user
 * 字段与DDL列名严格对应
 *
 * @author zhiban
 */
@Data
@TableName("user")
public class User {

    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 用户名
     */
    @TableField("username")
    private String username;

    /**
     * 加密密码（BCrypt）
     */
    @TableField("password")
    private String password;

    /**
     * 手机号（AES-256-GCM 加密存储，附件一 §8.1）
     */
    @TableField("phone")
    private String phone;

    /**
     * 手机号盲索引（HMAC-SHA256），用于加密后的等值查询
     */
    @TableField("phone_hash")
    private String phoneHash;

    /**
     * 角色: USER / ADMIN
     */
    @TableField("role")
    private String role;

    /**
     * 头像URL
     */
    @TableField("avatar")
    private String avatar;

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

    /**
     * 逻辑删除: 0=未删除 1=已删除
     */
    @TableLogic
    @TableField("deleted")
    private Integer deleted;
}
