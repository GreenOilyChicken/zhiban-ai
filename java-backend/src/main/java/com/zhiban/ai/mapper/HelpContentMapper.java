package com.zhiban.ai.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.core.metadata.Page;
import com.zhiban.ai.entity.HelpContent;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

/**
 * 帮助内容 Mapper
 *
 * @author zhiban
 */
@Mapper
public interface HelpContentMapper extends BaseMapper<HelpContent> {

    /**
     * 分页查询已发布的帮助文章
     *
     * @param page     分页参数
     * @param category 分类（可选）
     * @param keyword  关键词（标题模糊搜索，可选）
     * @return 分页结果
     */
    @Select("""
        <script>
        SELECT id, title, content, category, cover_image, video_url,
               tags, is_published, create_time, update_time
        FROM help_content
        WHERE deleted = 0 AND is_published = 1
        <if test="category != null and category != ''">
            AND category = #{category}
        </if>
        <if test="keyword != null and keyword != ''">
            AND title LIKE CONCAT('%', #{keyword}, '%')
        </if>
        ORDER BY create_time DESC
        </script>
        """)
    IPage<HelpContent> selectPublishedPage(Page<HelpContent> page,
                                          @Param("category") String category,
                                          @Param("keyword") String keyword);
}
