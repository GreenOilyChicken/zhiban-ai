package com.zhiban.ai.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 帮助内容实体
 * 对应数据库表: help_content
 * 字段与DDL列名严格对应
 *
 * @author zhiban
 */
@Data
@TableName("help_content")
public class HelpContent {

    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 标题
     */
    @TableField("title")
    private String title;

    /**
     * 正文内容（富文本/Markdown）
     */
    @TableField("content")
    private String content;

    /**
     * 分类: 老年人/政务/旅游 等
     */
    @TableField("category")
    private String category;

    /**
     * 封面图URL
     */
    @TableField("cover_image")
    private String coverImage;

    /**
     * 视频URL
     */
    @TableField("video_url")
    private String videoUrl;

    /**
     * 标签（逗号分隔）
     */
    @TableField("tags")
    private String tags;

    /**
     * 是否发布: 0=未发布 1=已发布
     */
    @TableField("is_published")
    private Integer isPublished;

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
