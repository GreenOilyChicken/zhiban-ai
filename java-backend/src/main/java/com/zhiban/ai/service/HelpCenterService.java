package com.zhiban.ai.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.zhiban.ai.dto.GovPolicyRequest;
import com.zhiban.ai.dto.GovPolicyQuery;
import com.zhiban.ai.dto.HelpArticleRequest;
import com.zhiban.ai.dto.PolicyAnswerVO;
import com.zhiban.ai.dto.PolicyQuestionRequest;
import com.zhiban.ai.vo.CategoryVO;
import com.zhiban.ai.vo.GovPolicyVO;
import com.zhiban.ai.vo.HelpArticleVO;
import com.zhiban.ai.vo.QuotaVO;

import java.util.List;

/**
 * 帮助中心服务接口
 * 涵盖帮助文章CRUD、政策文档CRUD、政策问答、配额管理、分类查询
 *
 * @author zhiban
 */
public interface HelpCenterService {

    // ==================== 帮助文章 ====================

    /**
     * 分页查询已发布的帮助文章
     */
    IPage<HelpArticleVO> getPublishedArticles(int page, int size, String category, String keyword);

    /**
     * 根据ID获取帮助文章详情
     */
    HelpArticleVO getArticleById(Long id);

    /**
     * 创建帮助文章（管理员）
     */
    Long createArticle(HelpArticleRequest request);

    /**
     * 更新帮助文章（管理员）
     */
    void updateArticle(Long id, HelpArticleRequest request);

    /**
     * 删除帮助文章（管理员，逻辑删除）
     */
    void deleteArticle(Long id);

    // ==================== 政策文档 ====================

    /**
     * 分页查询政策文档
     */
    IPage<GovPolicyVO> getGovPolicies(GovPolicyQuery query);

    /**
     * 根据ID获取政策文档详情
     */
    GovPolicyVO getGovPolicyById(Long id);

    /**
     * 创建政策文档（管理员）
     */
    Long createGovPolicy(GovPolicyRequest request);

    /**
     * 更新政策文档（管理员）
     */
    void updateGovPolicy(Long id, GovPolicyRequest request);

    /**
     * 删除政策文档（管理员，逻辑删除）
     */
    void deleteGovPolicy(Long id);

    // ==================== 政策问答 ====================

    /**
     * 政策智能问答（RAG）
     * 关键流程：先原子扣减配额，再执行RAG检索生成回答
     */
    PolicyAnswerVO askPolicyQuestion(PolicyQuestionRequest request);

    // ==================== FAQ ====================

    /**
     * 获取FAQ列表
     */
    List<GovPolicyVO> getFaqList(String policyType);

    // ==================== 配额管理 ====================

    /**
     * 获取用户配额
     */
    QuotaVO getUserQuota(String quotaType);

    /**
     * 原子扣减配额（内部调用）
     */
    boolean deductQuota(Long userId, String quotaType);

    // ==================== 分类 ====================

    /**
     * 获取分类列表
     */
    List<CategoryVO> getCategories(String type);
}
