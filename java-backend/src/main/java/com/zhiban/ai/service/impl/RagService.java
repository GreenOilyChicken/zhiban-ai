package com.zhiban.ai.service.impl;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.zhiban.ai.config.RagConfig;
import com.zhiban.ai.dto.PolicyAnswerVO;
import com.zhiban.ai.entity.GovPolicyDocument;
import com.zhiban.ai.exception.BusinessException;
import com.zhiban.ai.mapper.GovPolicyDocumentMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * RAG（检索增强生成）服务
 * 负责向量检索和答案生成
 *
 * @author zhiban
 */
@Service
public class RagService {

    private static final Logger log = LoggerFactory.getLogger(RagService.class);

    private final RagConfig ragConfig;
    private final GovPolicyDocumentMapper govPolicyMapper;
    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    public RagService(RagConfig ragConfig,
                      GovPolicyDocumentMapper govPolicyMapper,
                      ObjectMapper objectMapper) {
        this.ragConfig = ragConfig;
        this.govPolicyMapper = govPolicyMapper;
        this.objectMapper = objectMapper;
        this.restTemplate = new RestTemplate();
    }

    /**
     * 执行 RAG 检索与回答生成
     * 1. 调用向量检索服务获取相关文档ID
     * 2. 回查MySQL获取原始文档内容
     * 3. 按相似度分数阈值过滤
     * 4. 拼接上下文生成回答
     *
     * @param question   用户问题
     * @param policyType 政策类型（可选筛选）
     * @return 问答结果（回答+来源）
     */
    public PolicyAnswerVO searchAndAnswer(String question, String policyType) {
        log.info("RAG检索开始: question={}, policyType={}", question, policyType);

        // 1. 调用向量检索服务获取相关文档
        List<VectorSearchResult> vectorResults = searchVector(question, policyType);

        if (vectorResults.isEmpty()) {
            log.info("向量检索无结果，尝试关键词兜底检索");
            // 向量检索无结果时，使用关键词兜底
            return keywordFallbackAnswer(question, policyType);
        }

        // 2. 回查MySQL获取原始文档
        List<String> vectorIds = vectorResults.stream()
                .map(VectorSearchResult::getVectorId)
                .collect(Collectors.toList());

        List<GovPolicyDocument> documents = govPolicyMapper.selectByVectorIds(vectorIds);

        if (documents.isEmpty()) {
            log.warn("向量检索有结果但回查数据库为空，vectorIds={}", vectorIds);
            return keywordFallbackAnswer(question, policyType);
        }

        // 3. 构建分数映射，按分数阈值过滤
        Map<String, Double> scoreMap = new HashMap<>();
        for (VectorSearchResult vr : vectorResults) {
            scoreMap.put(vr.getVectorId(), vr.getScore());
        }

        // 4. 按分数降序排序并过滤
        List<GovPolicyDocument> filteredDocs = documents.stream()
                .filter(doc -> {
                    Double score = scoreMap.get(doc.getVectorId());
                    return score != null && score >= ragConfig.getScoreThreshold();
                })
                .sorted((a, b) -> {
                    Double scoreA = scoreMap.getOrDefault(a.getVectorId(), 0.0);
                    Double scoreB = scoreMap.getOrDefault(b.getVectorId(), 0.0);
                    return Double.compare(scoreB, scoreA);
                })
                .limit(ragConfig.getTopK())
                .collect(Collectors.toList());

        if (filteredDocs.isEmpty()) {
            log.info("所有文档相似度低于阈值 {}，降级关键词检索", ragConfig.getScoreThreshold());
            return keywordFallbackAnswer(question, policyType);
        }

        // 5. 构建上下文并生成回答
        String answer = generateAnswer(question, filteredDocs);

        // 6. 构建来源列表
        List<PolicyAnswerVO.PolicySource> sources = filteredDocs.stream()
                .map(doc -> new PolicyAnswerVO.PolicySource(
                        doc.getId(),
                        doc.getTitle(),
                        doc.getDocNumber(),
                        doc.getIssuingAuthority(),
                        scoreMap.getOrDefault(doc.getVectorId(), 0.0)
                ))
                .collect(Collectors.toList());

        log.info("RAG检索完成，找到 {} 篇相关文档", filteredDocs.size());

        return new PolicyAnswerVO(answer, sources);
    }

    /**
     * 调用向量检索服务
     */
    private List<VectorSearchResult> searchVector(String question, String policyType) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            if (ragConfig.getApiKey() != null && !ragConfig.getApiKey().isBlank()) {
                headers.set("Authorization", "Bearer " + ragConfig.getApiKey());
            }

            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("query", question);
            requestBody.put("topK", ragConfig.getTopK());
            if (policyType != null && !policyType.isBlank()) {
                requestBody.put("filter", Map.of("policy_type", policyType));
            }

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

            @SuppressWarnings("unchecked")
            Map<String, Object> response = restTemplate.postForObject(
                    ragConfig.getVectorApiUrl(),
                    entity,
                    Map.class
            );

            if (response == null || response.get("results") == null) {
                return Collections.emptyList();
            }

            @SuppressWarnings("unchecked")
            List<Map<String, Object>> results = (List<Map<String, Object>>) response.get("results");

