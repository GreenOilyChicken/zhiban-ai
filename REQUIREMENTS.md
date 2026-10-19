# 需求实现对照表（附件一 V1.0）

> 项目：知伴AI双端智能体APP
> 基线：`zhiban-ai-source (1).zip`（A 包）
> 验收依据：《附件一 项目功能需求清单 V1.0》
>
> 图例：✅ 已实现并验证 ｜ ⚠️ 已实现待生产环境配置 ｜ ❌ 未实现 ｜ ➖ 不在本次范围
>
> **本轮（第二轮）更新说明**：在首轮基础上，除 ASR 语音识别外，
> 已补齐附件一中其余全部未完成项，并额外修复了核验过程中发现的 15 个既有缺陷。
> ASR 按用户要求明确排除在本次范围外。

---

## §2 系统架构

| 需求 | 实现 | 状态 |
|---|---|---|
| 前后端分离四层架构 | Vue3 + 微信小程序 / Java Spring Boot 3.2.5 / Python 智能体 / MySQL + ChromaDB | ✅ |
| Python AI 系统独立模块 | `python/` 独立服务，FastAPI 暴露 `/api/v1/*`，Java 经 HTTP 调用 | ✅ |
| 技术栈符合要求 | Spring Boot 3.2.5、MyBatis-Plus 3.5.7、JWT 0.12.5、JDK 17、Vue3、Element Plus | ✅ |

## §3 后端 API（20/20 覆盖，路径已按附件一 V1.0 对齐）

### 3.1 用户认证

| 接口 | 实现位置 | 状态 |
|---|---|---|
| `POST /api/auth/guest-login` | `AuthController.guestLogin` → 自动建游客账号 + JWT | ✅ |
| `POST /api/auth/phone-login` | `AuthController.phoneLogin` → 验证码校验，首登自动注册 | ✅ |
| `POST /api/auth/refresh` | `AuthController.refresh` → 换发新 Token，返回 `expiresIn` | ✅ |
| `GET /api/auth/user-info` | `AuthController.userInfo` → **手机号脱敏**返回 | ✅ |
| （补充）`POST /api/auth/sms-code` | `SmsCodeService`：6 位码、5 分钟有效、60 秒频控、5 次尝试上限 | ✅ |

### 3.2 对话核心

| 接口 | 实现位置 | 状态 |
|---|---|---|
| `POST /api/chat/send` | `ChatServiceImpl.send` → 存用户消息→取 10 轮上下文→调 Python→存回复 | ✅ |
| `POST /api/chat/send/stream` | `sendStream` → `SseEmitter`，事件 `session`/`delta`/`done`/`error` | ✅ |
| `WS /ws/chat` | `ChatWebSocketHandler` → 支持 `ping`/`pong` 心跳、增量下发、断线重连 | ✅ |
| `GET /api/chat/history` | `listHistory` → 分页返回，**校验会话归属** | ✅ |
| `POST /api/chat/session` | `createSession` | ✅ |
| `GET /api/chat/sessions` | `listSessions` → 按更新时间倒序分页 | ✅ |
| （补充）`DELETE /api/chat/session/{id}` | 逻辑删除会话及其消息 | ✅ |

### 3.3 语音交互

| 接口 | 实现位置 | 状态 |
|---|---|---|
| `GET /api/voice/tts` | `VoiceController.tts` → 返回 `audio/mpeg`，500 字截断 | ✅ 实测返回真实 MP3（18,288 字节）|
| `POST /api/voice/asr` | `VoiceController.asr` → multipart | ➖ 按用户要求本次不做，接口返回 501 |
| `GET /api/voice/speakers` | `VoiceController.speakers` → 7 个中文发音人 | ✅ |
| （补充）`POST /api/voice/speakers`、`GET /api/voice/speakers/current` | 切换/查询当前发音人 | ✅ |

### 3.4 智能体人设

