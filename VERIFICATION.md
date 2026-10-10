# 验证报告（Verification Report）

> 项目：知伴AI双端智能体APP
> 验证时间：2026-10-10
> 验证方式：编译 + 单元测试 + 集成测试 + 真实联调

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
| Python AI | 单元测试 | ✅ **31 passed** |
| Python AI | 服务启动 + 自动建库 | ✅ 3 个 collection 自动构建成功 |
| Python AI | 三大智能体构建 | ✅ 工具数 4 / 2 / 3 |
| Python AI | 真实对话（CodeBuddy） | ✅ 三方向均返回专业回复 |
| Python AI | TTS 语音合成 | ✅ 返回 18,720 字节有效 MP3 |
| Python AI | RAG 检索 + 来源归属 | ✅ 返回文档片段与文件名来源 |
| Python AI | 集合隔离 | ✅ 三库各自命中，无串库 |
| Java 后端 | 编译 | ✅ `mvn compile` 成功（76 个类） |
| Java 后端 | 集成测试（H2） | ✅ **16 passed** |
| Java 后端 | Java→Python 联调 | ✅ **5 passed** |
| Java 后端 | 全量测试一起跑 | ✅ **21 passed** |
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

## 7. 未覆盖项（需生产环境验证）

| 项 | 原因 | 建议 |
|---|---|---|
| BGE 语义检索质量 | 验证环境无法访问 HuggingFace，使用 `hash` 兜底验证链路 | 生产环境预置 BGE 模型 |
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
```
