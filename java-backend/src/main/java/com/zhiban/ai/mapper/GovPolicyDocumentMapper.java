package com.zhiban.ai.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zhiban.ai.entity.GovPolicyDocument;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * 政策文档 Mapper
 *
 * @author zhiban
 */
@Mapper
public interface GovPolicyDocumentMapper extends BaseMapper<GovPolicyDocument> {

    /**
     * 分页查询政策文档
     *
     * @param page        分页参数
     * @param policyType  政策类型（可选）
     * @param keyword     关键词（标题/摘要模糊搜索，可选）
     * @param status      状态（可选）
     * @param region      地区（可选）
     * @return 分页结果
     */
    @Select("""
        <script>
        SELECT id, doc_number, title, issuing_authority, policy_type,
               effective_date, publish_date, region, status, summary,
               full_text, key_points, faq, vector_id, create_time, update_time
        FROM gov_policy_document
        WHERE deleted = 0
        <if test="policyType != null and policyType != ''">
            AND policy_type = #{policyType}
        </if>
        <if test="keyword != null and keyword != ''">
            AND (title LIKE CONCAT('%', #{keyword}, '%')
                 OR summary LIKE CONCAT('%', #{keyword}, '%')
                 OR issuing_authority LIKE CONCAT('%', #{keyword}, '%'))
        </if>
        <if test="status != null">
            AND status = #{status}
        </if>
        <if test="region != null and region != ''">
            AND region LIKE CONCAT('%', #{region}, '%')
        </if>
        ORDER BY publish_date DESC, create_time DESC
        </script>
        """)
    IPage<GovPolicyDocument> selectPolicyPage(Page<GovPolicyDocument> page,
                                              @Param("policyType") String policyType,
                                              @Param("keyword") String keyword,
                                              @Param("status") Integer status,
                                              @Param("region") String region);

    /**
     * 根据向量ID列表查询政策文档
     * 用于RAG向量检索后，回查原始文档内容
     *
     * @param vectorIds 向量ID列表
     * @return 政策文档列表
     */
    @Select("""
        <script>
        SELECT id, doc_number, title, issuing_authority, policy_type,
               effective_date, publish_date, region, status, summary,
               full_text, key_points, faq, vector_id, create_time, update_time
        FROM gov_policy_document
        WHERE deleted = 0 AND status = 1
        AND vector_id IN
        <foreach collection="vectorIds" item="vid" open="(" separator="," close=")">
            #{vid}
        </foreach>
        </script>
        """)
    List<GovPolicyDocument> selectByVectorIds(@Param("vectorIds") List<String> vectorIds);

    /**
     * 查询FAQ列表（所有已发布政策的FAQ）
     *
     * @param policyType 政策类型（可选筛选）
     * @return 政策文档列表（仅含id, title, faq字段）
     */
    @Select("""
        <script>
        SELECT id, title, faq, policy_type
        FROM gov_policy_document
        WHERE deleted = 0 AND status = 1
        AND faq IS NOT NULL AND faq != '[]'
        <if test="policyType != null and policyType != ''">
            AND policy_type = #{policyType}
        </if>
        ORDER BY update_time DESC
        </script>
        """)
    List<GovPolicyDocument> selectFaqList(@Param("policyType") String policyType);
}
