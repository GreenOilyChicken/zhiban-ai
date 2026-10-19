# 验证报告（Verification Report）

> 项目：知伴AI双端智能体APP
> 验证时间：2026-10-10（首轮）／2026-10-10（第二轮补齐后复验）
> 验证方式：编译 + 单元测试 + 集成测试 + 真实联调 + 端到端实测

---

## 0. 第二轮复验结果（补齐需求缺口后）

本轮在「不改动 ASR」的前提下补齐了附件一其余缺口，并对修复项做了实测复验。

| 模块 | 验证项 | 命令 | 结果 |
|---|---|---|---|
| Java | 全量测试 | `mvn test` | ✅ **43 run / 0 fail**（38 执行 + 5 联调跳过）|
| Java | 需求补齐项集成测试 | `RequirementGapIntegrationTest` | ✅ 18 passed |
| Java | RAG 检索链路回归 | `RagRetrievalRegressionTest` | ✅ 4 passed |
| Python | 单元测试 | `pytest tests/ -q` | ✅ **35 passed**（新增 4 项回归）|
| Python | 向量库重建（21 篇语料）| `build_knowledge_base(rebuild=True)` | ✅ govpolicy 23 / elderly 19 / tourism 19 片段 |
| Python | 真实相似度分数 | `POST /api/v1/search` | ✅ 返回真实相似度（如 0.2597），修复前恒为 0.0 |
| Python | 知识库上传（含重复重建）| `POST /api/v1/kb/upload` | ✅ 上传+重建成功，连续两次均成功 |
| Python | TTS 语音合成 | `POST /api/v1/tts` | ✅ HTTP 200，18,288 字节真实 MP3 |
| Python | ASR（按用户要求不做）| `POST /api/v1/asr` | ➖ HTTP 501（符合预期）|
| Vue | 生产构建 | `npm run build` | ✅ 成功（9.60s）|
| 小程序 | JS 语法 | `node --check`（10 个文件）| ✅ 全部通过 |
| 小程序 | 适老化字号 | 全量 `font-size` 扫描 | ✅ 最小 32rpx，无低于阈值 |
| 小程序 | 页面/图标完整性 | `app.json` 校验 | ✅ 8 页 + 6 图标，无缺失 |
| 部署 | compose 解析（默认/HTTPS）| `docker compose config -q` | ✅ 两种模式均 exit 0 |

### 0.1 本轮修复缺陷的实测证据

| 缺陷 | 修复前 | 修复后（实测）|
|---|---|---|
| 管理员哈希错误 | `matches("admin123", hash)` = **false** | = **true**，`seededAdminCanLogin` 用例锁定 |
| 向量分数恒为 0 | `score: 0.0`（阈值 0.75 永不通过）| `sim=0.2597 / 0.1002 / 0.0853` 真实相似度 |
| 重复重建失败 | 第 2 次起 `readonly database` | 连续 3 次重建全部成功 |
| 上传集合被忽略 | 传 `elderly` 却落入 `policies/` | 正确落入 `elderly/` |
| 关键词兜底不命中 | 整句 LIKE，命中为空 | `长期护理保险怎么申请` 命中并返回来源 |
| 手机号明文落库 | `phone` = 明文 | `phone` = `enc1:...` 密文，`phone_hash` 可反查 |

> 说明：真实 Java 后端 + MySQL + Python 服务的端到端并发基线尚未采集
> （见 `docs/PERFORMANCE.md`，需部署环境）。上表中 RAG/TTS/上传等
> Python 侧结论均为本机真实启动服务后的实测输出。

---

## 1. 验证环境

| 项 | 版本 |
|---|---|
| OS | Debian (Linux) |
| JDK | OpenJDK 21.0.11 |
| Maven | 3.9.16（本地安装，阿里云镜像） |
| Python | 3.13.5 |
| Node.js | v24.21.0 / npm 11.19.0 |
| MySQL | 8.x（宿主服务，本报告使用 H2 内存库做集成测试） |
| LLM | CodeBuddy 本地代理 `http://127.0.0.1:3800/v1`，模型 `deepseek-v4-flash` |

