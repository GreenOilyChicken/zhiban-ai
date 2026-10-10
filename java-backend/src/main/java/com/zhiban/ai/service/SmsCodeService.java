package com.zhiban.ai.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.security.SecureRandom;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 短信验证码服务
 *
 * 当前实现为进程内存储（带 TTL 与尝试次数限制），
 * 单机部署满足附件一 §3.1 的手机号登录需求；
 * 多实例部署时应替换为 Redis 实现（接口保持不变）。
 *
 * @author zhiban
 */
@Service
public class SmsCodeService {

    private static final Logger log = LoggerFactory.getLogger(SmsCodeService.class);

    /** 验证码有效期：5 分钟 */
    private static final long TTL_MS = 5 * 60 * 1000L;

    /** 同一手机号发送间隔：60 秒 */
    private static final long SEND_INTERVAL_MS = 60 * 1000L;

    /** 最大校验失败次数 */
    private static final int MAX_ATTEMPTS = 5;

    private final SecureRandom random = new SecureRandom();
    private final Map<String, Entry> store = new ConcurrentHashMap<>();

    /**
     * 生成并保存验证码
     *
     * @param phone 手机号
     * @return 生成的验证码（生产环境应通过短信通道下发，不返回给调用方）
     */
    public String generate(String phone) {
        long now = System.currentTimeMillis();
        Entry existing = store.get(phone);
        if (existing != null && now - existing.createdAt < SEND_INTERVAL_MS) {
            long wait = (SEND_INTERVAL_MS - (now - existing.createdAt)) / 1000;
            throw new com.zhiban.ai.exception.BusinessException(429,
                    "验证码发送过于频繁，请 " + wait + " 秒后重试");
        }

        String code = String.format("%06d", random.nextInt(1_000_000));
        store.put(phone, new Entry(code, now, 0));
        // 开发/联调环境打印验证码，生产环境应改为短信通道下发
        log.info("短信验证码已生成: phone={}, code={}", maskPhone(phone), code);
        return code;
    }

    /**
     * 校验验证码
     *
     * @param phone 手机号
     * @param code  用户输入验证码
     * @return true=校验通过（通过后立即失效，防重放）
     */
    public boolean verify(String phone, String code) {
        if (phone == null || code == null) {
            return false;
        }
        Entry entry = store.get(phone);
        if (entry == null) {
            return false;
        }
        if (System.currentTimeMillis() - entry.createdAt > TTL_MS) {
            store.remove(phone);
            return false;
        }
        if (entry.attempts >= MAX_ATTEMPTS) {
            store.remove(phone);
            return false;
        }

        if (entry.code.equals(code.trim())) {
            store.remove(phone);   // 一次性使用
            return true;
        }

        entry.attempts++;
        if (entry.attempts >= MAX_ATTEMPTS) {
            store.remove(phone);
        }
        return false;
    }

    private String maskPhone(String phone) {
        if (phone == null || phone.length() < 11) {
            return "***";
        }
        return phone.substring(0, 3) + "****" + phone.substring(7);
    }

    /**
     * 验证码条目
     */
    private static final class Entry {
        final String code;
        final long createdAt;
        int attempts;

        Entry(String code, long createdAt, int attempts) {
            this.code = code;
            this.createdAt = createdAt;
            this.attempts = attempts;
        }
    }
}
