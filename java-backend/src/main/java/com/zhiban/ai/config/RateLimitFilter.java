package com.zhiban.ai.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * 接口频率限制过滤器
 *
 * 附件一 §3.6：接口须实现请求频率限制，防止恶意调用（429 状态码）。
 *
 * 采用固定窗口计数（按客户端 IP + 分钟），单机内存实现；
 * 多实例部署时应替换为 Redis 分布式限流。
 *
 * @author zhiban
 */
@Component
public class RateLimitFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(RateLimitFilter.class);

    /** 每窗口最大请求数 */
    @Value("${rate-limit.max-requests:300}")
    private int maxRequests;

    /** 窗口大小（毫秒），默认 1 分钟 */
    @Value("${rate-limit.window-ms:60000}")
    private long windowMs;

    /** 是否启用 */
    @Value("${rate-limit.enabled:true}")
    private boolean enabled;

    private final Map<String, Window> windows = new ConcurrentHashMap<>();

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        if (!enabled) {
            filterChain.doFilter(request, response);
            return;
        }

        String key = clientIp(request) + ":" + request.getMethod();
        long now = System.currentTimeMillis();

        Window window = windows.compute(key, (k, w) -> {
            if (w == null || now - w.start >= windowMs) {
                return new Window(now);
            }
            return w;
        });

        int count = window.count.incrementAndGet();
        if (count > maxRequests) {
            log.warn("触发限流: key={}, count={}, limit={}", key, count, maxRequests);
            response.setStatus(429);
            response.setContentType("application/json;charset=UTF-8");
            response.getWriter().write(
                    "{\"code\":429,\"message\":\"请求过于频繁，请稍后重试\",\"data\":null}");
            return;
        }

        // 清理过期窗口，防止内存无限增长
        if (windows.size() > 10_000) {
            windows.entrySet().removeIf(e -> now - e.getValue().start >= windowMs * 2);
        }

        filterChain.doFilter(request, response);
    }

    /**
     * 获取客户端真实 IP（考虑反向代理）
     */
    private String clientIp(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip != null && !ip.isBlank() && !"unknown".equalsIgnoreCase(ip)) {
            int idx = ip.indexOf(',');
            return idx > 0 ? ip.substring(0, idx).trim() : ip.trim();
        }
        ip = request.getHeader("X-Real-IP");
        if (ip != null && !ip.isBlank() && !"unknown".equalsIgnoreCase(ip)) {
            return ip.trim();
        }
        return request.getRemoteAddr();
    }

    /**
     * 固定窗口计数
     */
    private static final class Window {
        final long start;
        final AtomicInteger count = new AtomicInteger(0);

        Window(long start) {
            this.start = start;
        }
    }
}