> 说明：本次验证使用 CodeBuddy 代理替代真实厂商 API Key 完成 AI 链路测试，
> 生产环境只需将 `LLM_PROVIDER` 切回 `deepseek`/`openai`/`qwen` 并配置对应 Key。

---

## 2. 验证结果总览

| 模块 | 验证项 | 结果 |
|---|---|---|
| Python AI | 单元测试 | ✅ **35 passed**（本轮 +4 回归）|
| Python AI | 服务启动 + 自动建库 | ✅ 3 个 collection 自动构建成功 |
| Python AI | 三大智能体构建 | ✅ 工具数 4 / 2 / 3 |
| Python AI | 真实对话（CodeBuddy） | ✅ 三方向均返回专业回复 |
| Python AI | TTS 语音合成 | ✅ 返回 18,288 字节有效 MP3（本轮恢复 edge-tts 通道）|
| Python AI | RAG 检索 + 来源归属 | ✅ 返回文档片段与文件名来源 |
| Python AI | 集合隔离 | ✅ 三库各自命中，无串库 |
| Java 后端 | 编译 | ✅ `mvn compile` 成功（76 个类） |
| Java 后端 | 集成测试（H2） | ✅ **16 passed** |
| Java 后端 | Java→Python 联调 | ✅ **5 passed** |
| Java 后端 | 全量测试一起跑 | ✅ **43 run / 0 fail**（38 执行 + 5 联调跳过）|
| Java 后端 | API 覆盖（附件一 §3） | ✅ **20/20** |
| Vue 前端 | 依赖安装 | ✅ npm install 成功 |
| Vue 前端 | 生产构建 | ✅ `vite build` 成功（9.72s） |
| 微信小程序 | JS 语法 | ✅ 全部通过 `node --check` |
| 微信小程序 | 页面/图标完整性 | ✅ 8 页 + 6 图标，无缺失 |
| 微信小程序 | API 路径有效性 | ✅ 全部对应真实后端接口 |
| 微信小程序 | 适老化字号 | ✅ 无低于 32rpx 的字号 |
| 部署 | docker-compose YAML | ✅ 语法正确，4 个服务 |
| 部署 | 密钥泄露 | ✅ 已轮换，未进入 git 历史 |

---

## 3. Python AI 服务验证

### 3.1 单元测试

```
$ cd python && PYTHONPATH=.pylibs:. python3 -m pytest tests/ -q
31 passed, 7 warnings in 0.45s
```

覆盖：知识库加载/切分/查询、Agent 框架、台账生成、用药安全、身份证脱敏与校验。

### 3.2 服务健康与自动建库

清空 `knowledge_base/chroma_db/` 后启动服务：

```json
{"status":"ok","service":"zhiban-ai-agent","version":"1.1.0",
 "llmProvider":"codebuddy",
 "collections":["govpolicy","elderly","tourism"],"loaded":[]}
```

启动日志显示自动构建：
```
自动构建知识库: collection=govpolicy ...
知识库构建完成: collection=govpolicy, chunks=4
自动构建知识库: collection=elderly ...
知识库构建完成: collection=elderly, chunks=4
自动构建知识库: collection=tourism ...
知识库构建完成: collection=tourism, chunks=4
```

### 3.3 三大智能体构建（附件一 §6.2-6.4）

```
[tourism]   built OK, tools=3     ← 景点导览/路线规划/文化故事
[govpolicy] built OK, tools=2     ← 政策检索/培训台账
[elderly]   built OK, tools=4     ← 用药指导/护理建议/康复计划/长护险
```

### 3.4 真实对话（附件一 §6.5 合规性）

**康养智能体** — 请求：`高血压老人饮食要注意什么？一句话`