            return results.stream()
                    .map(r -> new VectorSearchResult(
                            (String) r.get("vectorId"),
                            ((Number) r.get("score")).doubleValue()
                    ))
                    .collect(Collectors.toList());

        } catch (Exception e) {
            log.warn("向量检索服务调用失败，降级关键词检索: {}", e.getMessage());
            return Collections.emptyList();
        }
    }

    /**
     * 关键词兜底检索
     */
    private PolicyAnswerVO keywordFallbackAnswer(String question, String policyType) {
        GovPolicyDocumentMapper mapper = govPolicyMapper;

        // 使用MyBatis-Plus条件构造器做关键词搜索
        com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<GovPolicyDocument> wrapper =
                new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<>();
        wrapper.eq(GovPolicyDocument::getDeleted, 0)
               .eq(GovPolicyDocument::getStatus, 1)
               .and(w -> w.like(GovPolicyDocument::getTitle, question)
                         .or().like(GovPolicyDocument::getSummary, question)
                         .or().like(GovPolicyDocument::getFullText, question));
        if (policyType != null && !policyType.isBlank()) {
            wrapper.eq(GovPolicyDocument::getPolicyType, policyType);
        }
        wrapper.orderByDesc(GovPolicyDocument::getPublishDate);
        wrapper.last("LIMIT " + ragConfig.getTopK());

        List<GovPolicyDocument> docs = mapper.selectList(wrapper);

        if (docs.isEmpty()) {
            PolicyAnswerVO result = new PolicyAnswerVO();
            result.setAnswer("抱歉，未找到与您问题相关的政策文档。请尝试更换关键词或联系人工客服。");
            result.setSources(Collections.emptyList());
            return result;
        }

        String answer = generateAnswer(question, docs);
        List<PolicyAnswerVO.PolicySource> sources = docs.stream()
                .map(doc -> new PolicyAnswerVO.PolicySource(
                        doc.getId(),
                        doc.getTitle(),
                        doc.getDocNumber(),
                        doc.getIssuingAuthority(),
                        null
                ))
                .collect(Collectors.toList());

        return new PolicyAnswerVO(answer, sources);
    }

    /**
     * 根据检索到的文档生成回答
     * 将文档内容拼接为上下文，构建回答
     */
    private String generateAnswer(String question, List<GovPolicyDocument> docs) {
        StringBuilder context = new StringBuilder();
        context.append("根据以下政策文档为您解答：\n\n");

        for (int i = 0; i < docs.size(); i++) {
            GovPolicyDocument doc = docs.get(i);
            context.append(String.format("【文档%d】%s\n", i + 1, doc.getTitle()));
            if (doc.getDocNumber() != null) {
                context.append(String.format("文号：%s\n", doc.getDocNumber()));
            }
            if (doc.getIssuingAuthority() != null) {
                context.append(String.format("发文机关：%s\n", doc.getIssuingAuthority()));
            }
            if (doc.getSummary() != null) {
                context.append(String.format("摘要：%s\n", doc.getSummary()));
            }
            // 解析要点
            List<String> keyPoints = parseKeyPoints(doc.getKeyPoints());
            if (!keyPoints.isEmpty()) {
                context.append("要点：\n");
                for (String point : keyPoints) {
                    context.append(String.format("  - %s\n", point));
                }
            }
            // 解析FAQ
            List<FaqItem> faqItems = parseFaq(doc.getFaq());
            if (!faqItems.isEmpty()) {
                context.append("常见问题：\n");
                for (FaqItem faq : faqItems) {
                    context.append(String.format("  问：%s\n  答：%s\n", faq.getQuestion(), faq.getAnswer()));
                }
            }
            context.append("\n");
        }

        context.append("您的提问：").append(question).append("\n\n");
        context.append("请参考以上政策文档内容，如需更详细信息请联系相关部门。");

        return context.toString();
    }

    /**
     * 解析要点JSON
     */
    private List<String> parseKeyPoints(String keyPointsJson) {
        if (keyPointsJson == null || keyPointsJson.isBlank()) {
            return Collections.emptyList();
        }
        try {
            return objectMapper.readValue(keyPointsJson, new TypeReference<List<String>>() {});
        } catch (Exception e) {
            log.warn("解析keyPoints失败: {}", e.getMessage());
            return Collections.emptyList();
        }
    }

    /**
     * 解析FAQ JSON
     */
    private List<FaqItem> parseFaq(String faqJson) {
        if (faqJson == null || faqJson.isBlank()) {
            return Collections.emptyList();
        }
        try {
            return objectMapper.readValue(faqJson, new TypeReference<List<FaqItem>>() {});
        } catch (Exception e) {
            log.warn("解析faq失败: {}", e.getMessage());
            return Collections.emptyList();
        }
    }

    // ==================== 内部类 ====================

    /**
     * 向量检索结果
     */
    private static class VectorSearchResult {
        private final String vectorId;
        private final double score;

        public VectorSearchResult(String vectorId, double score) {
            this.vectorId = vectorId;
            this.score = score;
        }

        public String getVectorId() {
            return vectorId;
        }

        public double getScore() {
            return score;
        }
    }

    /**
     * FAQ项
     */
    private static class FaqItem {
        private String question;
        private String answer;

        public String getQuestion() {
            return question;
        }

        public void setQuestion(String question) {
            this.question = question;
        }

        public String getAnswer() {
            return answer;
        }

        public void setAnswer(String answer) {
            this.answer = answer;
        }
    }
}