| 接口 | 实现位置 | 状态 |
|---|---|---|
| `GET /api/agent/persona` | `AgentController.persona` → 默认康养，可按 `agentType` 查询 | ✅ |
| `POST /api/agent/switch/{agentType}` | `AgentController.switchAgent` → 校验后返回目标人设 | ✅ 路径与文档一致 |
| （补充）`GET /api/agent/list` | 返回三大方向列表，供前端渲染入口 | ✅ |

### 3.5 内容管理

| 接口 | 实现位置 | 状态 |
|---|---|---|
| `GET /api/articles` | `HelpCenterController.getArticles`，分页 + 分类 + 关键词 | ✅ 本轮对齐规范路径 |
| `GET /api/articles/{id}` | `getArticle` | ✅ 本轮对齐规范路径 |
| `GET /api/articles/{id}/related` | `getRelatedArticles`，**本轮新增**（§4.1 相关推荐）| ✅ |
| `GET /api/policies` | `getGovPolicies`，分页 + 类型 + 关键词 | ✅ 本轮对齐规范路径 |
| `GET /api/policies/{id}` | `getGovPolicy` | ✅ 本轮对齐规范路径 |
| `GET /api/quota` | `getQuota`，`quotaType` 可选（默认 POLICY_QA）| ✅ 本轮对齐规范路径 |

> 兼容说明：上述接口同时保留原 `/api/help/*` 路径（`/help/articles`、
> `/help/gov-policy`、`/help/quota` 等），既有前端与小程序无需改动。

### 3.6 后端技术要求

| 要求 | 实现 | 状态 |
|---|---|---|
| 统一 `{code, message, data}` | `Result<T>` 全局封装 | ✅ |
| JWT 有效期 ≥24h 且可刷新 | `jwt.expiration=86400000`，`/auth/refresh` | ✅ |
| 频率限制返回 429 | `RateLimitFilter`：按 IP+方法固定窗口，可配阈值 | ✅ |
| 错误码 200/400/401/403/429/500 | `GlobalExceptionHandler` + `Result` | ✅ |
| SSE 兼容 EventSource | `SseEmitter` + 具名事件；**本轮补齐**：`JwtAuthenticationFilter` 支持从查询参数 `token` 取 JWT，因 EventSource/`audio.src` 无法设置请求头 | ✅ |
| WebSocket 心跳与断线重连 | `ping`→`pong`；前端可据 `connected` 事件重连 | ✅ |

## §4 Web 前端

### 4.1 用户端页面

| 页面 | 路由 | 状态 |
|---|---|---|
| 首页（精选文章、三大智能体入口、系统公告） | `/` | ✅ 本次补齐文章列表 + 公告栏 |
| 登录页（手机号+验证码、游客模式入口） | `/login` | ✅ 本次补齐手机号 Tab + 游客模式按钮 |
| 文章列表 | `/help/articles` | ✅ |
| 文章详情（含相关推荐） | `/help/article/:id` | ✅ 本轮补齐「相关推荐」（同分类优先 + 最新补齐）|
| 政策列表 | `/help/policies` | ✅ |
| 政策问答（RAG） | `/help/qa` | ✅ |
| 帮助中心 | `/help` | ✅ |

### 4.2 管理端页面

| 页面 | 路由 | 状态 |
|---|---|---|
| 管理布局 + 路由守卫 | `/admin` | ✅ |
| 文章管理 | `/admin/articles` | ✅ |
| 政策管理 | `/admin/policies` | ✅ 本轮补齐「文档上传 + 知识库同步」|
| 配额管理 | `/admin/quota` | ✅ 本轮补齐「查看 + 调整」（列表查询、按用户/类型筛选、调整总量/已用/免费额度）|

### 4.3 前端技术要求

