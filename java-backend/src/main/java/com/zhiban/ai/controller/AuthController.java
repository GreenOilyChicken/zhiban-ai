package com.zhiban.ai.controller;

import com.zhiban.ai.dto.LoginRequest;
import com.zhiban.ai.dto.RegisterRequest;
import com.zhiban.ai.service.AuthService;
import com.zhiban.ai.vo.LoginVO;
import com.zhiban.ai.vo.Result;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 认证 Controller
 * 提供用户登录和注册接口
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
     * 用户登录
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
}
