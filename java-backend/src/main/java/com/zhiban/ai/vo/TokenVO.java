package com.zhiban.ai.vo;

import lombok.Data;

/**
 * Token 刷新响应 VO
 *
 * @author zhiban
 */
@Data
public class TokenVO {

    private String token;

    /**
     * 有效期（毫秒）
     */
    private Long expiresIn;
}
