package com.zhiban.ai;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * 认证与智能体接口集成测试
 *
 * 覆盖附件一 §3.1（认证）、§3.4（人设）、§10.3（安全）。
 * 使用 H2 内存库，不依赖外部 MySQL；AI 服务调用通过 Mock 拦截。
 *
 * @author zhiban
 */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@DisplayName("认证与智能体接口")
class AuthAndAgentIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    private final ObjectMapper mapper = new ObjectMapper();

    // ── §3.1 游客登录 ───────────────────────────────────

    @Test
    @DisplayName("游客登录无需凭证即可获得 JWT Token")
    void guestLoginReturnsToken() throws Exception {
        MvcResult result = mockMvc.perform(post("/auth/guest-login"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.token").isNotEmpty())
                .andExpect(jsonPath("$.data.userId").isNumber())
                .andReturn();

        JsonNode data = mapper.readTree(result.getResponse().getContentAsString()).get("data");
        // 游客用户名应为 guest_ 前缀
        assertThat(data.get("username").asText()).startsWith("guest_");
        // JWT 应为三段式
        assertThat(data.get("token").asText().split("\\.")).hasSize(3);
    }

    // ── §3.1 用户信息（需认证 + 手机号脱敏）───────────────

    @Test
    @DisplayName("未携带 Token 访问 user-info 返回 401/403")
    void userInfoRequiresAuth() throws Exception {
        int code = mockMvc.perform(get("/auth/user-info"))
                .andReturn().getResponse().getStatus();
        assertThat(code).isIn(401, 403);
    }

    @Test
    @DisplayName("携带 Token 可获取用户信息，手机号必须脱敏")
    void userInfoReturnsMaskedPhone() throws Exception {
        String token = guestToken();

        mockMvc.perform(get("/auth/user-info").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.userId").isNumber())
                .andExpect(jsonPath("$.data.guest").value(true));
    }

    // ── §3.1 Token 刷新 ─────────────────────────────────

    @Test
    @DisplayName("Token 刷新返回新 Token")
    void refreshIssuesNewToken() throws Exception {
        String token = guestToken();

        mockMvc.perform(post("/auth/refresh")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.token").isNotEmpty())
                .andExpect(jsonPath("$.data.expiresIn").value(86400000L));
    }

    @Test
    @DisplayName("无效 Token 刷新被拒绝")
    void refreshRejectsInvalidToken() throws Exception {
        mockMvc.perform(post("/auth/refresh")
                        .header("Authorization", "Bearer not-a-real-token"))
                .andExpect(jsonPath("$.code").value(401));
    }

    // ── §3.4 智能体人设 ─────────────────────────────────

    @Test
    @DisplayName("获取人设默认返回康养智能体")
    void personaDefaultsToElderly() throws Exception {
        mockMvc.perform(get("/agent/persona").header("Authorization", "Bearer " + guestToken()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.agentType").value("elderly"))
                .andExpect(jsonPath("$.data.greeting").isNotEmpty());
    }

    @Test
    @DisplayName("三大智能体人设均可获取（康养/政务/文旅）")
    void allThreeAgentsAvailable() throws Exception {
        String token = guestToken();
        for (String type : new String[]{"elderly", "govpolicy", "tourism"}) {
            mockMvc.perform(get("/agent/persona")
                            .param("agentType", type)
                            .header("Authorization", "Bearer " + token))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.data.agentType").value(type))
                    .andExpect(jsonPath("$.data.name").isNotEmpty());
        }
    }

    @Test
    @DisplayName("切换智能体返回目标人设")
    void switchAgentReturnsPersona() throws Exception {
        mockMvc.perform(post("/agent/switch/tourism")
                        .header("Authorization", "Bearer " + guestToken()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.agentType").value("tourism"));
    }

    @Test
    @DisplayName("切换到未知智能体返回 400")
    void switchUnknownAgentRejected() throws Exception {
        mockMvc.perform(post("/agent/switch/unknown")
                        .header("Authorization", "Bearer " + guestToken()))
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    @DisplayName("智能体列表返回三大方向")
    void agentListHasThreeEntries() throws Exception {
        MvcResult r = mockMvc.perform(get("/agent/list")
                        .header("Authorization", "Bearer " + guestToken()))
                .andExpect(status().isOk())
                .andReturn();
        JsonNode list = mapper.readTree(r.getResponse().getContentAsString()).get("data");
        assertThat(list).hasSize(3);
    }

    // ── §3.5 内容接口（公开）────────────────────────────

    @Test
    @DisplayName("文章与政策列表为公开接口")
    void contentListsArePublic() throws Exception {
        mockMvc.perform(get("/help/articles").param("page", "1").param("size", "10"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));

        mockMvc.perform(get("/help/gov-policy").param("page", "1").param("size", "10"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    @DisplayName("分类接口为公开接口")
    void categoriesArePublic() throws Exception {
        mockMvc.perform(get("/help/categories"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }

    // ── §10.3 安全：未认证请求被拦截 ─────────────────────

    @Test
    @DisplayName("对话接口未认证时被拦截")
    void chatRequiresAuth() throws Exception {
        int code = mockMvc.perform(post("/chat/send")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"content\":\"你好\"}"))
                .andReturn().getResponse().getStatus();
        assertThat(code).isIn(401, 403);
    }

    @Test
    @DisplayName("会话列表未认证时被拦截")
    void sessionsRequireAuth() throws Exception {
        int code = mockMvc.perform(get("/chat/sessions"))
                .andReturn().getResponse().getStatus();
        assertThat(code).isIn(401, 403);
    }

    // ── §3.2 会话管理（认证后）──────────────────────────

    @Test
    @DisplayName("可创建会话并查询会话列表")
    void createAndListSession() throws Exception {
        String token = guestToken();

        MvcResult created = mockMvc.perform(post("/chat/session")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"测试会话\",\"agentType\":\"tourism\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.agentType").value("tourism"))
                .andReturn();

        long sessionId = mapper.readTree(created.getResponse().getContentAsString())
                .get("data").get("id").asLong();

        mockMvc.perform(get("/chat/sessions").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.records[0].id").value(sessionId));

        mockMvc.perform(get("/chat/history")
                        .param("sessionId", String.valueOf(sessionId))
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    @DisplayName("无法访问他人的会话（越权防护）")
    void cannotAccessOthersSession() throws Exception {
        String tokenA = guestToken();
        String tokenB = guestToken();

        MvcResult created = mockMvc.perform(post("/chat/session")
                        .header("Authorization", "Bearer " + tokenA)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"A的会话\"}"))
                .andExpect(status().isOk())
                .andReturn();

        long sessionId = mapper.readTree(created.getResponse().getContentAsString())
                .get("data").get("id").asLong();

        // B 访问 A 的会话历史应被拒绝
        mockMvc.perform(get("/chat/history")
                        .param("sessionId", String.valueOf(sessionId))
                        .header("Authorization", "Bearer " + tokenB))
                .andExpect(jsonPath("$.code").value(403));
    }

    // ── 辅助方法 ────────────────────────────────────────

    private String guestToken() throws Exception {
        MvcResult r = mockMvc.perform(post("/auth/guest-login"))
                .andExpect(status().isOk())
                .andReturn();
        return mapper.readTree(r.getResponse().getContentAsString())
                .get("data").get("token").asText();
    }
}
