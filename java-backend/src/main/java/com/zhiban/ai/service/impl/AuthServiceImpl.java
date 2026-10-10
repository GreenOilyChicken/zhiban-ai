package com.zhiban.ai.service.impl;

import com.zhiban.ai.dto.LoginRequest;
import com.zhiban.ai.dto.RegisterRequest;
import com.zhiban.ai.entity.User;
import com.zhiban.ai.exception.BusinessException;
import com.zhiban.ai.mapper.UserMapper;
import com.zhiban.ai.mapper.UserQuotaMapper;
import com.zhiban.ai.security.JwtTokenProvider;
import com.zhiban.ai.service.AuthService;
import com.zhiban.ai.vo.LoginVO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 认证服务实现
 *
 * @author zhiban
 */
@Service
public class AuthServiceImpl implements AuthService {

    private static final Logger log = LoggerFactory.getLogger(AuthServiceImpl.class);

    private final UserMapper userMapper;
    private final UserQuotaMapper userQuotaMapper;
    private final JwtTokenProvider jwtTokenProvider;
    private final PasswordEncoder passwordEncoder;

    public AuthServiceImpl(UserMapper userMapper,
                           UserQuotaMapper userQuotaMapper,
                           JwtTokenProvider jwtTokenProvider,
                           PasswordEncoder passwordEncoder) {
        this.userMapper = userMapper;
        this.userQuotaMapper = userQuotaMapper;
        this.jwtTokenProvider = jwtTokenProvider;
        this.passwordEncoder = passwordEncoder;
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

        // 生成JWT Token
        String token = jwtTokenProvider.generateToken(user.getId(), user.getUsername(), user.getRole());

        log.info("用户登录成功: userId={}, username={}", user.getId(), user.getUsername());

        LoginVO vo = new LoginVO();
        vo.setToken(token);
        vo.setUserId(user.getId());
        vo.setUsername(user.getUsername());
        vo.setRole(user.getRole());
        vo.setAvatar(user.getAvatar());
        return vo;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Long register(RegisterRequest request) {
        // 检查用户名是否已存在
        int count = userMapper.countByUsername(request.getUsername());
        if (count > 0) {
            throw new BusinessException(400, "用户名已存在");
        }

        // 创建用户
        User user = new User();
        user.setUsername(request.getUsername());
        user.setPassword(passwordEncoder.encode(request.getPassword()));
        user.setPhone(request.getPhone());
        user.setRole("USER"); // 默认普通用户

        userMapper.insert(user);

        // 初始化默认配额（政策问答）
        userQuotaMapper.initQuotaIfAbsent(
                user.getId(),
                "POLICY_QA",
                100,
                10
        );

        log.info("用户注册成功: userId={}, username={}", user.getId(), user.getUsername());
        return user.getId();
    }
}