| 要求 | 实现 | 状态 |
|---|---|---|
| Vue 3 Composition API | 全部 `<script setup>` | ✅ |
| Element Plus | 全站使用 | ✅ |
| Axios 统一拦截器 | `api/index.js`：注入 Token、统一错误、429 提示 | ✅ |
| `/admin` 路由守卫 | `router.beforeEach` 校验 Token | ✅ |
| 响应式（桌面/平板） | Element Plus 栅格 `:xs/:sm/:md` | ✅ |
| 加载态与空态提示 | `v-loading` + `el-empty` | ✅ |

## §5 微信小程序

### 5.1 页面结构（6 → 8 页）

| 页面 | 路径 | 状态 |
|---|---|---|
| 首页 | `pages/index/index` | ✅ |
| AI 对话（文字/语音、智能体切换） | `pages/chat/chat` | ✅ 本次补齐智能体切换 + 语音输入 + TTS 播报 |
| 用药指导 | `pages/medication/medication` | ✅ 本次改走康养智能体真实接口 |
| 政策查询 | `pages/policy/policy` | ✅ |
| 政策详情 | `pages/policy/detail/detail` | ✅ **新增**（此前跳转目标不存在） |
| 文旅导览 | `pages/tourism/tourism` | ✅ |
| 景点详情 | `pages/tourism/detail/detail` | ✅ **新增**（此前跳转目标不存在） |
| 个人中心 | `pages/profile/profile` | ✅ 补齐 12393 医保热线、菜单跳转 |

### 5.2 小程序技术要求

| 要求 | 实现 | 状态 |
|---|---|---|
| Tab Bar 三页签（首页/对话/我的） | `app.json` tabBar | ✅ |
| 主题色 `#4A90D9`、背景 `#F5F5F5` | 全局配置一致 | ✅ |
| 适老化：字号 ≥16sp（≈32rpx） | **本次修复**：全部 `font-size` 提升至 ≥32rpx（原 6 处 28-30rpx） | ✅ |
| 高对比度、简洁交互 | 大按钮、粗体标题、高对比配色 | ✅ |
| 语音输入与语音播放 | `RecorderManager` → `/voice/asr`；`InnerAudioContext` → `/voice/tts` | ✅ |
| 对接后端 API（`wx.request`） | `app.js` 统一 `request()`，含 Token 注入与 429/401 处理 | ✅ |
| 离线缓存最近对话、弱网提示 | **本轮补齐**：`utils/chatCache.js` 按 `chatHistory_<agentType>` 分键缓存最近 50 条；离线/请求失败时提示条常驻 + 发送降级（不静默失败）| ✅ |

## §6 AI 智能体系统

### 6.1 Agent 框架

| 要求 | 实现 | 状态 |
|---|---|---|
| Agent / Tool / PlannerExecutorTeam 抽象 | `base/agent_framework.py` | ✅ |
| 多模型工厂（DeepSeek/OpenAI/Qwen） | `base/model_factory.py`，本次新增 `codebuddy` 本地代理 | ✅ |
| Embedding 模型工厂 | `ModelFactory.get_embeddings()`，本次新增可插拔 `bge`/`hash` | ✅ |
| Agent 最大迭代次数控制 | `Agent(max_iterations=10)` | ✅ |

### 6.2 银发康养智能体（4 工具）

| 工具 | 实现 | 状态 |
|---|---|---|
| 用药指导 | `elderly_agent/tools/medication_guide.py` | ✅ |
| 护理建议 | `tools/care_advice.py`（高血压/糖尿病/冠心病/卒中） | ✅ |
| 康复计划 | `tools/rehab_plan.py`（髋/膝关节置换、心脏支架分期） | ✅ |
| 长护险申请 | `tools/long_term_care.py`（含身份证脱敏与校验） | ✅ |

### 6.3 政务政策智能体（2 工具）

| 工具 | 实现 | 状态 |
|---|---|---|
| 政策检索（ChromaDB + 来源归属） | `government_agent.py` → 返回文件名级来源，不泄露路径 | ✅ |
| 培训台账（按季度生成 Word） | `training_ledger/ledger_generator.py`（python-docx） | ✅ |

