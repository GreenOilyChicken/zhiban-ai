package com.zhiban.ai.service;

import com.zhiban.ai.dto.LoginRequest;
import com.zhiban.ai.dto.PhoneLoginRequest;
import com.zhiban.ai.dto.RegisterRequest;
import com.zhiban.ai.vo.LoginVO;
import com.zhiban.ai.vo.TokenVO;
import com.zhiban.ai.vo.UserInfoVO;

/**
 * 认证服务接口
 * 附件一 §3.1：游客登录、手机号登录、Token 刷新、用户信息。
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

    /**
     * 游客登录：无需凭证，自动创建游客身份并返回 JWT
     */
    LoginVO guestLogin();

    /**
     * 发送短信验证码
     *
     * @param phone 手机号
     */
    void sendSmsCode(String phone);

    /**
     * 手机号 + 验证码登录
     */
    LoginVO phoneLogin(PhoneLoginRequest request);

    /**
     * 刷新 Token（旧 Token 有效期内换取新 Token）
     *
     * @param token 原 Token
     * @return 新 Token 信息
     */
    TokenVO refresh(String token);

    /**
     * 获取当前登录用户信息
     */
    UserInfoVO currentUser();
}
