package com.zhiban.ai.vo;

import lombok.Data;

/**
 * 当前用户信息 VO
 * 注意：手机号必须脱敏后返回（附件一 §8.1 敏感数据保护）
 *
 * @author zhiban
 */
@Data
public class UserInfoVO {

    private Long userId;

    private String username;

    /**
     * 脱敏后的手机号，如 138****8000
     */
    private String phone;

    private String role;

    private String avatar;

    /**
     * 是否游客账号
     */
    private Boolean guest;
}
