package com.zhiban.ai.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 政策问答结果 DTO
 * - answer: AI生成的回答
 * - sources: 引用的政策文档来源列表
 *
 * @author zhiban
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PolicyAnswerVO {

    /**
     * AI生成的回答内容
     */
    private String answer;

    /**
     * 引用的政策文档来源列表
     */
    private List<PolicySource> sources;

    /**
     * 政策来源信息
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PolicySource {
        private Long id;
        private String title;
        private String docNumber;
        private String issuingAuthority;
        private Double score;
    }
}
