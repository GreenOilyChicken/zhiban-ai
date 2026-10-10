package com.zhiban.ai.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 政策文档实体
 * 对应数据库表: gov_policy_document
 * 字段与DDL列名严格对应，驼峰映射通过 @TableField 显式指定
 *
 * @author zhiban
 */
@Data
@TableName("gov_policy_document")
public class GovPolicyDocument {

    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 文号
     */
    @TableField("doc_number")
    private String docNumber;

    /**
     * 标题
     */
    @TableField("title")
    private String title;

    /**
     * 发文机关
     */
    @TableField("issuing_authority")
    private String issuingAuthority;

    /**
     * 政策类型: 养老/旅游/政务 等
     */
    @TableField("policy_type")
    private String policyType;

    /**
     * 生效日期
     */
    @TableField("effective_date")
    private LocalDate effectiveDate;

    /**
     * 发布日期
     */
    @TableField("publish_date")
    private LocalDate publishDate;

    /**
     * 适用地区
     */
    @TableField("region")
    private String region;

    /**
     * 状态: 0=失效 1=有效
     */
    @TableField("status")
    private Integer status;

    /**
     * 摘要
     */
    @TableField("summary")
    private String summary;

    /**
     * 全文内容
     */
    @TableField("full_text")
    private String fullText;

    /**
     * 要点列表（JSON数组字符串）
     */
    @TableField("key_points")
    private String keyPoints;

    /**
     * 常见问题（JSON数组字符串）
     */
    @TableField("faq")
    private String faq;

    /**
     * 向量库ID
     */
    @TableField("vector_id")
    private String vectorId;

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
