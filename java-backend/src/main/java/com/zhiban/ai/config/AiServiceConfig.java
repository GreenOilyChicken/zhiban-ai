package com.zhiban.ai.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * Python AI 智能体服务配置
 *
 * 附件一 §2.1：AI 层为独立的 Python 智能体系统，
 * Java 后端通过 HTTP 调用其对话/语音接口。
 *
 * @author zhiban
 */
@Data
@Configuration
@ConfigurationProperties(prefix = "ai-service")
public class AiServiceConfig {

    /**
     * Python AI 服务基础地址
     */
    private String baseUrl = "http://localhost:8081";

    /**
     * 调用超时（毫秒）
     */
    private int timeoutMs = 60000;

    /**
     * 连接超时（毫秒）
     */
    private int connectTimeoutMs = 5000;

    /**
     * 智能体对话接口路径
     */
    private String chatPath = "/api/v1/chat";

    /**
     * 向量检索接口路径
     */
    private String searchPath = "/api/v1/search";

    /**
     * 知识库构建接口路径
     */
    private String buildPath = "/api/v1/build";

    /**
     * 知识库文档上传接口路径（附件一 §4.2 政策管理「文档上传」）
     */
    private String kbUploadPath = "/api/v1/kb/upload";

    /**
     * TTS 接口路径
     */
    private String ttsPath = "/api/v1/tts";

    /**
     * ASR 接口路径
     */
    private String asrPath = "/api/v1/asr";

    /**
     * 发音人列表接口路径
     */
    private String speakersPath = "/api/v1/speakers";

    /**
     * 内部调用密钥（可选）
     */
    private String apiKey;
}
