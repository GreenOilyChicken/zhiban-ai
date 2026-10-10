package com.zhiban.ai.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * RAG（检索增强生成）配置
 * - top-k: 向量检索返回的结果数量
 * - score-threshold: 相似度分数阈值，低于此分数的结果被过滤
 * - vector-api-url: 向量检索服务的API地址
 * - api-key: 向量检索服务的API密钥
 *
 * @author zhiban
 */
@Data
@Configuration
@ConfigurationProperties(prefix = "rag")
public class RagConfig {

    /**
     * 向量检索返回Top-K结果
     */
    private int topK = 5;

    /**
     * 相似度分数阈值（0-1），低于此分数的结果被过滤
     */
    private double scoreThreshold = 0.75;

    /**
     * 向量检索服务API地址
     */
    private String vectorApiUrl = "http://localhost:8081/api/v1/search";

    /**
     * 向量检索服务API密钥
     */
    private String apiKey;
}