> 一句话：**少盐少油，每天食盐不超过5克（约一啤酒瓶盖），多吃新鲜蔬果和全谷物，少吃腌制品和加工肉。**
>
> ⚠️ 以上建议仅供参考，具体请遵医嘱。若出现剧烈头痛、视物模糊、胸痛等，请立即拨打120。

✅ 同时包含**医疗免责声明**与**紧急信号提醒（120）**，符合 §6.5。

**文旅智能体** — 请求：`西湖有哪些看点？简单说两句`

> 西湖的看点可不少…苏堤春晓、断桥残雪、三潭印月、雷峰夕照、花港观鱼…
> **老人优惠**：65岁以上凭身份证，部分景点可享优惠或免费…

✅ 主动关注老年人出行需求，符合 §6.5。

### 3.5 TTS 语音合成（附件一 §3.3）

```
$ curl -X POST .../api/v1/tts -d '{"text":"您好，我是知伴AI助手"}'
HTTP 200  size=18720

$ file tts.mp3
MPEG ADTS, layer III, v2, 48 kbps, 24 kHz, Monaural
```

✅ 返回真实可播放 MP3。

### 3.6 RAG 检索与集合隔离（附件一 §7）

同一查询词 `政策 养老` 分别请求三个集合：

| collection | 命中数 | 来源文件 |
|---|---|---|
| govpolicy | 1 | 银发经济政策.txt |
| elderly | 1 | hypertension.txt |
| tourism | 1 | 主要景点导览.txt |

✅ **集合完全隔离**，且返回结果含来源文件名（§6.3 可追溯性要求）。

---

## 4. Java 后端验证

### 4.1 编译

```
$ mvn -DskipTests compile
BUILD SUCCESS
编译产物：76 个 class
```

### 4.2 集成测试（16 项，H2 内存库）

覆盖附件一 §3.1 / §3.4 / §3.5 / §10.3：

| 测试 | 验证内容 | 结果 |
|---|---|---|
| `guestLoginReturnsToken` | 游客登录返回三段式 JWT、`guest_` 前缀用户名 | ✅ |
| `userInfoRequiresAuth` | 未带 Token 访问 → 401/403 | ✅ |
| `userInfoReturnsMaskedPhone` | 带 Token 可获取信息，`guest=true` | ✅ |
| `refreshIssuesNewToken` | 刷新返回新 Token，`expiresIn=86400000` | ✅ |
| `refreshRejectsInvalidToken` | 无效 Token → code 401 | ✅ |
| `personaDefaultsToElderly` | 人设默认康养，含 greeting | ✅ |
| `allThreeAgentsAvailable` | 三大智能体人设均可获取 | ✅ |
| `switchAgentReturnsPersona` | 切换到文旅返回目标人设 | ✅ |
| `switchUnknownAgentRejected` | 未知智能体 → 400 | ✅ |
| `agentListHasThreeEntries` | 智能体列表返回 3 项 | ✅ |
| `contentListsArePublic` | 文章/政策列表公开可访问 | ✅ |
| `categoriesArePublic` | 分类接口公开 | ✅ |
| `chatRequiresAuth` | 对话接口未认证被拦截 | ✅ |
| `sessionsRequireAuth` | 会话列表未认证被拦截 | ✅ |
| `createAndListSession` | 创建会话 → 列表可见 → 历史可查 | ✅ |
| `cannotAccessOthersSession` | **跨用户访问会话 → 403**（越权防护） | ✅ |

### 4.3 Java → Python 真实联调（5 项）

```
$ mvn -Dtest=AiServiceLiveTest -Dai.live=true test
Tests run: 5, Failures: 0, Errors: 0
```

| 测试 | 验证内容 | 结果 |
|---|---|---|
| `health` | AI 服务健康检查 | ✅ |
| `chatWithAllAgents` | 三大智能体均返回非空回复 | ✅ |
| `multiTurnContext` | 多轮对话携带上下文 | ✅ |
| `ttsReturnsAudio` | 返回内容为有效 MP3（校验帧头） | ✅ |
| `speakers` | 发音人列表含当前选中项 | ✅ |

