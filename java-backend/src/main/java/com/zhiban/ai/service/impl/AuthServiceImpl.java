package com.zhiban.ai.service.impl;

import com.zhiban.ai.dto.LoginRequest;
import com.zhiban.ai.dto.PhoneLoginRequest;
import com.zhiban.ai.dto.RegisterRequest;
import com.zhiban.ai.entity.User;
import com.zhiban.ai.exception.BusinessException;
import com.zhiban.ai.mapper.UserMapper;
import com.zhiban.ai.mapper.UserQuotaMapper;
import com.zhiban.ai.security.JwtTokenProvider;
import com.zhiban.ai.security.PhoneCryptoService;
import com.zhiban.ai.security.SecurityUtils;
import com.zhiban.ai.service.AuthService;
import com.zhiban.ai.service.SmsCodeService;
import com.zhiban.ai.vo.LoginVO;
import com.zhiban.ai.vo.TokenVO;
import com.zhiban.ai.vo.UserInfoVO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

/**
 * 认证服务实现
 *
 * @author zhiban
 */
@Service
public class AuthServiceImpl implements AuthService {

    private static final Logger log = LoggerFactory.getLogger(AuthServiceImpl.class);

    /** 游客账号用户名前缀 */
    private static final String GUEST_PREFIX = "guest_";

    private final UserMapper userMapper;
    private final UserQuotaMapper userQuotaMapper;
    private final JwtTokenProvider jwtTokenProvider;
    private final PasswordEncoder passwordEncoder;
    private final SmsCodeService smsCodeService;
    private final SecurityUtils securityUtils;
    private final PhoneCryptoService phoneCryptoService;

