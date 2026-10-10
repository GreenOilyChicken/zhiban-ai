package com.zhiban.ai.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 帮助文章创建/更新请求 DTO
 *
 * @author zhiban
 */
@Data
public class HelpArticleRequest {

    @NotBlank(message = "标题不能为空")
    @Size(max = 256, message = "标题长度不能超过256")
    private String title;

    @NotBlank(message = "内容不能为空")
    private String content;

    @NotBlank(message = "分类不能为空")
    @Size(max = 64, message = "分类长度不能超过64")
    private String category;

    @Size(max = 512, message = "封面图URL长度不能超过512")
    private String coverImage;

    @Size(max = 512, message = "视频URL长度不能超过512")
    private String videoUrl;

    @Size(max = 512, message = "标签长度不能超过512")
    private String tags;

    /**
     * 是否发布: 0=未发布 1=已发布
     */
    private Integer isPublished = 0;
}