### 4.4 全量测试

```
$ mvn -Dai.live=true test
Tests run: 5,  Failures: 0, Errors: 0   -- AiServiceLiveTest
Tests run: 16, Failures: 0, Errors: 0   -- AuthAndAgentIntegrationTest
Tests run: 21, Failures: 0, Errors: 0
BUILD SUCCESS
```

### 4.5 API 覆盖

附件一 §3 要求的 20 个接口：**20/20 全部实现**（脚本逐项核对注解）。

---

## 5. 前端验证

### 5.1 Vue 3 Web

```
$ npm install        → 成功
$ npm run build      → ✓ built in 9.72s
```

产物：13 个视图分包，主包 gzip 后约 405 KB。

### 5.2 微信小程序

```
$ node --check 全部 .js        → 全部通过
$ app.json 页面存在性校验       → 8/8 存在
$ tabBar 图标存在性校验         → 6/6 存在
$ API 路径 vs 后端接口          → 全部匹配
$ font-size < 32rpx 检查        → 0 处（适老化达标）
```

---

## 6. 验证中发现并修复的缺陷

验证过程**主动暴露了 10 个缺陷**，其中 2 个为致命级：

### 致命 1：Spring Security 规则全部失效

`SecurityConfig` 中的 `requestMatchers` 写的是 `/api/auth/login` 等带前缀路径，
但 `server.servlet.context-path=/api` 会由 Servlet 容器**剥离前缀**再做匹配。
结果：**所有放行规则都不生效，连登录接口都返回 403，系统完全不可用**。

修复：改为无前缀路径（`/auth/login` 等），并用测试锁定行为。

### 致命 2：小程序三个接口调用不存在的后端路径

`/help/medication/guide`、`/help/tourism/attractions`、`/auth/wx-login`
在 A 包后端均不存在 → 用药指导、文旅导览、登录功能全部不可用。

修复：统一改走 `/chat/send`（按 `agentType` 路由）与 `/auth/guest-login`。

其余 8 个缺陷（Page 导入错误、`_get_chroma_path` 缺失、12 处 KB 签名不符、
collection 串库、返回值类型不符、图标缺失、详情页未声明、密钥泄露）详见 `REQUIREMENTS.md`。

---

## 6.1 第二轮复验中发现并修复的缺陷（14 项）

第二轮在核验需求覆盖时，对每一处「文档说已实现」的结论都做了实测复核，
额外暴露 14 个既有缺陷。其中 5 个属功能性阻断（用户可见的失败）：

**功能性阻断**

| # | 缺陷 | 影响 | 实测证据 |
|---|---|---|---|
| 1 | `user` 表默认管理员 BCrypt 哈希与 `admin123` 不匹配 | 内置管理员**无法登录**，管理端完全不可用 | `BCryptPasswordEncoder.matches()` = false（修复后 true）|
| 2 | 全站列表页传 `page=0`，后端 `@Min(1)` | 文章/政策列表与管理页**首页请求 400** | 4 个视图均用 `currentPage - 1` |
| 3 | 前端政策字段名与后端 DTO 错位 | 管理端**新建政策必定 400**（`policyType` 为 `@NotBlank`）| 前端传 `documentNumber`/`category`/`content`，DTO 为 `docNumber`/`policyType`/`fullText` |
| 4 | 新建文章无发布开关，`isPublished` 默认 0 | 新建文章恒为草稿，**用户端不可见** | 用户端列表只查 `is_published = 1` |
| 5 | TTS 被改为未实现桩（工作区回归）| §3.3 TTS **返回 501** | 本轮恢复 edge-tts，实测返回 18,288 字节 MP3 |

**检索链路（导致政策问答答非所问）**

