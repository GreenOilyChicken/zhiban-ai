package com.zhiban.ai.vo;

import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 政策文档展示 VO
 * 返回给前端的结构化政策文档数据
 *
 * @author zhiban
 */
@Data
public class GovPolicyVO {

    private Long id;

    private String docNumber;

    private String title;

    private String issuingAuthority;

    private String policyType;

    private LocalDate effectiveDate;

    private LocalDate publishDate;

    private String region;

    /**
     * 状态: 0=失效 1=有效
     */
    private Integer status;

    private String summary;

    private String fullText;

    /**
     * 要点列表（解析后的JSON数组）
     */
    private List<String> keyPoints;

    /**
     * 常见问题（解析后的JSON数组）
     */
    private List<FaqItem> faq;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;

    /**
     * FAQ项
     */
    @Data
    public static class FaqItem {
        private String question;
        private String answer;
    }
}
