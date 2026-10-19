package com.zhiban.ai.controller;

import com.zhiban.ai.service.AiAgentClient;
import com.zhiban.ai.vo.Result;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 健康检查 Controller
 *
 * 说明：pom 中未引入 spring-boot-starter-actuator，因此原先
 * SecurityConfig 放行的 /actuator/health 实际为 404（死规则）。
 * 这里提供一个轻量的公开健康端点，供容器编排与运维探活使用。
 *
 * @author zhiban
 */
@RestController
public class HealthController {

    private final AiAgentClient aiAgentClient;

    public HealthController(AiAgentClient aiAgentClient) {
        this.aiAgentClient = aiAgentClient;
    }

    /**
     * 健康检查（公开）
     *
     * 返回本服务状态，并附带下游 Python AI 服务的连通性。
     * 注意：AI 服务不可用不应导致本服务被判为不健康，
     * 因此 status 恒为 "ok"，AI 状态单列字段供排查。
     */
    @GetMapping("/health")
    public Result<Map<String, Object>> health() {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("status", "ok");
        body.put("service", "zhiban-ai-backend");
        body.put("aiService", aiAgentClient.isHealthy() ? "up" : "down");
        return Result.success(body);
    }
}