| # | 缺陷 | 影响 |
|---|---|---|
| 6 | 向量检索 `score` 恒为 0（元数据无 score；且 Chroma 返回的是**距离**而非相似度）| 阈值 `>=0.75` 永不通过，政策问答**静默降级为关键词检索** |
| 7 | Java 按 `policy_type` 过滤，但知识库元数据只有 `source`/`category` | 带类型筛选时**结果被全部丢弃** |
| 8 | 关键词兜底用**整个问题**做 LIKE | 兜底检索**几乎永不命中** |
| 9 | 知识库重建前未清 Chroma System 缓存 | **第二次重建必定失败**（readonly database）|
| 10 | `gov_policy_document` 无种子数据、`vector_id` 从不写入 | 向量命中后**回查数据库为空** |

**接口与配置**

| # | 缺陷 | 影响 |
|---|---|---|
| 11 | 上传接口 `collection`/`rebuild` 未用 `Form(...)` 声明 | multipart 字段被忽略，**文件落入错误集合** |
| 12 | `application.yml` 未配置 multipart | 声明 5MB/10MB 实际上限 1MB，超限报 **500 而非 400** |
| 13 | `SecurityConfig` 放行 `/actuator/health` 但未引入 actuator | 死规则，实际 404（已补 `HealthController`）|
| 14 | 音频/SSE 用裸 URL 无法带 Token | TTS 播报与 SSE 流式**均 401**（已支持查询参数 token）|

---

## 6.2 第三轮实跑验证（"能不能跑起来"）

前两轮只证明「测试通过」，未证明「服务真能起来并跑通」。第三轮实际启动全部服务实测：

| # | 实跑项 | 命令/方式 | 结果 |
|---|---|---|---|
| 1 | Java 后端启动 | `java -cp <deps> com.zhiban.ai.ZhibanApplication`（H2 profile）| ✅ 8080 启动，`/api/health` 返回 `aiService: up` |
| 2 | 管理员登录 | `POST /api/auth/login` admin/admin123 | ✅ code 200，role=ADMIN |
| 3 | 规范路径 | `GET /api/articles`、`/api/policies` | ✅ 200，政策返回 8 条种子数据 |
| 4 | 文章创建+可见 | 建文章(`isPublished=1`) → 用户端列表 | ✅ 用户端 total=1 可见 |
| 5 | 配额查询/调整 | `GET /api/quota`、`PUT /api/admin/quota/...` | ✅ 调整后 500/5/495/20 |
| 6 | 政策问答(RAG) | `POST /api/policies/ask` | ✅ 命中「长期护理保险政策」并带来源 |
| 7 | 对话(真实 LLM) | `POST /api/chat/send` | ✅ 返回专业回复 + 免责声明 + 120 提示 |
| 8 | SSE 流式 | `POST /api/chat/send/stream?token=...` | ✅ session/delta 事件正常，查询参数鉴权生效 |
| 9 | WebSocket | `GET /api/ws/chat` 握手 | ✅ HTTP 101 Switching Protocols |
| 10 | TTS | `GET /api/voice/tts?token=...` | ✅ 11,232 字节真实 MP3 |
| 11 | Python 上传接口 | `POST /api/v1/kb/upload` | ✅ 文件落盘到指定集合 |
| 12 | 向量真实分数 | `POST /api/v1/search` | ✅ sim=0.2597（非 0）|
| 13 | 前端构建产物 | 静态服务器托管 dist | ✅ 页面与 1.25MB 主包正常 |
| 14 | **生产链路 nginx** | 真实 nginx 加载 `nginx.conf` | ✅ 页面 200、`/api/` 代理 200、SPA 回退 200、安全头齐全 |
| 15 | **HTTPS/TLS** | 真实 nginx 加载 `nginx.https.conf` + 自签证书 | ✅ 301 跳转、TLS 握手、HSTS、healthz 200 |

### 6.2.1 第三轮新发现的缺陷（第 15 项）

