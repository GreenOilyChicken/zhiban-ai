package com.zhiban.ai.service.impl;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.zhiban.ai.config.RagConfig;
import com.zhiban.ai.dto.PolicyAnswerVO;
import com.zhiban.ai.entity.GovPolicyDocument;
import com.zhiban.ai.exception.BusinessException;
import com.zhiban.ai.mapper.GovPolicyDocumentMapper;
import com.zhiban.ai.service.AiAgentClient;
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
import java.util.LinkedHashSet;
import java.util.Set;
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
    private final AiAgentClient aiAgentClient;

    public RagService(RagConfig ragConfig,
                      GovPolicyDocumentMapper govPolicyMapper,
                      ObjectMapper objectMapper,
                      AiAgentClient aiAgentClient) {
        this.ragConfig = ragConfig;
        this.govPolicyMapper = govPolicyMapper;
        this.objectMapper = objectMapper;
        this.aiAgentClient = aiAgentClient;
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

        // 4. 按分数降序排序，再按阈值优先过滤
        List<GovPolicyDocument> ranked = documents.stream()
                // 政策类型筛选在实体层进行（知识库元数据无 policy_type 字段）
                .filter(doc -> policyType == null || policyType.isBlank()
                        || policyType.equals(doc.getPolicyType()))
                .sorted((a, b) -> {
                    Double scoreA = scoreMap.getOrDefault(a.getVectorId(), 0.0);
                    Double scoreB = scoreMap.getOrDefault(b.getVectorId(), 0.0);
                    return Double.compare(scoreB, scoreA);
                })
                .collect(Collectors.toList());

        double threshold = ragConfig.getScoreThreshold();
        List<GovPolicyDocument> filteredDocs = ranked.stream()
                .filter(doc -> {
                    Double score = scoreMap.get(doc.getVectorId());
                    return score != null && score >= threshold;
                })
                .limit(ragConfig.getTopK())
                .collect(Collectors.toList());

        // 若没有结果达到阈值，但向量检索确实命中了已入库文档，
        // 则退而取排序后的 Top-K，而不是直接降级为关键词检索。
        //
        // 原因：不同 Embedding 模型的相似度绝对值分布差异很大
        // （hash 兜底、bge 等各不相同），固定高阈值会把「确实相关但分数偏低」
        // 的结果全部丢弃，导致政策问答静默退化为关键词匹配、答非所问。
        if (filteredDocs.isEmpty() && !ranked.isEmpty()) {
            log.info("无文档达到阈值 {}，改用向量排序 Top-{} 作为结果",
                    threshold, ragConfig.getTopK());
            filteredDocs = ranked.stream()
                    .limit(ragConfig.getTopK())
                    .collect(Collectors.toList());
        }

        if (filteredDocs.isEmpty()) {
            log.info("向量检索未命中任何已入库文档，降级关键词检索");
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
            // 注意：不向向量库传 policy_type 过滤。
            // 知识库元数据只有 source / category（见 build_kb._load_documents），
            // 并无 policy_type 字段；若在此过滤，条件永不匹配会把结果全部丢弃。
            // 政策类型筛选改在回查 MySQL 后按实体字段进行（见 searchAndAnswer）。

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
     *
     * 修复要点：原实现直接把「整个问题」当作 LIKE 模式，
     * 例如「长期护理保险怎么申请」会被拼成
     * LIKE '%长期护理保险怎么申请%'，几乎不可能命中任何文档，
     * 导致兜底检索形同虚设。
     *
     * 现改为：把问题切分为 2 字以上的词块（中文按二元切分、英文按单词），
     * 再用 OR 组合匹配标题/摘要/全文，并按命中词数排序。
     */
    private PolicyAnswerVO keywordFallbackAnswer(String question, String policyType) {
        List<String> terms = extractKeywords(question);

        if (terms.isEmpty()) {
            PolicyAnswerVO result = new PolicyAnswerVO();
            result.setAnswer("抱歉，未找到与您问题相关的政策文档。请尝试更换关键词或联系人工客服。");
            result.setSources(Collections.emptyList());
            return result;
        }

        com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<GovPolicyDocument> wrapper =
                new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<>();
        wrapper.eq(GovPolicyDocument::getDeleted, 0)
               .eq(GovPolicyDocument::getStatus, 1);
        if (policyType != null && !policyType.isBlank()) {
            wrapper.eq(GovPolicyDocument::getPolicyType, policyType);
        }
        // 任一关键词命中标题/摘要/全文即视为候选
        wrapper.and(w -> {
            for (int i = 0; i < terms.size(); i++) {
                String term = terms.get(i);
                if (i == 0) {
                    w.and(x -> x.like(GovPolicyDocument::getTitle, term)
                                .or().like(GovPolicyDocument::getSummary, term)
                                .or().like(GovPolicyDocument::getFullText, term));
                } else {
                    w.or(x -> x.like(GovPolicyDocument::getTitle, term)
                               .or().like(GovPolicyDocument::getSummary, term)
                               .or().like(GovPolicyDocument::getFullText, term));
                }
            }
        });
        wrapper.orderByDesc(GovPolicyDocument::getPublishDate);
        // 多取一些候选，再按命中词数精排
        wrapper.last("LIMIT " + Math.max(ragConfig.getTopK() * 4, 20));

        List<GovPolicyDocument> candidates = govPolicyMapper.selectList(wrapper);

        // 按命中关键词数量降序，命中越多越相关
        List<GovPolicyDocument> docs = candidates.stream()
                .sorted((a, b) -> Integer.compare(hitCount(b, terms), hitCount(a, terms)))
                .limit(ragConfig.getTopK())
                .collect(Collectors.toList());

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
     * 从问题中提取用于 LIKE 匹配的关键词
     *
     * 策略：
     *  - 去掉常见疑问词与标点（怎么、如何、什么、请问、可以 等），这些词无区分度；
     *  - 连续中文按 2 字滑窗切分（如「长期护理保险」→ 长期/期护/护理/理保/保险），
     *    再保留其中较长的整词块，避免切得过碎；
     *  - 英文/数字按单词切分。
     */
    private List<String> extractKeywords(String question) {
        if (question == null || question.isBlank()) {
            return Collections.emptyList();
        }

        // 去除无区分度的疑问词/语气词
        String cleaned = question;
        for (String noise : new String[]{
                "请问", "我想", "我要", "怎么", "如何", "什么", "哪些", "哪个",
                "可以", "能否", "是否", "需要", "关于", "一下", "的话", "吗", "呢", "的"}) {
            cleaned = cleaned.replace(noise, " ");
        }

        Set<String> terms = new LinkedHashSet<>();

        // 中文连续片段：按 2 字滑窗
        java.util.regex.Matcher zh = java.util.regex.Pattern
                .compile("[\\u4e00-\\u9fa5]{2,}")
                .matcher(cleaned);
        while (zh.find()) {
            String seg = zh.group();
            if (seg.length() <= 4) {
                terms.add(seg);
            } else {
                for (int i = 0; i + 2 <= seg.length(); i++) {
                    terms.add(seg.substring(i, i + 2));
                }
            }
        }

        // 英文/数字单词
        java.util.regex.Matcher en = java.util.regex.Pattern
                .compile("[A-Za-z0-9]{2,}")
                .matcher(cleaned);
        while (en.find()) {
            terms.add(en.group());
        }

        return terms.stream()
                .filter(t -> t.length() >= 2)
                .limit(20)
                .collect(Collectors.toList());
    }

    /**
     * 统计文档命中的关键词数量（用于兜底检索的相关性排序）
     */
    private int hitCount(GovPolicyDocument doc, List<String> terms) {
        StringBuilder sb = new StringBuilder();
        if (doc.getTitle() != null) {
            sb.append(doc.getTitle());
        }
        if (doc.getSummary() != null) {
            sb.append(doc.getSummary());
        }
        if (doc.getFullText() != null) {
            sb.append(doc.getFullText());
        }
        String text = sb.toString();
        int hits = 0;
        for (String term : terms) {
            if (text.contains(term)) {
                hits++;
            }
        }
        return hits;
    }

    /**
     * 根据检索到的文档生成回答。
     *
     * 实现策略（真正的 RAG 生成）：
     * 1. 把检索到的政策文档字段拼成「上下文」；
     * 2. 构造指令 prompt，要求大模型「仅依据上下文回答、不得编造、标注来源」；
     * 3. 调用 AiAgentClient.chat()（经 Python 侧 LLM 生成自然语言回答）；
     * 4. 若 LLM 不可用或超时，降级为字段拼接（buildFallbackAnswer），保证可用。
     *
     * @param question 用户提问
     * @param docs     检索命中的政策文档
     * @return 自然语言回答（含来源标注）
     */
    private String generateAnswer(String question, List<GovPolicyDocument> docs) {
        String context = buildContextText(docs);

        // 构造 RAG 指令 prompt：约束模型只用提供的文档回答
        String prompt = "你是一名政务政策助手。请严格依据以下政策文档为用户解答，"
                + "不得编造文档之外的信息。回答要通俗、准确，并在相关处标注来源"
                + "（如「据《文号》」）。若文档不足以回答，请直接说明并建议用户咨询相关部门。\n\n"
                + "【政策文档】\n" + context + "\n"
                + "【用户提问】" + question + "\n\n"
                + "请基于上述政策文档作答。";

        try {
            String reply = aiAgentClient.chat(prompt, "govpolicy", Collections.emptyList());
            if (reply != null && !reply.isBlank()) {
                return reply;
            }
            log.warn("LLM 返回空内容，降级字段拼接");
        } catch (Exception e) {
            log.warn("调用 LLM 生成回答失败，降级字段拼接: {}", e.getMessage());
        }
        // 降级：用文档字段拼接出可读回答
        return buildFallbackAnswer(question, docs);
    }

    /**
     * 把文档字段拼成上下文文本，供 LLM prompt 与降级回答共用。
     */
    private String buildContextText(List<GovPolicyDocument> docs) {
        StringBuilder context = new StringBuilder();
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
            List<String> keyPoints = parseKeyPoints(doc.getKeyPoints());
            if (!keyPoints.isEmpty()) {
                context.append("要点：\n");
                for (String point : keyPoints) {
                    context.append(String.format("  - %s\n", point));
                }
            }
            List<FaqItem> faqItems = parseFaq(doc.getFaq());
            if (!faqItems.isEmpty()) {
                context.append("常见问题：\n");
                for (FaqItem faq : faqItems) {
                    context.append(String.format("  问：%s\n  答：%s\n", faq.getQuestion(), faq.getAnswer()));
                }
            }
            context.append("\n");
        }
        return context.toString();
    }

    /**
     * 降级回答：LLM 不可用时，用文档字段拼接出可读回答（原 generateAnswer 逻辑）。
     */
    private String buildFallbackAnswer(String question, List<GovPolicyDocument> docs) {
        StringBuilder sb = new StringBuilder();
        sb.append("根据以下政策文档为您解答：\n\n");
        sb.append(buildContextText(docs));
        sb.append("您的提问：").append(question).append("\n\n");
        sb.append("请参考以上政策文档内容，如需更详细信息请联系相关部门。");
        return sb.toString();
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
