package com.zhiban.ai.security;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * 手机号加密配置（附件一 §8.1：敏感数据须加密存储）
 *
 * <p>密钥必须通过环境变量注入，不提供硬编码默认值：
 * <pre>
 *   PHONE_ENC_KEY   —— AES 加密密钥（32 字节 Base64，或任意口令经 SHA-256 派生）
 *   PHONE_INDEX_KEY —— 盲索引 HMAC 密钥（可选，缺省回退到加密密钥）
 * </pre>
 *
 * @author zhiban
 */
@Data
@Configuration
@ConfigurationProperties(prefix = "security.phone")
public class PhoneSecurityProperties {

    /**
     * 手机号 AES 加密密钥
     */
    private String encryptionKey;

    /**
     * 手机号盲索引 HMAC 密钥
     */
    private String blindIndexKey;
}
