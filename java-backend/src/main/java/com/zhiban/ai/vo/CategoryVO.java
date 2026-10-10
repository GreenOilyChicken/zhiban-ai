package com.zhiban.ai.vo;

import lombok.Data;

/**
 * 分类展示 VO
 *
 * @author zhiban
 */
@Data
public class CategoryVO {

    private Long id;

    private String name;

    private String type;

    private Integer sortOrder;
}
