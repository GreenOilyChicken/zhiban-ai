package com.zhiban.ai.service;

import com.zhiban.ai.dto.LoginRequest;
import com.zhiban.ai.dto.RegisterRequest;
import com.zhiban.ai.vo.LoginVO;

/**
 * 认证服务接口
 *
 * @author zhiban
 */
public interface AuthService {

    /**
     * 用户登录
     */
    LoginVO login(LoginRequest request);

    /**
     * 用户注册
     */
    Long register(RegisterRequest request);
}
