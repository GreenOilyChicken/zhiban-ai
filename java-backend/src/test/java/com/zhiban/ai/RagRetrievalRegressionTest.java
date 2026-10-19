package com.zhiban.ai;

import com.zhiban.ai.dto.PolicyAnswerVO;
import com.zhiban.ai.service.impl.RagService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * RAG 检索链路回归测试
 *
 * 覆盖本次修复的缺陷：
 *  1. 关键词兜底检索原先拿「整个问题」做 LIKE，几乎永不命中；
 *  2. 知识库元数据无 policy_type 字段，按该字段过滤会把结果全部丢弃；
 *  3. 阈值过滤过于严格时会静默降级为关键词检索。
 *
 * 说明：测试环境不启动 Python AI 服务，向量检索必然失败，
 * 因此这里实际走的是「关键词兜底」路径——正好覆盖缺陷 1。
 *
 * @author zhiban
 */
@SpringBootTest
@ActiveProfiles("test")
@DisplayName("RAG 检索链路回归")
class RagRetrievalRegressionTest {

    @Autowired
    private RagService ragService;

    @Test
    @DisplayName("关键词兜底：整句式提问也能命中政策文档（修复前命中不到）")
    void keywordFallbackMatchesNaturalQuestion() {
        // 这是一个「整句提问」，修复前会拼成 LIKE '%长期护理保险怎么申请%'，命中为空
        PolicyAnswerVO result = ragService.searchAndAnswer("长期护理保险怎么申请", null);

        assertThat(result).isNotNull();
        assertThat(result.getSources()).as("应命中政策文档来源").isNotEmpty();
        assertThat(result.getAnswer()).contains("长期护理保险");
    }

    @Test
    @DisplayName("关键词兜底：命中结果带可追溯来源（附件一 §6.3）")
    void keywordFallbackReturnsTraceableSources() {
        PolicyAnswerVO result = ragService.searchAndAnswer("医保报销流程", null);

        assertThat(result.getSources()).isNotEmpty();
        result.getSources().forEach(src -> {
            assertThat(src.getTitle()).as("来源必须带标题").isNotBlank();
            assertThat(src.getId()).as("来源必须带可追溯的文档ID").isNotNull();
        });
    }

    @Test
    @DisplayName("关键词兜底：政策类型筛选在实体层生效")
    void keywordFallbackRespectsPolicyType() {
        PolicyAnswerVO result = ragService.searchAndAnswer("银发经济", "银发经济");
        assertThat(result.getSources()).isNotEmpty();
        // 结果标题应来自银发经济类文档
        assertThat(result.getSources().stream().anyMatch(s ->
                s.getTitle() != null && s.getTitle().contains("银发经济"))).isTrue();
    }

    @Test
    @DisplayName("无匹配时给出友好提示而非报错")
    void noMatchReturnsFriendlyAnswer() {
        PolicyAnswerVO result = ragService.searchAndAnswer("量子纠缠与外星文明", null);
        assertThat(result).isNotNull();
        assertThat(result.getAnswer()).isNotBlank();
    }
}
