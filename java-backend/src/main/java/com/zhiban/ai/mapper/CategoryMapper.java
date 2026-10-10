package com.zhiban.ai.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.zhiban.ai.entity.Category;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * 分类 Mapper
 *
 * @author zhiban
 */
@Mapper
public interface CategoryMapper extends BaseMapper<Category> {

    /**
     * 根据类型查询分类列表
     *
     * @param type 类型: POLICY / HELP
     * @return 分类列表
     */
    @Select("""
        SELECT id, name, type, sort_order, create_time, update_time
        FROM categories
        WHERE type = #{type}
        ORDER BY sort_order ASC
        """)
    List<Category> selectByType(@Param("type") String type);
}