    public AuthServiceImpl(UserMapper userMapper,
                           UserQuotaMapper userQuotaMapper,
                           JwtTokenProvider jwtTokenProvider,
                           PasswordEncoder passwordEncoder,
                           SmsCodeService smsCodeService,
                           SecurityUtils securityUtils,
                           PhoneCryptoService phoneCryptoService) {
        this.userMapper = userMapper;
        this.userQuotaMapper = userQuotaMapper;
        this.jwtTokenProvider = jwtTokenProvider;
        this.passwordEncoder = passwordEncoder;
        this.smsCodeService = smsCodeService;
        this.securityUtils = securityUtils;
        this.phoneCryptoService = phoneCryptoService;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public LoginVO login(LoginRequest request) {
        User user = userMapper.selectByUsername(request.getUsername());
        if (user == null) {
            throw new BusinessException(401, "用户名或密码错误");
        }

        if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            throw new BusinessException(401, "用户名或密码错误");
        }

        log.info("用户登录成功: userId={}, username={}", user.getId(), user.getUsername());
        return buildLoginVO(user);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Long register(RegisterRequest request) {
        int count = userMapper.countByUsername(request.getUsername());
        if (count > 0) {
            throw new BusinessException(400, "用户名已存在");
        }

        if (request.getPhone() != null && !request.getPhone().isBlank()
                && userMapper.selectByPhoneHash(phoneCryptoService.blindIndex(request.getPhone())) != null) {
            throw new BusinessException(400, "手机号已被注册");
        }

        User user = new User();
        user.setUsername(request.getUsername());
        user.setPassword(passwordEncoder.encode(request.getPassword()));
        // 附件一 §8.1：手机号加密存储 + 盲索引（用于等值查询）
        user.setPhone(phoneCryptoService.encrypt(request.getPhone()));
        user.setPhoneHash(phoneCryptoService.blindIndex(request.getPhone()));
        user.setRole("USER");

        userMapper.insert(user);
        initDefaultQuota(user.getId());

        log.info("用户注册成功: userId={}, username={}", user.getId(), user.getUsername());
        return user.getId();
    }

    // ── 游客登录 ────────────────────────────────────────

    @Override
    @Transactional(rollbackFor = Exception.class)
    public LoginVO guestLogin() {
        // 附件一 §3.1：无需凭证，自动生成游客身份并返回 JWT Token
        String username = GUEST_PREFIX + UUID.randomUUID().toString()
                .replace("-", "").substring(0, 16);

        User user = new User();
        user.setUsername(username);
        // 游客无密码，写入随机不可登录的 BCrypt 值
        user.setPassword(passwordEncoder.encode(UUID.randomUUID().toString()));
        user.setRole("USER");
        userMapper.insert(user);

        initDefaultQuota(user.getId());

        log.info("游客登录成功: userId={}", user.getId());
        return buildLoginVO(user);
    }

    // ── 手机号登录 ──────────────────────────────────────

    @Override
    public void sendSmsCode(String phone) {
        smsCodeService.generate(phone);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public LoginVO phoneLogin(PhoneLoginRequest request) {
        if (!smsCodeService.verify(request.getPhone(), request.getCode())) {
            throw new BusinessException(401, "验证码错误或已过期");
        }

        User user = userMapper.selectByPhoneHash(phoneCryptoService.blindIndex(request.getPhone()));
        if (user == null) {
            // 首次使用该手机号：自动注册
            user = new User();
            user.setUsername("u" + request.getPhone());
            user.setPassword(passwordEncoder.encode(UUID.randomUUID().toString()));
            // 附件一 §8.1：手机号加密存储 + 盲索引
            user.setPhone(phoneCryptoService.encrypt(request.getPhone()));
            user.setPhoneHash(phoneCryptoService.blindIndex(request.getPhone()));
            user.setRole("USER");
            userMapper.insert(user);
            initDefaultQuota(user.getId());
            log.info("手机号首次登录，自动注册: userId={}", user.getId());
        }

        log.info("手机号登录成功: userId={}", user.getId());
        return buildLoginVO(user);
    }

    // ── Token 刷新 ──────────────────────────────────────

    @Override
    public TokenVO refresh(String token) {
        if (token == null || token.isBlank()) {
            throw new BusinessException(401, "缺少 Token");
        }
        if (!jwtTokenProvider.validateToken(token)) {
            throw new BusinessException(401, "Token 无效或已过期，请重新登录");
        }

        Long userId = jwtTokenProvider.getUserIdFromToken(token);
        String username = jwtTokenProvider.getUsernameFromToken(token);
        String role = jwtTokenProvider.getRoleFromToken(token);

        String newToken = jwtTokenProvider.generateToken(userId, username, role);

        TokenVO vo = new TokenVO();
        vo.setToken(newToken);
        vo.setExpiresIn(jwtTokenProvider.getExpirationMs());
        log.info("Token 刷新成功: userId={}", userId);
        return vo;
    }

    // ── 当前用户信息 ────────────────────────────────────

    @Override
    public UserInfoVO currentUser() {
        Long userId = securityUtils.getCurrentUserId();
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new BusinessException(401, "用户不存在或已注销");
        }

        UserInfoVO vo = new UserInfoVO();
        vo.setUserId(user.getId());
        vo.setUsername(user.getUsername());
        // 附件一 §8.1：先解密再脱敏返回，数据库中不落明文
        vo.setPhone(maskPhone(phoneCryptoService.decrypt(user.getPhone())));
        vo.setRole(user.getRole());
        vo.setAvatar(user.getAvatar());
        vo.setGuest(user.getUsername() != null && user.getUsername().startsWith(GUEST_PREFIX));
        return vo;
    }

    // ── 内部方法 ────────────────────────────────────────

    private LoginVO buildLoginVO(User user) {
        String token = jwtTokenProvider.generateToken(
                user.getId(), user.getUsername(), user.getRole());

        LoginVO vo = new LoginVO();
        vo.setToken(token);
        vo.setUserId(user.getId());
        vo.setUsername(user.getUsername());
        vo.setRole(user.getRole());
        vo.setAvatar(user.getAvatar());
        return vo;
    }

    /**
     * 初始化默认配额
     */
    private void initDefaultQuota(Long userId) {
        userQuotaMapper.initQuotaIfAbsent(userId, "POLICY_QA", 100, 10);
    }

    /**
     * 手机号脱敏（附件一 §8.1 敏感数据保护）
     */
    private String maskPhone(String phone) {
        if (phone == null || phone.length() < 11) {
            return phone;
        }
        return phone.substring(0, 3) + "****" + phone.substring(7);
    }
}
