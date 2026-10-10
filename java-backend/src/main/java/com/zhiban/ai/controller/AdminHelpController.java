package com.zhiban.ai.controller;

import com.zhiban.ai.dto.GovPolicyRequest;
import com.zhiban.ai.dto.HelpArticleRequest;
import com.zhiban.ai.service.HelpCenterService;
import com.zhiban.ai.vo.Result;
import jakarta.validation.Valid;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 管理端帮助中心 Controller
 * 所有接口均需要 ADMIN 角色权限，通过 @PreAuthorize 注解进行方法级权限控制
 *
 * @author zhiban
 */
@RestController
@RequestMapping("/admin/help")
@PreAuthorize("hasRole('ADMIN')")
public class AdminHelpController {

    private final HelpCenterService helpCenterService;

    public AdminHelpController(HelpCenterService helpCenterService) {
        this.helpCenterService = helpCenterService;
    }

    // ==================== 帮助文章管理 ====================

    /**
     * 创建帮助文章
     */
    @PostMapping("/article")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Long> createArticle(@Valid @RequestBody HelpArticleRequest request) {
        Long id = helpCenterService.createArticle(request);
        return Result.success("创建成功", id);
    }

    /**
     * 更新帮助文章
     */
    @PutMapping("/article/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Void> updateArticle(@PathVariable Long id,
                                      @Valid @RequestBody HelpArticleRequest request) {
        helpCenterService.updateArticle(id, request);
        return Result.success();
    }

    /**
     * 删除帮助文章（逻辑删除）
     */
    @DeleteMapping("/article/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Void> deleteArticle(@PathVariable Long id) {
        helpCenterService.deleteArticle(id);
        return Result.success();
    }

    // ==================== 政策文档管理 ====================

    /**
     * 创建政策文档
     */
    @PostMapping("/gov-policy")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Long> createGovPolicy(@Valid @RequestBody GovPolicyRequest request) {
        Long id = helpCenterService.createGovPolicy(request);
        return Result.success("创建成功", id);
    }

    /**
     * 更新政策文档
     */
    @PutMapping("/gov-policy/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Void> updateGovPolicy(@PathVariable Long id,
                                        @Valid @RequestBody GovPolicyRequest request) {
        helpCenterService.updateGovPolicy(id, request);
        return Result.success();
    }

    /**
     * 删除政策文档（逻辑删除）
     */
    @DeleteMapping("/gov-policy/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Void> deleteGovPolicy(@PathVariable Long id) {
        helpCenterService.deleteGovPolicy(id);
        return Result.success();
    }
}
