package com.zhiban.ai.security;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import javax.crypto.Cipher;
import javax.crypto.Mac;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;

/**
 * 手机号加密服务（附件一 §8.1：敏感数据须加密存储）
 *
 * <p>设计：
 * <ul>
 *   <li><b>机密性</b>：AES-256-GCM 加密，每条记录使用独立随机 IV，
 *       密文格式为 <code>enc1:base64(iv || ciphertext || tag)</code>。</li>
 *   <li><b>可检索性</b>：GCM 非确定性，无法直接按密文等值查询，
 *       因此额外维护 HMAC-SHA256「盲索引」(phone_hash) 用于等值查找。</li>
 *   <li><b>兼容性</b>：无 <code>enc1:</code> 前缀的历史明文数据按原样返回，
 *       便于灰度迁移；未配置密钥时退化为明文并打印告警。</li>
 * </ul>
 *
 * @author zhiban
 */
@Component
public class PhoneCryptoService {

    private static final Logger log = LoggerFactory.getLogger(PhoneCryptoService.class);

    /** 密文版本前缀，用于区分历史明文数据 */
    private static final String PREFIX = "enc1:";

    private static final String AES_GCM = "AES/GCM/NoPadding";
    private static final String HMAC_SHA256 = "HmacSHA256";
    private static final int GCM_IV_BYTES = 12;
    private static final int GCM_TAG_BITS = 128;

    private final SecureRandom secureRandom = new SecureRandom();

    private final PhoneSecurityProperties properties;

    /** 加密密钥（null 表示未配置，退化为明文存储） */
    private final SecretKeySpec encryptionKey;

    /** 盲索引密钥（null 表示未配置，退化为明文查找） */
    private final SecretKeySpec blindIndexKey;

    public PhoneCryptoService(PhoneSecurityProperties properties) {
        this.properties = properties;
        this.encryptionKey = deriveKey(properties.getEncryptionKey());
        this.blindIndexKey = deriveKey(properties.getBlindIndexKey());

        if (encryptionKey == null) {
            log.warn("未配置 PHONE_ENC_KEY，手机号将以明文存储。" +
                    "生产环境请务必注入该环境变量以满足附件一 §8.1 敏感数据加密要求。");
        }
        if (blindIndexKey == null && encryptionKey != null) {
            log.warn("未配置 PHONE_INDEX_KEY，手机号盲索引将回退使用加密密钥派生。");
        }
    }

    /**
     * 加密手机号
     *
     * @param plainPhone 明文手机号，可为 null/空
     * @return 密文（含 enc1: 前缀）；未配置密钥或入参为空时原样返回
     */
    public String encrypt(String plainPhone) {
        if (plainPhone == null || plainPhone.isBlank()) {
            return plainPhone;
        }
        if (encryptionKey == null) {
            return plainPhone;
        }
        try {
            byte[] iv = new byte[GCM_IV_BYTES];
            secureRandom.nextBytes(iv);

            Cipher cipher = Cipher.getInstance(AES_GCM);
            cipher.init(Cipher.ENCRYPT_MODE, encryptionKey, new GCMParameterSpec(GCM_TAG_BITS, iv));
            byte[] cipherText = cipher.doFinal(plainPhone.getBytes(StandardCharsets.UTF_8));

            byte[] combined = new byte[iv.length + cipherText.length];
            System.arraycopy(iv, 0, combined, 0, iv.length);
            System.arraycopy(cipherText, 0, combined, iv.length, cipherText.length);

            return PREFIX + Base64.getEncoder().encodeToString(combined);
        } catch (Exception e) {
            // 加密失败不应导致业务不可用，但必须显式告警
            log.error("手机号加密失败，已降级为明文存储: {}", e.getMessage());
            return plainPhone;
        }
    }

