package com.zhiban.ai.controller;

import com.zhiban.ai.dto.LoginRequest;
import com.zhiban.ai.dto.PhoneLoginRequest;
import com.zhiban.ai.dto.RegisterRequest;
import com.zhiban.ai.dto.SmsCodeRequest;
import com.zhiban.ai.service.AuthService;
import com.zhiban.ai.vo.LoginVO;
import com.zhiban.ai.vo.Result;
import com.zhiban.ai.vo.TokenVO;
import com.zhiban.ai.vo.UserInfoVO;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 认证 Controller
 *
 * 附件一 §3.1：
 *   POST /api/auth/guest-login  游客登录
 *   POST /api/auth/phone-login  手机号+验证码登录
 *   POST /api/auth/refresh      Token 刷新
 *   GET  /api/auth/user-info    当前用户信息
 *
 * @author zhiban
 */
@RestController
@RequestMapping("/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    /**
     * 用户名密码登录
     */
    @PostMapping("/login")
    public Result<LoginVO> login(@Valid @RequestBody LoginRequest request) {
        LoginVO vo = authService.login(request);
        return Result.success("登录成功", vo);
    }

    /**
     * 用户注册
     */
    @PostMapping("/register")
    public Result<Long> register(@Valid @RequestBody RegisterRequest request) {
        Long userId = authService.register(request);
        return Result.success("注册成功", userId);
    }

    /**
     * 游客登录（无需凭证）
     */
    @PostMapping("/guest-login")
    public Result<LoginVO> guestLogin() {
        LoginVO vo = authService.guestLogin();
        return Result.success("登录成功", vo);
    }

    /**
     * 发送短信验证码
     */
    @PostMapping("/sms-code")
    public Result<Void> sendSmsCode(@Valid @RequestBody SmsCodeRequest request) {
        authService.sendSmsCode(request.getPhone());
        return Result.success("验证码已发送", null);
    }

    /**
     * 手机号 + 验证码登录
     */
    @PostMapping("/phone-login")
    public Result<LoginVO> phoneLogin(@Valid @RequestBody PhoneLoginRequest request) {
        LoginVO vo = authService.phoneLogin(request);
        return Result.success("登录成功", vo);
    }

    /**
     * 刷新 Token
     * 优先从 Authorization 头读取，也兼容请求体传入
     */
    @PostMapping("/refresh")
    public Result<TokenVO> refresh(
            @RequestHeader(value = "Authorization", required = false) String authorization,
            @RequestBody(required = false) java.util.Map<String, String> body) {

        String token = null;
        if (authorization != null && authorization.startsWith("Bearer ")) {
            token = authorization.substring(7);
        } else if (body != null) {
            token = body.get("token");
        }

        TokenVO vo = authService.refresh(token);
        return Result.success("刷新成功", vo);
    }

    /**
     * 获取当前登录用户信息
     */
    @GetMapping("/user-info")
    public Result<UserInfoVO> userInfo() {
        return Result.success(authService.currentUser());
    }
}
