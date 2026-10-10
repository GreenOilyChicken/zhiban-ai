package com.zhiban.ai.vo;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 帮助文章展示 VO
 * 返回给前端的结构化帮助文章数据
 *
 * @author zhiban
 */
@Data
public class HelpArticleVO {

    private Long id;

    private String title;

    private String content;

    private String category;

    private String coverImage;

    private String videoUrl;

    /**
     * 标签列表（解析后的数组）
     */
    private List<String> tags;

    /**
     * 是否发布: 0=未发布 1=已发布
     */
    private Integer isPublished;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
