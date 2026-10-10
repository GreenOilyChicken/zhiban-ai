package com.zhiban.ai.config;

import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;

/**
 * RestTemplate 配置
 * 用于调用 Python AI 智能体服务。
 *
 * @author zhiban
 */
@Configuration
public class RestTemplateConfig {

    private final AiServiceConfig aiServiceConfig;

    public RestTemplateConfig(AiServiceConfig aiServiceConfig) {
        this.aiServiceConfig = aiServiceConfig;
    }

    /**
     * 调用 Python AI 服务的 RestTemplate（较长超时，大模型生成较慢）
     */
    @Bean("aiRestTemplate")
    public RestTemplate aiRestTemplate(RestTemplateBuilder builder) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofMillis(aiServiceConfig.getConnectTimeoutMs()));
        factory.setReadTimeout(Duration.ofMillis(aiServiceConfig.getTimeoutMs()));
        return builder.requestFactory(() -> factory).build();
    }
}