    /**
     * 解密手机号
     *
     * @param stored 存储值（密文或历史明文）
     * @return 明文手机号；历史明文原样返回
     */
    public String decrypt(String stored) {
        if (stored == null || stored.isBlank()) {
            return stored;
        }
        if (!stored.startsWith(PREFIX)) {
            // 历史明文数据，保持兼容
            return stored;
        }
        if (encryptionKey == null) {
            log.error("数据为密文但未配置 PHONE_ENC_KEY，无法解密");
            return null;
        }
        try {
            byte[] combined = Base64.getDecoder().decode(stored.substring(PREFIX.length()));
            if (combined.length <= GCM_IV_BYTES) {
                log.error("手机号密文长度非法");
                return null;
            }
            byte[] iv = new byte[GCM_IV_BYTES];
            System.arraycopy(combined, 0, iv, 0, GCM_IV_BYTES);
            byte[] cipherText = new byte[combined.length - GCM_IV_BYTES];
            System.arraycopy(combined, GCM_IV_BYTES, cipherText, 0, cipherText.length);

            Cipher cipher = Cipher.getInstance(AES_GCM);
            cipher.init(Cipher.DECRYPT_MODE, encryptionKey, new GCMParameterSpec(GCM_TAG_BITS, iv));
            return new String(cipher.doFinal(cipherText), StandardCharsets.UTF_8);
        } catch (Exception e) {
            log.error("手机号解密失败: {}", e.getMessage());
            return null;
        }
    }

    /**
     * 计算手机号盲索引，用于等值查询
     *
     * @param plainPhone 明文手机号
     * @return HMAC-SHA256 十六进制串；未配置密钥或入参为空时原样返回明文
     */
    public String blindIndex(String plainPhone) {
        if (plainPhone == null || plainPhone.isBlank()) {
            return plainPhone;
        }
        SecretKeySpec key = blindIndexKey != null ? blindIndexKey : encryptionKey;
        if (key == null) {
            // 未配置密钥：退化为明文，保证历史行为可用
            return plainPhone;
        }
        try {
            Mac mac = Mac.getInstance(HMAC_SHA256);
            mac.init(key);
            byte[] digest = mac.doFinal(plainPhone.getBytes(StandardCharsets.UTF_8));
            return toHex(digest);
        } catch (Exception e) {
            log.error("手机号盲索引计算失败: {}", e.getMessage());
            return plainPhone;
        }
    }

    /**
     * 从存储值还原明文手机号（供返回脱敏前使用）
     */
    public String resolvePlain(String stored) {
        return decrypt(stored);
    }

    /**
     * 将配置的任意长度密钥材料派生为 256 位 AES 密钥
     *
     * @return 密钥；配置为空时返回 null
     */
    private SecretKeySpec deriveKey(String raw) {
        if (raw == null || raw.isBlank()) {
            return null;
        }
        try {
            // 允许直接传入 32 字节 Base64 密钥，也允许传入任意口令
            byte[] material;
            try {
                byte[] decoded = Base64.getDecoder().decode(raw);
                material = decoded.length == 32 ? decoded : null;
            } catch (IllegalArgumentException ignored) {
                material = null;
            }
            if (material == null) {
                material = MessageDigest.getInstance("SHA-256")
                        .digest(raw.getBytes(StandardCharsets.UTF_8));
            }
            return new SecretKeySpec(material, "AES");
        } catch (Exception e) {
            log.error("派生手机号加密密钥失败: {}", e.getMessage());
            return null;
        }
    }

    private String toHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) {
            sb.append(Character.forDigit((b >> 4) & 0xF, 16));
            sb.append(Character.forDigit(b & 0xF, 16));
        }
        return sb.toString();
    }

    /**
     * 是否已启用加密
     */
    public boolean isEnabled() {
        return encryptionKey != null;
    }

    /**
     * 供健康检查/诊断使用的配置摘要（不泄露密钥）
     */
    public String describe() {
        return isEnabled() ? "enabled" : "disabled(plaintext)";
    }
}
