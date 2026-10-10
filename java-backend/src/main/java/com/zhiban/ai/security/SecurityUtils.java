package com.zhiban.ai.security;

import com.zhiban.ai.exception.BusinessException;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;

/**
 * 安全上下文工具
 * 从 SecurityContext 中获取当前认证用户ID
 *
 * @author zhiban
 */
@Component
public class SecurityUtils {

    /**
     * 获取当前登录用户ID
     *
     * @return 用户ID
     * @throws BusinessException 如果未登录
     */
    public Long getCurrentUserId() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !authentication.isAuthenticated()
                || authentication.getPrincipal() == null
                || "anonymousUser".equals(authentication.getPrincipal())) {
            throw new BusinessException(401, "未登录或登录已过期");
        }
        Object principal = authentication.getPrincipal();
        if (principal instanceof Long userId) {
            return userId;
        }
        throw new BusinessException(401, "无法获取用户信息");
    }

    /**
     * 判断当前用户是否已认证
     */
    public boolean isAuthenticated() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        return authentication != null
                && authentication.isAuthenticated()
                && !"anonymousUser".equals(authentication.getPrincipal());
    }
}
