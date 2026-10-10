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
 * @author zhiban
 */
@Validated
@RestController
@RequestMapping("/help")
public class HelpCenterController {

    private final HelpCenterService helpCenterService;

    public HelpCenterController(HelpCenterService helpCenterService) {
        this.helpCenterService = helpCenterService;
    }

    // ==================== 帮助文章 ====================

    /**
     * 分页查询已发布的帮助文章
     */
    @GetMapping("/articles")
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
     */
    @GetMapping("/article/{id}")
    public Result<HelpArticleVO> getArticle(@PathVariable Long id) {
        HelpArticleVO vo = helpCenterService.getArticleById(id);
        return Result.success(vo);
    }

    // ==================== 政策文档 ====================

    /**
     * 分页查询政策文档
     */
    @GetMapping("/gov-policy")
    public Result<IPage<GovPolicyVO>> getGovPolicies(@Valid GovPolicyQuery query) {
        IPage<GovPolicyVO> result = helpCenterService.getGovPolicies(query);
        return Result.success(result);
    }

    /**
     * 政策智能问答（需登录，会扣减配额）
     * 关键：先原子扣减配额，再执行RAG检索
     */
    @PostMapping("/gov-policy/ask")
    public Result<PolicyAnswerVO> askPolicyQuestion(@Valid @RequestBody PolicyQuestionRequest request) {
        PolicyAnswerVO result = helpCenterService.askPolicyQuestion(request);
        return Result.success(result);
    }

    // ==================== FAQ ====================

    /**
     * 获取FAQ列表
     */
    @GetMapping("/faq")
    public Result<List<GovPolicyVO>> getFaqList(
            @RequestParam(required = false) String policyType) {
        List<GovPolicyVO> result = helpCenterService.getFaqList(policyType);
        return Result.success(result);
    }

    // ==================== 配额 ====================

    /**
     * 获取用户配额（需登录）
     */
    @GetMapping("/quota")
    public Result<QuotaVO> getQuota(@RequestParam String quotaType) {
        if (quotaType == null || quotaType.isBlank()) {
            throw new BusinessException(400, "配额类型不能为空");
        }
        QuotaVO vo = helpCenterService.getUserQuota(quotaType);
        return Result.success(vo);
    }

    // ==================== 分类 ====================

    /**
     * 获取分类列表
     */
    @GetMapping("/categories")
    public Result<List<CategoryVO>> getCategories(
            @RequestParam(required = false) String type) {
        List<CategoryVO> result = helpCenterService.getCategories(type);
        return Result.success(result);
    }
}