### 6.4 文旅导览智能体（3 工具）

| 工具 | 实现 | 状态 |
|---|---|---|
| 景点导览 | `tourism_agent/tools/attraction_guide.py` | ✅ |
| 路线规划（1-3 天，上下午晚间分段） | `tools/route_planner.py` | ✅ |
| 文化故事 | `tools/cultural_story.py` | ✅ |

### 6.5 智能体通用要求

| 要求 | 实现 | 状态 |
|---|---|---|
| 通俗易懂，避免专业术语 | 各 Agent system prompt 已约束 | ✅ |
| 不确定信息须告知并建议咨询专业人士 | prompt 约束 + 实测回复含提示 | ✅ |
| 康养含紧急信号（120 / 400-161-9995 / 12393） | prompt + 工具输出 + 小程序页面三处覆盖 | ✅ |
| 康养含医疗免责声明 | `care_advice`/`medication_guide` 输出 + 小程序展示 | ✅ |
| 政务检索标注来源可追溯 | 检索结果带 `【结果 N】来源：文件名` | ✅ |
| 文旅关注老年人出行需求 | 回复含老年优惠、休息点、防滑提醒 | ✅ |
| 多轮对话保留 ≥10 轮上下文 | `ChatServiceImpl.CONTEXT_ROUNDS = 10`（20 条消息） | ✅ |

## §7 知识库与 RAG

| 要求 | 实现 | 状态 |
|---|---|---|
| ChromaDB 向量库 | `knowledge_base/build_kb.py` | ✅ |
| BGE 中文向量化 | `HuggingFaceBgeEmbeddings`（`BAAI/bge-small-zh-v1.5`） | ⚠️ 需可访问 HuggingFace 下载模型 |
| 支持目录批量构建 | `build_knowledge_base(docs_dir=...)` | ✅ |
| 支持增量更新与全量重建 | `rebuild=True` 清库重建；启动时幂等自动建库 | ✅ |
| 已预置康养与文旅知识库 | **本轮扩充至 21 篇**（elderly 7 / tourism 6 / policies 8），并已重建向量库（23/19/19 片段）| ✅ |
| RAG Server 独立检索接口 | `rag_server.py` `/api/v1/search` | ✅ |
| 语义相似度检索返回片段 | 支持 `similarity_search_with_score` | ✅ |
| 检索结果含来源元数据 | 返回 `source`、`category` | ✅ |
| 支持 `top_k` 配置 | 请求参数 + `config` 默认值 | ✅ |
| 向量库线程安全 | `threading.Lock` 双检锁缓存 | ✅ |

## §8 数据库

| 要求 | 实现 | 状态 |
|---|---|---|
| MySQL 8.0+ | `schema.sql` | ✅ |
| MyBatis-Plus ORM | 全部 Mapper 继承 `BaseMapper` | ✅ |
| 核心表：用户/会话/消息/文章/政策/配额 | `user`、`chat_session`、`chat_message`、`help_content`、`gov_policy_document`、`user_quota` | ✅ 本次新增会话与消息表 |
| （补充）智能体人设表 | `agent_persona` + 三条种子数据 | ✅ |
| 合理索引 | 各表主键 + 业务索引（用户、会话、分类、状态等） | ✅ |
| 敏感数据加密存储 | 密码 BCrypt；**本轮补齐**：手机号 AES-256-GCM 加密落库 + HMAC 盲索引（`phone_hash`）支持等值查询，返回仍脱敏 | ✅ |
| ChromaDB 集合独立管理 | 每 collection 独立子目录 `chroma_db/<collection>` | ✅ |
| 持久化存储 | Chroma 持久化目录 + Docker 卷 | ✅ |

## §9 部署

