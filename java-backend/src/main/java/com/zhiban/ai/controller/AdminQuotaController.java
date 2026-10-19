package com.zhiban.ai.controller;

import com.zhiban.ai.dto.QuotaAdjustRequest;
import com.zhiban.ai.service.HelpCenterService;
import com.zhiban.ai.vo.QuotaVO;
import com.zhiban.ai.vo.Result;
import jakarta.validation.Valid;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 管理端配额 Controller
 *
 * 附件一 §4.2 配额管理：用户配额「查看与调整」。
 * 所有接口均需要 ADMIN 角色（URL 级 + 方法级双重校验）。
 *
 * @author zhiban
 */
@RestController
@RequestMapping("/admin/quota")
@PreAuthorize("hasRole('ADMIN')")
public class AdminQuotaController {

    private final HelpCenterService helpCenterService;

    public AdminQuotaController(HelpCenterService helpCenterService) {
        this.helpCenterService = helpCenterService;
    }

    /**
     * 查询配额列表（可按用户、类型过滤）
     */
    @GetMapping
    @PreAuthorize("hasRole('ADMIN')")
    public Result<List<QuotaVO>> listQuotas(
            @RequestParam(required = false) Long userId,
            @RequestParam(required = false) String quotaType) {
        return Result.success(helpCenterService.listQuotas(userId, quotaType));
    }

    /**
     * 调整指定用户指定类型的配额
     */
    @PutMapping("/{userId}/{quotaType}")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<QuotaVO> adjustQuota(@PathVariable Long userId,
                                       @PathVariable String quotaType,
                                       @Valid @RequestBody QuotaAdjustRequest request) {
        QuotaVO vo = helpCenterService.adjustQuota(
                userId, quotaType,
                request.getTotalAmount(),
                request.getUsedAmount(),
                request.getFreeAmount());
        return Result.success("配额调整成功", vo);
    }
}
