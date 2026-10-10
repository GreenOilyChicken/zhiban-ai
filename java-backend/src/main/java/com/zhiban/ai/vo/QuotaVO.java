package com.zhiban.ai.vo;

import lombok.Data;

/**
 * 用户配额展示 VO
 *
 * @author zhiban
 */
@Data
public class QuotaVO {

    private Long id;

    private Long userId;

    /**
     * 配额类型
     */
    private String quotaType;

    /**
     * 总配额
     */
    private Integer totalAmount;

    /**
     * 已使用配额
     */
    private Integer usedAmount;

    /**
     * 剩余配额
     */
    private Integer remainingAmount;

    /**
     * 免费配额
     */
    private Integer freeAmount;
}