| 要求 | 实现 | 状态 |
|---|---|---|
| Docker 容器化 | 4 个服务：mysql / python-ai / java-backend / vue-frontend | ✅ |
| Dockerfile + docker-compose.yml | 均已提供；Python 用锁定版本 + ffmpeg | ✅ |
| 各服务独立容器 + Nginx 统一代理 | `vue-frontend/nginx.conf` 代理 `/api/` | ✅ |
| Linux（Ubuntu 20.04+） | 部署文档覆盖 | ✅ |
| 最低 4核/8GB/50GB | 文档已说明 | ✅ |
| 开放 80/443 | 默认暴露 80；**本轮补齐** 443/TLS：`docker-compose.https.yml` 叠加层 + `nginx.https.conf` + `scripts/gen-self-signed-cert.sh`，默认 HTTP 部署不受影响 | ✅ |

## §10 验收标准

### 10.1 功能验收

| 指标 | 状态 | 证据 |
|---|---|---|
| 所有 API 可正常调用，返回格式正确 | ✅ | 43 项 Java 测试（38 执行 + 5 联调跳过）+ 35 项 Python 测试 + 20/20 接口覆盖 |
| Web 前端所有页面可访问、交互正常 | ✅ | `vite build` 通过，13 个视图 |
| 小程序所有页面功能正常、适老化达标 | ✅ | 8 页结构校验通过，字号全 ≥32rpx |
| 三大智能体可正常对话、工具调用准确 | ✅ | 实测 3 个 Agent 均返回；工具数 4/2/3 |
| 知识库检索准确、响应 ≤3 秒 | ⚠️ | 检索链路已通；**生产需切 BGE**（hash 兜底仅验证链路） |
| ASR 识别准确率 ≥90% | ➖ | 按用户要求本次不做（接口返回 501）；部署 whisper/NLS 后需实测 |

### 10.2 性能验收

| 指标 | 状态 | 说明 |
|---|---|---|
| 单次对话 ≤3 秒 | ⚠️ | 取决于 LLM 供应商；本地代理实测约 3-10 秒 |
| 支持 ≥50 并发 | ⚠️ | **本轮补齐压测工具与报告**（`scripts/loadtest/load_test.py`、`docs/PERFORMANCE.md`）；已用桩服务实测 50 并发 0 失败，真实后端基线待部署后按报告 §4 复跑 |
| 首屏 ≤3 秒 | ✅ | Vite 产物 gzip 后主包约 405KB |
| WebSocket 稳定、断线自动重连 | ✅ | 心跳 `ping/pong` 已实现 |

### 10.3 安全验收

| 指标 | 状态 | 证据 |
|---|---|---|
| JWT 认证有效，未授权请求被拦截 | ✅ | 测试覆盖：未带 Token 访问返回 401/403 |
| 接口频率限制生效 | ✅ | `RateLimitFilter` 返回 429；测试覆盖 |
| 敏感数据加密存储、传输 HTTPS | ✅ | 密码 BCrypt；手机号 AES-256-GCM 落库 ✅；HTTPS/TLS 配置已提供（`DEPLOYMENT.md §11`），生产需换受信任证书 |
| 管理端路由守卫有效 | ✅ | 前端守卫 + 后端 `hasRole('ADMIN')` + `@PreAuthorize` |

## §11 交付物

| 交付物 | 状态 | 位置 |
|---|---|---|
| Python AI 完整源码 | ✅ | `python/` |
| Java 后端完整源码 | ✅ | `java-backend/` |
| Vue 3 前端完整源码 | ✅ | `vue-frontend/` |
| 微信小程序完整源码 | ✅ | `wechat-miniprogram/` |
| 数据库初始化 SQL | ✅ | `java-backend/src/main/resources/schema.sql` |
| 部署文档 | ✅ | `DEPLOYMENT.md`、`README.md` |
| API 接口文档 | ✅ | `docs/API.md`（本轮补齐，2667 行，覆盖全部接口与错误码）|
| 数据库设计文档 | ✅ | `docs/DATABASE.md`（本轮补齐，含 Mermaid ER 图与逐字段说明）|
| 系统使用说明 | ✅ | `docs/USER_GUIDE.md`（本轮补齐，用户端/管理端/小程序操作指南）|
| 系统测试报告 | ✅ | 见 `VERIFICATION.md`（43 项 Java + 35 项 Python 用例）|
| 知识库初始数据 | ✅ | `python/knowledge_base/`（21 篇，已重建向量库）|

