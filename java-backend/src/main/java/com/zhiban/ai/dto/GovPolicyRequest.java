package com.zhiban.ai.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.time.LocalDate;

/**
 * 政策文档创建/更新请求 DTO
 *
 * @author zhiban
 */
@Data
public class GovPolicyRequest {

    @Size(max = 128, message = "文号长度不能超过128")
    private String docNumber;

    @NotBlank(message = "标题不能为空")
    @Size(max = 512, message = "标题长度不能超过512")
    private String title;

    @Size(max = 256, message = "发文机关长度不能超过256")
    private String issuingAuthority;

    @NotBlank(message = "政策类型不能为空")
    @Size(max = 64, message = "政策类型长度不能超过64")
    private String policyType;

    private LocalDate effectiveDate;

    private LocalDate publishDate;

    @Size(max = 128, message = "地区长度不能超过128")
    private String region;

    /**
     * 状态: 0=失效 1=有效
     */
    private Integer status;

    private String summary;

    private String fullText;

    /**
     * 要点列表（JSON字符串格式）
     */
    private String keyPoints;

    /**
     * 常见问题（JSON字符串格式）
     */
    private String faq;

    /**
     * 向量库ID
     */
    private String vectorId;
}