| # | 缺陷 | 影响 | 实测证据 |
|---|---|---|---|
| 15 | `vite.config.js` 的 proxy 用 `rewrite: p => p.replace(/^\/api/, '')` 剥离 `/api` 前缀，但后端 `context-path=/api` | **开发环境所有接口 404**，前端完全无法联调 | 代理请求 `/api/health` 返回 Tomcat 404；直连 `/api/health` 返回 200。nginx 的 `proxy_pass .../api/` 保留前缀，二者行为不一致。已改为不 rewrite |

### 6.2.2 环境限制（如实说明）

- **Docker daemon 不可访问**（`permission denied ... /var/run/docker.sock`），
  故 `docker compose up` 未实测；compose 配置仅做了 `config -q` 解析校验。
- **MySQL 密码不匹配**：`.env.docker` 中的 `DB_PASSWORD` 无法连接本机 3306
  （宝塔面板实例，凭据不在可读范围内），故实跑使用 H2 内存库 + `schema-h2.sql`。
  生产首次部署需按 `DEPLOYMENT.md` 初始化 MySQL 并注入正确密码。
- 本机 8081 端口存在一个**会话前启动的旧版 Python 实例**（无 `/kb/upload`），
  实跑验证使用新实例（8097）确认新代码可用。

---

## 7. 未覆盖项（需生产环境验证）

| 项 | 原因 | 建议 |
|---|---|---|
| BGE 语义检索质量 | 验证环境无法访问 HuggingFace，使用 `hash` 兜底验证链路（本轮已修复分数换算与阈值逻辑，链路语义正确）| 生产环境预置 BGE 模型 |
| 真实后端并发基线 | 需部署 MySQL + Python 服务 | 按 `docs/PERFORMANCE.md` §4 复跑 |
| ASR 识别准确率 ≥90% | 需安装 `faster-whisper` 或配置阿里云 NLS | 部署后按 §10.1 实测 |
| 50 并发压测 | 需独立压测环境 | 用 JMeter/wrk 按 §10.2 验证 |
| HTTPS 传输加密 | 需域名与证书 | Nginx 配置 443 |
| 单次对话 ≤3 秒 | 取决于 LLM 供应商响应速度 | 选用低延迟模型或加缓存 |

---

## 8. 复现命令

```bash
# Python 单元测试
cd python
PYTHONPATH=.pylibs:. python3 -m pytest tests/ -q

# 启动 AI 服务（开发，用 CodeBuddy 代理）
cd python
LLM_PROVIDER=codebuddy \
CODEBUDDY_API_KEY=<key> \
CODEBUDDY_BASE_URL=http://127.0.0.1:3800/v1 \
EMBEDDING_PROVIDER=hash \
PYTHONPATH=.pylibs:. python3 rag_server.py

# Java 全量测试（含 Java→Python 联调）
cd java-backend
mvn -Dai.live=true test

# 仅静态集成测试（不需要 Python 服务）
mvn test

# 前端构建
cd vue-frontend && npm install && npm run build

# 小程序语法与完整性
cd wechat-miniprogram
for f in $(find . -name "*.js"); do node --check "$f" || exit 1; done

# 知识库重建（21 篇语料）
cd python
EMBEDDING_PROVIDER=hash PYTHONPATH=.pylibs:. python3 -c "
import config
from knowledge_base.build_kb import build_knowledge_base
for name, attr in [('govpolicy','KB_POLICY_DIR'),('elderly','KB_ELDERLY_DIR'),('tourism','KB_TOURISM_DIR')]:
    build_knowledge_base(docs_dir=getattr(config, attr), collection_name=name,
                         persist_dir=config.KB_CHROMA_DIR / name, rebuild=True)
"

# 并发压测（需先关闭限流，否则 429 会被误判为性能问题）
RATE_LIMIT_ENABLED=false mvn spring-boot:run &
python3 scripts/loadtest/load_test.py --base-url http://localhost:8080 --concurrency 50 --duration 30 --scenario mixed

# HTTPS 部署（可选叠加层）
bash scripts/gen-self-signed-cert.sh -d your-domain.com
docker compose -f docker-compose.yml -f docker-compose.https.yml up -d
```