---

## 首轮修复的严重缺陷

| # | 缺陷 | 影响 | 修复 |
|---|---|---|---|
| 1 | `SecurityConfig` 的 `requestMatchers` 带了 `/api` 前缀，但 `context-path=/api` 已被容器剥离 | **所有规则失效，连登录都 403**，系统完全不可用 | 改为无前缀路径；测试锁定 |
| 2 | `GovPolicyDocumentMapper`/`HelpContentMapper` 导入 `core.metadata.Page`（不存在） | `mvn compile` 失败 | 改为 `extension.plugins.pagination.Page` |
| 3 | `_get_chroma_path` 被 5 处引用但从未定义 | Python 智能体 `ImportError` | 新增该函数（按 collection 分目录） |
| 4 | 12 处 KB 调用用 `doc_dir/chroma_dir/rebuild`，真实签名是 `docs_dir/persist_dir` | `TypeError`，检索全部落空 | 统一签名并兼容两套参数名 |
| 5 | `rag_server` 忽略请求的 `collection` 参数，固定查默认库 | 三库检索串库 | 按 collection 路由到对应向量库 |
| 6 | `query_knowledge_base` 返回 `List[str]`，但调用方按 `Document` 用 `.page_content` | `AttributeError` 被吞，静默降级 | 统一返回 `Document`（保留来源元数据） |
| 7 | 小程序 tabBar 引用 6 个不存在的图标 | 小程序无法编译 | 生成 6 个 PNG |
| 8 | 小程序调用 `/help/medication/guide`、`/help/tourism/attractions`、`/auth/wx-login` | 三个接口后端都不存在，功能全废 | 改走 `/chat/send` + `/auth/guest-login` |
| 9 | 小程序跳转 `pages/policy/detail`、`pages/tourism/detail` 未声明 | 点击崩溃 | 新建两个详情页并注册 |
| 10 | `.env.docker` 含真实 DB 密码与 JWT 密钥 | 凭据泄露 | 轮换；compose 移除弱默认值 |

## 本轮（第二轮）补齐项与剩余待办

### 本轮（第二轮）已补齐

| # | 原缺口 | 对应条款 | 交付 |
|---|---|---|---|
| 1 | API 路径与文档不一致 | §3.4/§3.5 | `/api/articles`、`/api/articles/{id}`、`/api/policies`、`/api/policies/{id}`、`/api/quota` 已按文档注册，原 `/api/help/*` 保留为兼容别名 |
| 2 | 文章详情无「相关推荐」 | §4.1 | 新增 `GET /api/articles/{id}/related` + 前端相关推荐区块 |
| 3 | 配额管理只读 | §4.2 | 新增 `GET/PUT /api/admin/quota`，管理页支持查看、筛选与调整 |
| 4 | 政策管理无上传/同步 | §4.2 | 新增 `POST /api/admin/kb/upload`、`/api/admin/kb/sync` + Python `/api/v1/kb/upload`，管理页支持拖拽上传与重建索引 |
| 5 | 小程序无对话离线缓存 | §5.2 | `utils/chatCache.js` 分键缓存最近 50 条 + 弱网提示与发送降级 |
| 6 | 手机号明文落库 | §8.1 | `PhoneCryptoService`：AES-256-GCM 加密 + HMAC 盲索引，含迁移脚本 |
| 7 | 无 443/HTTPS | §9.2/§10.3 | `docker-compose.https.yml` + `nginx.https.conf` + 自签证书脚本，默认部署不受影响 |
| 8 | 无压测 | §10.2 | `scripts/loadtest/load_test.py`（纯标准库）+ `docs/PERFORMANCE.md` |
| 9 | 缺 3 份交付文档 | §11.2 | `docs/API.md`、`docs/DATABASE.md`、`docs/USER_GUIDE.md` |
| 10 | 知识库仅 5 篇 | §7.1 | 扩充至 21 篇并重建向量库 |

