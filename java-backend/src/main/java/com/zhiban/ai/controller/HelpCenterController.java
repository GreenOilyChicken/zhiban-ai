package com.zhiban.ai.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.zhiban.ai.dto.GovPolicyQuery;
import com.zhiban.ai.dto.PolicyAnswerVO;
import com.zhiban.ai.dto.PolicyQuestionRequest;
import com.zhiban.ai.exception.BusinessException;
import com.zhiban.ai.service.HelpCenterService;
import com.zhiban.ai.vo.CategoryVO;
import com.zhiban.ai.vo.GovPolicyVO;
import com.zhiban.ai.vo.HelpArticleVO;
import com.zhiban.ai.vo.QuotaVO;
import com.zhiban.ai.vo.Result;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 用户端帮助中心 Controller
 * 提供政策查询、问答、帮助文章、FAQ、配额、分类等公开接口
 *
 * <p>路径说明：附件一 §3.5 规定的是 <code>/api/articles</code>、
 * <code>/api/policies</code>、<code>/api/quota</code>；而前端与小程序
 * 历史版本使用 <code>/api/help/*</code>。为保证「按需求文档验收」与
 * 「既有客户端不破坏」同时成立，每个接口同时注册两套路径。
 * 因此本类不再使用类级 {@code @RequestMapping} 前缀，改为方法级全路径。
 *
 * @author zhiban
 */
@Validated
@RestController
public class HelpCenterController {

    private final HelpCenterService helpCenterService;

    public HelpCenterController(HelpCenterService helpCenterService) {
        this.helpCenterService = helpCenterService;
    }

    // ==================== 帮助文章 ====================

    /**
     * 分页查询已发布的帮助文章
     *
     * 附件一 §3.5：GET /api/articles
     */
    @GetMapping({"/articles", "/help/articles"})
    public Result<IPage<HelpArticleVO>> getArticles(
            @RequestParam(defaultValue = "1") @Min(1) int page,
            @RequestParam(defaultValue = "10") @Min(1) @Max(100) int size,
            @RequestParam(required = false) String category,
            @RequestParam(required = false) String keyword) {

        IPage<HelpArticleVO> result = helpCenterService.getPublishedArticles(page, size, category, keyword);
        return Result.success(result);
    }

    /**
     * 获取帮助文章详情
     *
     * 附件一 §3.5：GET /api/articles/{id}
     */
    @GetMapping({"/articles/{id}", "/help/article/{id}"})
    public Result<HelpArticleVO> getArticle(@PathVariable Long id) {
        HelpArticleVO vo = helpCenterService.getArticleById(id);
        return Result.success(vo);
    }

    /**
     * 获取相关推荐文章
     *
     * 附件一 §4.1：文章详情页「相关推荐」
     * 优先返回同分类文章，不足时按最新文章补齐。
     */
    @GetMapping({"/articles/{id}/related", "/help/article/{id}/related"})
    public Result<List<HelpArticleVO>> getRelatedArticles(
            @PathVariable Long id,
            @RequestParam(defaultValue = "5") @Min(1) @Max(20) int limit) {
        return Result.success(helpCenterService.getRelatedArticles(id, limit));
    }

    // ==================== 政策文档 ====================

    /**
     * 分页查询政策文档
     *
     * 附件一 §3.5：GET /api/policies
     */
    @GetMapping({"/policies", "/help/gov-policy"})
    public Result<IPage<GovPolicyVO>> getGovPolicies(@Valid GovPolicyQuery query) {
        IPage<GovPolicyVO> result = helpCenterService.getGovPolicies(query);
        return Result.success(result);
    }

    /**
     * 政策智能问答（需登录，会扣减配额）
     * 关键：先原子扣减配额，再执行RAG检索
     */
    @PostMapping({"/policies/ask", "/help/gov-policy/ask"})
    public Result<PolicyAnswerVO> askPolicyQuestion(@Valid @RequestBody PolicyQuestionRequest request) {
        PolicyAnswerVO result = helpCenterService.askPolicyQuestion(request);
        return Result.success(result);
    }

    /**
     * 获取单条政策完整内容
     * 附件一 §3.5：政策详情 GET /api/policies/{id}
     */
    @GetMapping({"/policies/{id}", "/help/gov-policy/{id}"})
    public Result<GovPolicyVO> getGovPolicy(@PathVariable Long id) {
        return Result.success(helpCenterService.getGovPolicyById(id));
    }

    // ==================== FAQ ====================

    /**
     * 获取FAQ列表
     */
    @GetMapping("/help/faq")
    public Result<List<GovPolicyVO>> getFaqList(
            @RequestParam(required = false) String policyType) {
        List<GovPolicyVO> result = helpCenterService.getFaqList(policyType);
        return Result.success(result);
    }

    // ==================== 配额 ====================

    /**
     * 获取用户配额（需登录）
     *
     * 附件一 §3.5：GET /api/quota
     * quotaType 可选，默认 POLICY_QA。
     */
    @GetMapping({"/quota", "/help/quota"})
    public Result<QuotaVO> getQuota(
            @RequestParam(required = false) String quotaType) {
        String type = (quotaType == null || quotaType.isBlank()) ? "POLICY_QA" : quotaType;
        QuotaVO vo = helpCenterService.getUserQuota(type);
        return Result.success(vo);
    }

    // ==================== 分类 ====================

    /**
     * 获取分类列表
     */
    @GetMapping("/help/categories")
    public Result<List<CategoryVO>> getCategories(
            @RequestParam(required = false) String type) {
        List<CategoryVO> result = helpCenterService.getCategories(type);
        return Result.success(result);
    }
}
