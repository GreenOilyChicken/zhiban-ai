# 知伴AI — 智能体全栈系统

> 开发单位：知伴（湖州）智能科技有限公司

## 项目概述

知伴AI是一套面向政务、银发（老年康养）、文旅三个方向的AI智能体全栈系统，包含：

1. **Python AI智能体系统** — 核心底座 + 三个垂直方向智能体
2. **Java Spring Boot后端** — Web API服务
3. **Vue.js前端** — 用户端 + 管理端
4. **微信小程序** — 适老化AI陪伴
5. **数据库** — MySQL + ChromaDB向量库

## 目录结构

```
zhiban-ai/
├── python/                      # Python AI智能体系统
│   ├── config.py                # 全局配置
│   ├── base/                    # 核心框架
│   │   ├── agent_framework.py   # Agent/Tool/PlannerExecutorTeam
│   │   └── model_factory.py     # LLM & Embedding工厂
│   ├── knowledge_base/          # 知识库（ChromaDB + BGE）
│   │   └── build_kb.py
│   ├── elderly_agent/           # 银发康养智能体
│   │   ├── elderly_agent.py     # 主Agent
│   │   ├── elderly_team.py      # Planner-Executor团队
│   │   └── tools/               # 用药指导、照护建议、康复计划、长护险
│   ├── govpolicy_agent/         # 政务政策智能体
│   │   ├── government_agent.py
│   │   ├── government_team.py
│   │   └── training_ledger/     # 台账生成
│   ├── tourism_agent/           # 文旅导览智能体
│   │   ├── tourism_agent.py
│   │   ├── tourism_team.py
│   │   └── tools/               # 景点导览、路线规划、文化故事
│   ├── tests/                   # 测试
│   ├── requirements.txt
│   └── .env.example
├── java-backend/                # Java Spring Boot后端
│   ├── src/main/java/com/zhiban/ai/
│   │   ├── config/              # 安全、MyBatis-Plus、RAG配置
│   │   ├── controller/          # 控制器
│   │   ├── dto/                 # 数据传输对象
│   │   ├── entity/              # 实体类
│   │   ├── mapper/              # MyBatis映射
│   │   ├── service/             # 业务逻辑
│   │   └── security/            # JWT认证
│   ├── src/main/resources/
│   │   ├── application.yml
│   │   └── schema.sql           # 数据库DDL
│   └── pom.xml
├── vue-frontend/                # Vue.js前端
│   ├── src/
│   │   ├── api/                 # API调用
│   │   ├── views/               # 页面（用户端+管理端）
│   │   ├── components/          # 公共组件
│   │   └── router/              # 路由
│   └── package.json
├── wechat-miniprogram/          # 微信小程序
│   ├── pages/                   # 页面
│   ├── app.json
│   └── app.js
└── README.md
```

## 技术栈

### Python AI系统
- LangChain 0.3.x — Agent框架
- ChromaDB — 向量数据库
- BGE Embedding — 中文语义检索
- DeepSeek/OpenAI/Qwen — LLM（多Provider支持）
- python-docx — 台账文档生成

### Java后端
- Spring Boot 3.2.x
- MyBatis-Plus 3.5.x
- Spring Security + JWT
- MySQL 8.0

### Vue前端
- Vue 3 (Composition API)
- Element Plus
- Vite
- Vue Router

## 快速开始

### Python智能体系统
```bash
cd python
pip install -r requirements.txt
cp .env.example .env  # 填写API Key
python elderly_agent/main.py --build-kb  # 构建知识库
python elderly_agent/main.py  # 启动银发康养智能体
```

### Java后端
```bash
cd java-backend
mvn spring-boot:run
```

### Vue前端
```bash
cd vue-frontend
npm install
npm run dev
```

## 核心设计

### 1. Planner-Executor调度模式
用户问题 → Planner(LLM路由) → 对应Executor Agent → 执行工具 → 返回结果

### 2. 医疗安全红线
- 不给具体药物剂量建议
- DDI(药物相互作用)矩阵检查
- 疾病-药物禁忌检查
- 免责声明
- 紧急信号识别（拨打120、心理援助热线）

### 3. 适老化设计
- 大字体界面
- 语音引导
- 简化操作流程
- 预留线下服务通道

---

## 本次交付说明（对照附件一 V1.0）

完整需求对照见 [`REQUIREMENTS.md`](REQUIREMENTS.md)，验证证据见 [`VERIFICATION.md`](VERIFICATION.md)。

### 架构（附件一 §2.1 四层）

```
Vue3 Web ──┐
           ├─► Java Spring Boot (/api, 8080) ──HTTP──► Python 智能体 (/api/v1, 8081)
微信小程序 ─┘         │                                      │
                   MySQL 8                            ChromaDB + BGE
```

Java 只负责业务与鉴权，AI 能力（对话/工具调用/RAG/语音）全部在 Python 侧，
通过 `AI_SERVICE_URL` 配置调用地址。

### 快速启动（本地开发）

```bash
# 1. 数据库
mysql -uroot -p < java-backend/src/main/resources/schema.sql

# 2. Python AI 服务（8081）
cd python
pip install -r requirements.lock.txt
export LLM_PROVIDER=deepseek DEEPSEEK_API_KEY=sk-xxx
python rag_server.py          # 首次启动自动构建知识库

# 3. Java 后端（8080）
cd java-backend
export DB_PASSWORD=xxx JWT_SECRET=<32位以上随机串> AI_SERVICE_URL=http://localhost:8081
mvn spring-boot:run

# 4. Vue 前端（5173）
cd vue-frontend && npm install && npm run dev

# 5. 微信小程序
用微信开发者工具打开 wechat-miniprogram/，修改 app.js 的 apiBaseUrl
```

### 关键环境变量

| 变量 | 说明 | 默认 |
|---|---|---|
| `DB_PASSWORD` | 数据库密码 | **必填，无默认值** |
| `JWT_SECRET` | JWT 密钥（≥32 字符） | **必填，无默认值** |
| `LLM_PROVIDER` | deepseek / openai / qwen / codebuddy | deepseek |
| `AI_SERVICE_URL` | Python AI 服务地址 | http://localhost:8081 |
| `EMBEDDING_PROVIDER` | bge（生产）/ hash（离线兜底） | bge |
| `RATE_LIMIT_MAX` | 每窗口最大请求数 | 300 |
| `KB_AUTO_BUILD` | 启动时自动建库 | true |

### 测试

```bash
cd python       && python3 -m pytest tests/ -q          # 31 passed
cd java-backend && mvn -Dai.live=true test              # 21 passed
cd vue-frontend && npm run build                        # 构建通过
```