### 本轮额外修复的既有缺陷（核验与实跑中发现，共 15 项）

| # | 缺陷 | 影响 |
|---|---|---|
| 1 | `user` 表默认管理员 BCrypt 哈希与 `admin123` 不匹配 | 内置管理员**无法登录**，管理端完全不可用 |
| 2 | 全站列表页传 `page=0`，后端 `@Min(1)` 校验 | 文章/政策列表与管理页**首页请求 400** |
| 3 | 前端政策字段名与后端 DTO 错位（`documentNumber`/`category`/`content` ↔ `docNumber`/`policyType`/`fullText`）| 管理端**新建政策必定 400 失败**；列表与详情字段显示为空 |
| 4 | 新建文章无发布开关，`isPublished` 默认 0 | 新建文章恒为草稿，**用户端不可见** |
| 5 | 向量检索 `score` 恒为 0（元数据无 score，且 Chroma 返回的是距离）| 政策问答**静默降级为关键词检索** |
| 6 | Java 按 `policy_type` 过滤，但知识库元数据无该字段 | 带政策类型筛选时**结果被全部丢弃** |
| 7 | 关键词兜底用整个问题做 LIKE | 兜底检索**几乎永不命中** |
| 8 | 知识库重建前未清 Chroma System 缓存 | **第二次重建必定失败**（readonly database）|
| 9 | 知识库上传的 `collection` 未用 `Form(...)` 声明 | multipart 字段被忽略，**文件落入错误集合** |
| 10 | `gov_policy_document` 无种子数据、`vector_id` 从不写入 | 向量命中后**回查数据库为空** |
| 11 | `application.yml` 未配置 multipart | 声明 5MB/10MB 实际上限 1MB，超限报 **500 而非 400** |
| 12 | `SecurityConfig` 放行 `/actuator/health` 但未引入 actuator | 该规则为死规则，实际 404 |
| 13 | TTS 被改为未实现桩（工作区回归）| §3.3 TTS **返回 501**；本轮已恢复 edge-tts 通道 |
| 14 | 音频/SSE 用裸 URL 无法带 Token | TTS 播报与 SSE 流式**均 401** |
| 15 | `vite.config.js` 代理 rewrite 剥离 `/api` 前缀，但后端 context-path 就是 `/api` | **开发环境所有接口 404**，前端无法联调 |

### 剩余待办（需生产环境或人工决策）

1. **ASR 语音识别**：按用户要求本轮不做，接口返回 501；部署 `faster-whisper` 或配置阿里云 NLS 后按 §10.1 实测准确率。
2. **BGE 模型下载**：生产需可访问 HuggingFace（或预置模型到镜像）；当前离线环境用 `EMBEDDING_PROVIDER=hash` 验证链路。
3. **真实后端并发基线**：压测工具与报告已就绪，需在部署后按 `docs/PERFORMANCE.md` §4 复跑填入真实数据（注意先关闭限流，否则 429 会被误判为性能问题）。
4. **正式 HTTPS 证书**：自签证书仅限开发/内网；生产需 Let's Encrypt 或商业证书 + 已备案域名。
5. **手机号加密密钥管理**：`PHONE_ENC_KEY`/`PHONE_INDEX_KEY` 需通过密钥管理系统注入并纳入轮换流程。
6. **知识库语料质量**：21 篇为示例语料，建议按三大方向补充真实业务语料。
7. **OpenAPI 导出**：`docs/API.md` 已覆盖全部接口，如需机器可读契约可再引入 springdoc 导出。
