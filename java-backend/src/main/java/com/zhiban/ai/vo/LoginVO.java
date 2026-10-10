package com.zhiban.ai.vo;

import lombok.Data;

/**
 * 登录响应 VO
 *
 * @author zhiban
 */
@Data
public class LoginVO {

    private String token;

    private Long userId;

    private String username;

    private String role;

    private String avatar;
}
