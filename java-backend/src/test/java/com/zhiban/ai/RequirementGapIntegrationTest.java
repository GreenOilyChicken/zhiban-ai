package com.zhiban.ai;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.zhiban.ai.entity.User;
import com.zhiban.ai.mapper.UserMapper;
import com.zhiban.ai.security.PhoneCryptoService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * 本次补齐需求（附件一）的集成测试
 *
 * 覆盖：
 *  - §3.5 规范 API 路径（/articles、/policies、/quota）
 *  - §4.1 文章相关推荐
 *  - §4.2 管理端配额查看与调整
 *  - §4.2 管理端知识库上传/同步（权限与参数校验）
 *  - §8.1 手机号加密存储（密文落库 + 可解密 + 盲索引可查）
 *
 * @author zhiban
 */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@DisplayName("需求补齐项：路径对齐/相关推荐/配额调整/手机号加密")
class RequirementGapIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private UserMapper userMapper;

    @Autowired
    private PhoneCryptoService phoneCryptoService;

    private final ObjectMapper mapper = new ObjectMapper();

    // ── §3.5 规范路径 ───────────────────────────────────

    @Test
    @DisplayName("附件一规范路径 /articles 与兼容路径 /help/articles 均可用")
    void canonicalArticlePathsWork() throws Exception {
        mockMvc.perform(get("/articles").param("page", "1").param("size", "10"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));

        mockMvc.perform(get("/help/articles").param("page", "1").param("size", "10"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    @DisplayName("附件一规范路径 /policies 与兼容路径 /help/gov-policy 均可用")
    void canonicalPolicyPathsWork() throws Exception {
        mockMvc.perform(get("/policies").param("page", "1").param("size", "10"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));

        mockMvc.perform(get("/help/gov-policy").param("page", "1").param("size", "10"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    @DisplayName("附件一规范路径 /quota 需登录且默认 POLICY_QA")
    void canonicalQuotaPathRequiresAuth() throws Exception {
        // 未认证 -> 401/403
        int code = mockMvc.perform(get("/quota"))
                .andReturn().getResponse().getStatus();
        assertThat(code).isIn(401, 403);

        // 认证后可不传 quotaType，默认 POLICY_QA
        mockMvc.perform(get("/quota").header("Authorization", "Bearer " + guestToken()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.quotaType").value("POLICY_QA"))
                .andExpect(jsonPath("$.data.totalAmount").isNumber());
    }

    @Test
    @DisplayName("§3.4 切换智能体的规范路径 /agent/switch/{type} 可用")
    void agentSwitchPathWorks() throws Exception {
        mockMvc.perform(post("/agent/switch/elderly")
                        .header("Authorization", "Bearer " + guestToken()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.agentType").value("elderly"));
    }

    // ── §4.1 相关推荐 ───────────────────────────────────

    @Test
    @DisplayName("§4.1 文章详情相关推荐接口可用且不包含自身")
    void relatedArticlesEndpoint() throws Exception {
        // 创建文章为管理端接口，需 ADMIN 角色
        String admin = adminToken();

        // 建两篇同分类文章
        long id1 = createArticle(admin, "相关推荐测试A", "测试分类X");
        long id2 = createArticle(admin, "相关推荐测试B", "测试分类X");

        MvcResult r = mockMvc.perform(get("/articles/" + id1 + "/related")
                        .param("limit", "5"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andReturn();

        JsonNode data = mapper.readTree(r.getResponse().getContentAsString()).get("data");
        assertThat(data.isArray()).isTrue();
        // 结果中不应包含当前文章自身
        for (JsonNode n : data) {
            assertThat(n.get("id").asLong()).isNotEqualTo(id1);
        }
        // 同分类的另一篇应出现在推荐中
        boolean containsSibling = false;
        for (JsonNode n : data) {
            if (n.get("id").asLong() == id2) {
                containsSibling = true;
            }
        }
        assertThat(containsSibling).as("同分类文章应被推荐").isTrue();
    }

    // ── §4.2 配额查看与调整 ─────────────────────────────

    @Test
    @DisplayName("§4.2 管理端配额列表与调整接口可用")
    void adminQuotaListAndAdjust() throws Exception {
        String admin = adminToken();
        String userToken = guestToken();

        // 先以普通用户触发一次配额初始化
        mockMvc.perform(get("/quota").header("Authorization", "Bearer " + userToken))
                .andExpect(status().isOk());

        // 管理端列表可查
        MvcResult listResult = mockMvc.perform(get("/admin/quota")
                        .header("Authorization", "Bearer " + admin))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andReturn();
        JsonNode list = mapper.readTree(listResult.getResponse().getContentAsString()).get("data");
        assertThat(list.isArray()).isTrue();
        assertThat(list.size()).isGreaterThan(0);

        long userId = list.get(0).get("userId").asLong();
        String quotaType = list.get(0).get("quotaType").asText();

        // 调整总量
        mockMvc.perform(put("/admin/quota/" + userId + "/" + quotaType)
                        .header("Authorization", "Bearer " + admin)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"totalAmount\":500,\"usedAmount\":5,\"freeAmount\":20}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.totalAmount").value(500))
                .andExpect(jsonPath("$.data.usedAmount").value(5))
                .andExpect(jsonPath("$.data.remainingAmount").value(495))
                .andExpect(jsonPath("$.data.freeAmount").value(20));
    }

    @Test
    @DisplayName("§4.2 已用配额超过总量时被拒绝（400）")
    void adjustQuotaRejectsUsedOverTotal() throws Exception {
        String admin = adminToken();
        String userToken = guestToken();
        mockMvc.perform(get("/quota").header("Authorization", "Bearer " + userToken));

        MvcResult listResult = mockMvc.perform(get("/admin/quota")
                        .header("Authorization", "Bearer " + admin))
                .andReturn();
        JsonNode list = mapper.readTree(listResult.getResponse().getContentAsString()).get("data");
        long userId = list.get(0).get("userId").asLong();
        String quotaType = list.get(0).get("quotaType").asText();

        mockMvc.perform(put("/admin/quota/" + userId + "/" + quotaType)
                        .header("Authorization", "Bearer " + admin)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"totalAmount\":10,\"usedAmount\":99}"))
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    @DisplayName("§4.2 普通用户访问管理端配额接口被拒绝（403）")
    void adminQuotaRequiresAdminRole() throws Exception {
        int code = mockMvc.perform(get("/admin/quota")
                        .header("Authorization", "Bearer " + guestToken()))
                .andReturn().getResponse().getStatus();
        assertThat(code).isIn(401, 403);
    }

    @Test
    @DisplayName("schema.sql 内置管理员账号可正常登录（防止种子数据哈希失效）")
    void seededAdminCanLogin() throws Exception {
        mockMvc.perform(post("/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"admin\",\"password\":\"admin123\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.token").isNotEmpty())
                .andExpect(jsonPath("$.data.role").value("ADMIN"));
    }

    // ── §4.2 知识库上传/同步（权限与参数校验）────────────

    @Test
    @DisplayName("§4.2 普通用户访问知识库管理接口被拒绝（403）")
    void adminKbRequiresAdminRole() throws Exception {
        int code = mockMvc.perform(post("/admin/kb/sync")
                        .param("collection", "govpolicy")
                        .header("Authorization", "Bearer " + guestToken()))
                .andReturn().getResponse().getStatus();
        assertThat(code).isIn(401, 403);
    }

    @Test
    @DisplayName("§4.2 知识库同步拒绝未知集合（400）")
    void adminKbRejectsUnknownCollection() throws Exception {
        mockMvc.perform(post("/admin/kb/sync")
                        .param("collection", "not-a-collection")
                        .header("Authorization", "Bearer " + adminToken()))
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    @DisplayName("§4.2 知识库上传拒绝非文本类型（400）")
    void adminKbRejectsBadFileType() throws Exception {
        mockMvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                        .multipart("/admin/kb/upload")
                        .file(new org.springframework.mock.web.MockMultipartFile(
                                "file", "evil.exe", "application/octet-stream", "x".getBytes()))
                        .param("collection", "govpolicy")
                        .header("Authorization", "Bearer " + adminToken()))
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    @DisplayName("§4.2 知识库上传拒绝空文件（400）")
    void adminKbRejectsEmptyFile() throws Exception {
        mockMvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                        .multipart("/admin/kb/upload")
                        .file(new org.springframework.mock.web.MockMultipartFile(
                                "file", "empty.txt", "text/plain", new byte[0]))
                        .param("collection", "govpolicy")
                        .header("Authorization", "Bearer " + adminToken()))
                .andExpect(jsonPath("$.code").value(400));
    }

    // ── §8.1 手机号加密存储 ─────────────────────────────

    @Test
    @DisplayName("§8.1 手机号在数据库中为密文，不落明文")
    void phoneIsEncryptedAtRest() throws Exception {
        String phone = "13900001234";
        registerUser("enc_test_user", phone);

        // 直接查库确认落库值
        String stored = jdbcTemplate.queryForObject(
                "SELECT phone FROM user WHERE username = ?", String.class, "enc_test_user");
        assertThat(stored).as("落库值不应为明文").isNotEqualTo(phone);
        assertThat(stored).as("应为 enc1: 前缀密文").startsWith("enc1:");
        assertThat(stored).doesNotContain(phone);

        // 密文可正确解密回明文
        assertThat(phoneCryptoService.decrypt(stored)).isEqualTo(phone);

        // 盲索引已写入且不等于明文
        String hash = jdbcTemplate.queryForObject(
                "SELECT phone_hash FROM user WHERE username = ?", String.class, "enc_test_user");
        assertThat(hash).isNotBlank();
        assertThat(hash).isNotEqualTo(phone);
    }

    @Test
    @DisplayName("§8.1 手机号加密非确定性：同一手机号两次加密结果不同")
    void phoneEncryptionIsNonDeterministic() {
        String phone = "13800005678";
        String c1 = phoneCryptoService.encrypt(phone);
        String c2 = phoneCryptoService.encrypt(phone);
        assertThat(c1).isNotEqualTo(c2);
        assertThat(phoneCryptoService.decrypt(c1)).isEqualTo(phone);
        assertThat(phoneCryptoService.decrypt(c2)).isEqualTo(phone);
    }

    @Test
    @DisplayName("§8.1 盲索引确定性：同一手机号盲索引一致，可用于等值查询")
    void blindIndexIsDeterministic() {
        String phone = "13700009999";
        assertThat(phoneCryptoService.blindIndex(phone))
                .isEqualTo(phoneCryptoService.blindIndex(phone));
        assertThat(phoneCryptoService.blindIndex(phone))
                .isNotEqualTo(phoneCryptoService.blindIndex("13700009998"));
    }

    @Test
    @DisplayName("§8.1 历史明文数据仍可读取（向后兼容）")
    void legacyPlaintextStillReadable() {
        assertThat(phoneCryptoService.decrypt("13800138000")).isEqualTo("13800138000");
        assertThat(phoneCryptoService.decrypt(null)).isNull();
        assertThat(phoneCryptoService.decrypt("")).isEmpty();
    }

    @Test
    @DisplayName("§8.1 通过盲索引可按手机号查到用户")
    void userLookupByPhoneHash() throws Exception {
        String phone = "13600001111";
        registerUser("hash_lookup_user", phone);

        User found = userMapper.selectByPhoneHash(phoneCryptoService.blindIndex(phone));
        assertThat(found).isNotNull();
        assertThat(found.getUsername()).isEqualTo("hash_lookup_user");
        assertThat(phoneCryptoService.decrypt(found.getPhone())).isEqualTo(phone);
    }

    // ── 辅助方法 ────────────────────────────────────────

    private String guestToken() throws Exception {
        MvcResult r = mockMvc.perform(post("/auth/guest-login"))
                .andExpect(status().isOk())
                .andReturn();
        return mapper.readTree(r.getResponse().getContentAsString())
                .get("data").get("token").asText();
    }

    /**
     * 使用 schema.sql 中的默认管理员账号登录（admin / admin123）
     */
    private String adminToken() throws Exception {
        MvcResult r = mockMvc.perform(post("/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"admin\",\"password\":\"admin123\"}"))
                .andExpect(status().isOk())
                .andReturn();
        return mapper.readTree(r.getResponse().getContentAsString())
                .get("data").get("token").asText();
    }

    private long createArticle(String token, String title, String category) throws Exception {
        MvcResult r = mockMvc.perform(post("/admin/help/article")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(mapper.writeValueAsString(java.util.Map.of(
                                "title", title,
                                "content", "测试正文内容",
                                "category", category,
                                "isPublished", 1))))
                .andExpect(status().isOk())
                .andReturn();
        return mapper.readTree(r.getResponse().getContentAsString()).get("data").asLong();
    }

    private void registerUser(String username, String phone) throws Exception {
        mockMvc.perform(post("/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(mapper.writeValueAsString(java.util.Map.of(
                                "username", username,
                                "password", "passw0rd123",
                                "phone", phone))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }
}
