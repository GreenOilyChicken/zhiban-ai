# 知伴AI — 项目启动与部署操作文档

> 本文档覆盖 Python AI智能体、Java Spring Boot后端、Vue.js前端、微信小程序四大模块的完整启动与部署流程。

---

## 目录

1. [环境要求](#1-环境要求)
2. [项目结构总览](#2-项目结构总览)
3. [快速启动（开发环境）](#3-快速启动开发环境)
4. [Python AI智能体系统](#4-python-ai智能体系统)
5. [Java Spring Boot后端](#5-java-spring-boot后端)
6. [Vue.js前端](#6-vuejs前端)
7. [微信小程序](#7-微信小程序)
8. [生产环境部署](#8-生产环境部署)
9. [环境变量完整参考](#9-环境变量完整参考)
10. [常见问题排查](#10-常见问题排查)

---

## 1. 环境要求

### 1.1 基础环境

| 组件 | 最低版本 | 推荐版本 | 说明 |
|------|----------|----------|------|
| JDK | 17 | 17 | Spring Boot 3.2 要求 JDK 17+ |
| Maven | 3.8 | 3.9+ | Java 依赖管理与构建 |
| Node.js | 18.x | 20.x LTS | Vue 前端构建 |
| npm | 9.x | 10.x | 随 Node.js 安装 |
| Python | 3.10 | 3.11+ | AI 智能体运行时 |
| MySQL | 8.0 | 8.0.36+ | 主数据库 |
| Git | 2.30+ | 最新 | 版本控制 |

### 1.2 验证环境

```bash
# 验证 Java
java -version

# 验证 Maven
mvn -version

# 验证 Node.js
node -v
npm -v

# 验证 Python
python --version

# 验证 MySQL
mysql --version
```

### 1.3 获取 API Key

本项目使用大语言模型（LLM）驱动 AI 智能体。启动前需至少获取一个 LLM Provider 的 API Key：

| Provider | 获取地址 | 默认模型 |
|----------|----------|----------|
| DeepSeek（推荐） | https://platform.deepseek.com/ | deepseek-chat |
| OpenAI | https://platform.openai.com/ | gpt-4o-mini |
| 通义千问 | https://dashscope.console.aliyun.com/ | qwen-plus |

---

## 2. 项目结构总览

```
zhiban-ai/
├── python/                      # Python AI智能体系统
│   ├── config.py                # 全局配置（环境变量读取）
│   ├── .env.example             # 环境变量模板
│   ├── requirements.txt         # Python 依赖
│   ├── base/                    # 核心框架（Agent/Tool/PlannerExecutorTeam）
│   ├── knowledge_base/          # 知识库（ChromaDB + BGE Embedding）
│   ├── elderly_agent/           # 银发康养智能体
│   ├── govpolicy_agent/         # 政务政策智能体
│   ├── tourism_agent/           # 文旅导览智能体
│   └── tests/                   # 单元测试
├── java-backend/                # Java Spring Boot 后端
│   ├── pom.xml                  # Maven 配置
│   ├── src/main/resources/
│   │   ├── application.yml       # Spring Boot 配置
│   │   └── schema.sql            # 数据库 DDL
│   └── src/main/java/com/zhiban/ai/
│       ├── config/               # 安全、MyBatis-Plus、RAG 配置
│       ├── controller/           # REST 控制器
│       ├── dto/                  # 数据传输对象
│       ├── entity/               # 实体类
│       ├── mapper/               # MyBatis 映射器
│       ├── service/              # 业务逻辑
│       └── security/             # JWT 认证
├── vue-frontend/                # Vue.js 前端
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── api/                  # API 调用层
│       ├── views/                # 页面组件
│       ├── components/           # 公共组件
│       └── router/               # 路由配置
├── wechat-miniprogram/          # 微信小程序
│   ├── app.js                    # 全局逻辑
│   ├── app.json                  # 全局配置
│   └── pages/                    # 页面（首页/对话/用药/政策/文旅/我的）
└── README.md
```

---

## 3. 快速启动（开发环境）

以下步骤假设您已安装所有基础环境（JDK 17、Maven、Node.js、Python 3.10+、MySQL 8.0）。

### 3.1 克隆项目

```bash
git clone <repository-url> zhiban-ai
cd zhiban-ai
```

### 3.2 启动 MySQL 并初始化数据库

```bash
# 登录 MySQL
mysql -u root -p

# 执行 DDL 脚本（在 MySQL 命令行中）
source java-backend/src/main/resources/schema.sql;
exit;
```

此脚本将：
- 创建 `zhiban_ai` 数据库
- 创建 `user`、`user_quota`、`gov_policy_document`、`help_content`、`categories` 五张表
- 插入默认管理员账户（用户名: `admin`，密码: `admin123`）
- 插入默认分类数据

### 3.3 配置 Python AI 智能体

```bash
cd python

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux/macOS:
# source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key
```

编辑 `.env` 文件，关键配置项：

```env
# 必填：至少配置一个 LLM Provider 的 API Key
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-actual-api-key

# 其余可使用默认值
```

### 3.4 构建知识库（首次必须执行）

```bash
# 确保在 python 目录下，虚拟环境已激活

# 构建政务政策知识库
python govpolicy_agent/main.py --build-kb

# 构建银发康养知识库
python elderly_agent/main.py --build-kb

# 构建文旅导览知识库
python tourism_agent/main.py --build-kb
```

> **注意**：首次执行会下载 BGE Embedding 模型（约 100MB），需要网络连接。模型缓存在 `~/.cache/huggingface/` 目录下，后续运行无需重复下载。

### 3.5 启动 Java 后端

```bash
# 回到项目根目录
cd ../java-backend

# 设置环境变量（PowerShell 示例）
$env:DB_PASSWORD="your-mysql-password"
$env:JWT_SECRET="your-jwt-secret-key-at-least-32-characters-long"

# Linux/macOS:
# export DB_PASSWORD=your-mysql-password
# export JWT_SECRET=your-jwt-secret-key-at-least-32-characters-long

# 启动 Spring Boot
mvn spring-boot:run
```

后端启动后，访问地址：`http://localhost:8080/api`

### 3.6 启动 Vue 前端

```bash
# 新开终端，回到项目根目录
cd vue-frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端启动后，访问地址：`http://localhost:5173`

Vite 开发服务器已配置代理，`/api` 请求自动转发到 `http://localhost:8080`。

### 3.7 启动微信小程序

1. 下载并安装 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 打开微信开发者工具，选择「导入项目」
3. 项目目录选择：`zhiban-ai/wechat-miniprogram`
4. AppID 填入你的小程序 AppID（或选择测试号）
5. 点击确定即可预览

> **开发环境配置**：在 `app.js` 中修改 `apiBaseUrl` 为本地后端地址：
> ```javascript
> apiBaseUrl: 'http://localhost:8080/api'
> ```

---

## 4. Python AI智能体系统

### 4.1 环境变量配置

编辑 `python/.env` 文件：

```env
# ═══ LLM 配置 ═══
LLM_PROVIDER=deepseek                    # deepseek | openai | qwen

# DeepSeek（推荐）
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# OpenAI（备选）
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# 通义千问（备选）
QWEN_API_KEY=
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus

# LLM 参数
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=2048

# ═══ Embedding 配置 ═══
BGE_MODEL_NAME=BAAI/bge-small-zh-v1.5
EMBEDDING_DEVICE=cpu                     # 有GPU可改为 cuda

# ═══ 知识库路径（可使用相对路径或绝对路径）═══
KB_POLICY_DIR=knowledge_base/policies
KB_ELDERLY_DIR=knowledge_base/elderly
KB_TOURISM_DIR=knowledge_base/tourism
KB_CHROMA_DIR=knowledge_base/chroma_db

# ═══ 台账输出 ═══
LEDGER_OUTPUT_DIR=output/ledgers

# ═══ 日志脱敏 ═══
LTC_LOG_MASK=true
```

### 4.2 知识库管理

```bash
cd python

# ── 构建知识库 ──
# 单独构建某个方向的知识库：
python govpolicy_agent/main.py --build-kb          # 政务政策
python elderly_agent/main.py --build-kb            # 银发康养
python tourism_agent/main.py --build-kb            # 文旅导览

# 强制重建（清除旧向量数据）：
python govpolicy_agent/main.py --build-kb --rebuild

# ── 验证知识库 ──
python -c "
from knowledge_base.build_kb import load_knowledge_base
db = load_knowledge_base()
print('知识库状态:', '正常' if db else '未构建')
"

# ── 清除知识库 ──
# 删除 chroma_db 目录即可
rm -rf knowledge_base/chroma_db
```

### 4.3 运行智能体

```bash
cd python

# ── 银发康养智能体 ──
python elderly_agent/main.py                        # 交互模式
python elderly_agent/main.py --query "高血压患者用药注意事项"  # 单次查询
python elderly_agent/main.py --verbose              # 详细日志

# ── 政务政策智能体 ──
python govpolicy_agent/main.py
python govpolicy_agent/main.py --query "银发经济有哪些政策"
python govpolicy_agent/main.py --team               # Planner-Executor团队模式

# ── 文旅导览智能体 ──
python tourism_agent/main.py
python tourism_agent/main.py --query "故宫的开放时间和门票"
python tourism_agent/main.py --team
```

### 4.4 运行测试

```bash
cd python

# 运行全部测试
pytest

# 运行特定测试文件
pytest tests/test_medication_safety.py -v
pytest tests/test_knowledge_base.py -v
pytest tests/test_agent.py -v
pytest tests/test_tools.py -v
pytest tests/test_ledger.py -v

# 生成测试覆盖率报告
pytest --cov=. --cov-report=html
```

### 4.5 Python 服务作为后端 RAG 检索服务

Java 后端通过 HTTP 调用 Python 向量检索服务。如需启用此集成：

1. 在 Python 侧部署一个向量检索 API（可使用 FastAPI 封装）
2. 在 Java 侧 `application.yml` 中配置 `rag.vector-api-url` 指向 Python 服务地址

示例 Python 检索服务（可选，简化版）：

```python
# python/rag_server.py （如需可自行创建）
from fastapi import FastAPI
from knowledge_base.build_kb import query_knowledge_base

app = FastAPI()

@app.post("/api/v1/search")
def search(request: dict):
    results = query_knowledge_base(request["query"], top_k=request.get("topK", 5))
    return {"results": results}
```

启动：`uvicorn rag_server:app --host 0.0.0.0 --port 8081`

---

## 5. Java Spring Boot后端

### 5.1 环境变量

后端通过环境变量注入敏感配置，**不硬编码任何密钥**：

| 环境变量 | 说明 | 示例值 |
|----------|------|--------|
| `DB_HOST` | MySQL 主机地址 | `localhost`（默认） |
| `DB_PORT` | MySQL 端口 | `3306`（默认） |
| `DB_NAME` | 数据库名 | `zhiban_ai`（默认） |
| `DB_USERNAME` | 数据库用户名 | `root`（默认） |
| `DB_PASSWORD` | 数据库密码（**必填**） | `your-password` |
| `JWT_SECRET` | JWT 签名密钥（**必填**，至少32字符） | `a1b2c3d4e5f6...` |
| `RAG_VECTOR_API_URL` | Python 向量检索服务地址 | `http://localhost:8081/api/v1/search` |
| `RAG_API_KEY` | RAG 服务 API Key（可选） | — |

### 5.2 设置环境变量

**Windows (PowerShell)：**
```powershell
$env:DB_PASSWORD="your-mysql-password"
$env:JWT_SECRET="your-jwt-secret-key-must-be-at-least-32-chars"
```

**Linux/macOS：**
```bash
export DB_PASSWORD=your-mysql-password
export JWT_SECRET=your-jwt-secret-key-must-be-at-least-32-chars
```

### 5.3 启动方式

**方式一：Maven 直接启动（开发）**
```bash
cd java-backend
mvn spring-boot:run
```

**方式二：构建 JAR 后启动（生产）**
```bash
cd java-backend
mvn clean package -DskipTests
java -jar target/zhiban-ai-backend-1.0.0.jar
```

**方式三：使用环境变量文件**
```bash
# 创建 .env 文件
cat > .env << 'EOF'
DB_PASSWORD=your-mysql-password
JWT_SECRET=your-jwt-secret-key-must-be-at-least-32-chars
EOF

# 加载后启动
export $(cat .env | xargs) && java -jar target/zhiban-ai-backend-1.0.0.jar
```

### 5.4 验证后端启动

```bash
# 健康检查
curl http://localhost:8080/api/help/articles?page=1&size=1

# 登录获取 Token
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 使用 Token 查询配额
curl http://localhost:8080/api/help/quota?quotaType=POLICY_QA \
  -H "Authorization: Bearer <your-token>"
```

### 5.5 数据库初始化

```bash
# 方式一：MySQL 命令行
mysql -u root -p < java-backend/src/main/resources/schema.sql

# 方式二：在 MySQL 中直接执行
mysql -u root -p -e "source java-backend/src/main/resources/schema.sql"
```

默认管理员账户：
- 用户名：`admin`
- 密码：`admin123`
- **生产环境部署后请立即修改密码**

---

## 6. Vue.js前端

### 6.1 开发环境

```bash
cd vue-frontend

# 安装依赖
npm install

# 启动开发服务器（默认端口 5173）
npm run dev
```

Vite 配置了代理，开发环境下 `/api` 请求自动转发到 `http://localhost:8080`。

### 6.2 生产构建

```bash
cd vue-frontend

# 构建生产包
npm run build

# 预览生产构建
npm run preview
```

构建产物输出到 `vue-frontend/dist/` 目录。

### 6.3 部署到 Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/vue-frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # API 代理到 Java 后端
    location /api/ {
        proxy_pass http://127.0.0.1:8080/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 6.4 前端路由说明

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | Home.vue | 首页 |
| `/login` | Login.vue | 登录页 |
| `/help` | HelpCenter.vue | 帮助中心 |
| `/help/articles` | ArticleList.vue | 文章列表 |
| `/help/article/:id` | ArticleDetail.vue | 文章详情 |
| `/policy` | PolicyList.vue | 政策列表 |
| `/policy/qa` | PolicyQA.vue | 政策智能问答 |
| `/admin` | AdminLayout.vue | 管理后台 |
| `/admin/articles` | AdminArticle.vue | 文章管理 |
| `/admin/policies` | AdminPolicy.vue | 政策管理 |
| `/admin/quotas` | AdminQuota.vue | 配额管理 |

---

## 7. 微信小程序

### 7.1 开发环境

1. 下载 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 打开后选择「导入项目」
3. 目录选择：`zhiban-ai/wechat-miniprogram`
4. AppID：填入你的小程序 AppID（如无可用测试号）
5. 点击确定

### 7.2 配置后端地址

编辑 `app.js`，修改 `apiBaseUrl`：

```javascript
// 开发环境
apiBaseUrl: 'http://localhost:8080/api'

// 生产环境
apiBaseUrl: 'https://api.your-domain.com/api'
```

### 7.3 小程序页面

| 页面 | 路径 | 功能 |
|------|------|------|
| 首页 | `pages/index/index` | 功能导航入口 |
| AI对话 | `pages/chat/chat` | 智能体对话 |
| 用药指导 | `pages/medication/medication` | 用药安全查询 |
| 政策查询 | `pages/policy/policy` | 政策文档浏览与问答 |
| 文旅导览 | `pages/tourism/tourism` | 景点与路线 |
| 我的 | `pages/profile/profile` | 个人中心 |

### 7.4 发布上线

1. 在微信开发者工具中点击「上传」
2. 登录 [微信公众平台](https://mp.weixin.qq.com/) 提交审核
3. 审核通过后发布

### 7.5 适老化设计

小程序内置适老化模式，默认开启：
- 大字体显示（`fontSize: 'large'`）
- 高对比度配色
- 简化操作流程
- 语音输入支持
- 预留线下服务通道

---

## 8. 生产环境部署

### 8.1 整体架构

```
                    ┌──────────────┐
                    │  微信小程序   │
                    └──────┬───────┘
                           │ HTTPS
                           ▼
┌──────────┐     ┌──────────────────┐     ┌──────────────┐
│  Nginx   │────▶│  Java Backend    │────▶│   MySQL 8.0  │
│  (前端)   │     │  Spring Boot     │     └──────────────┘
└──────────┘     │  :8080           │
                  └────────┬─────────┘
                           │ HTTP
                           ▼
                  ┌──────────────────┐     ┌──────────────┐
                  │  Python AI 服务   │────▶│   ChromaDB    │
                  │  (RAG 检索)       │     │   (向量库)     │
                  │  :8081            │     └──────────────┘
                  └──────────────────┘
```

### 8.2 服务器要求

| 资源 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 2核 | 4核+ |
| 内存 | 4GB | 8GB+ |
| 磁盘 | 40GB | 100GB SSD |
| 带宽 | 5Mbps | 10Mbps+ |
| 操作系统 | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### 8.3 Docker 部署（可选）

#### 8.3.1 Docker Compose 配置

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    container_name: zhiban-mysql
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_PASSWORD}
      MYSQL_DATABASE: zhiban_ai
      MYSQL_CHARSET: utf8mb4
      MYSQL_COLLATION: utf8mb4_unicode_ci
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./java-backend/src/main/resources/schema.sql:/docker-entrypoint-initdb.d/schema.sql
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

  java-backend:
    build: ./java-backend
    container_name: zhiban-backend
    depends_on:
      - mysql
    environment:
      DB_HOST: mysql
      DB_PORT: 3306
      DB_NAME: zhiban_ai
      DB_USERNAME: root
      DB_PASSWORD: ${DB_PASSWORD}
      JWT_SECRET: ${JWT_SECRET}
      RAG_VECTOR_API_URL: http://python-ai:8081/api/v1/search
    ports:
      - "8080:8080"

  python-ai:
    build: ./python
    container_name: zhiban-ai
    environment:
      LLM_PROVIDER: deepseek
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY}
      BGE_MODEL_NAME: BAAI/bge-small-zh-v1.5
      EMBEDDING_DEVICE: cpu
    ports:
      - "8081:8081"

  nginx:
    image: nginx:latest
    container_name: zhiban-nginx
    depends_on:
      - java-backend
    ports:
      - "80:80"
    volumes:
      - ./vue-frontend/dist:/usr/share/nginx/html
      - ./nginx.conf:/etc/nginx/conf.d/default.conf

volumes:
  mysql_data:
```

#### 8.3.2 Java Dockerfile

`java-backend/Dockerfile`：

```dockerfile
FROM maven:3.9-eclipse-temurin-17 AS builder
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:resolve
COPY src ./src
RUN mvn clean package -DskipTests

FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=builder /app/target/zhiban-ai-backend-1.0.0.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

#### 8.3.3 Python Dockerfile

`python/Dockerfile`：

```dockerfile
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')" || true

EXPOSE 8081
CMD ["python", "-m", "uvicorn", "rag_server:app", "--host", "0.0.0.0", "--port", "8081"]
```

#### 8.3.4 一键部署

```bash
# 创建环境变量文件
cat > .env << 'EOF'
DB_PASSWORD=your-mysql-password
JWT_SECRET=your-jwt-secret-key-must-be-at-least-32-chars
DEEPSEEK_API_KEY=sk-your-api-key
EOF

# 构建前端
cd vue-frontend && npm install && npm run build && cd ..

# 启动所有服务
docker compose up -d

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f java-backend
```

### 8.4 Nginx 配置

`nginx.conf`：

```nginx
server {
    listen 80;
    server_name _;

    # 前端
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    # API 网关
    location /api/ {
        proxy_pass http://java-backend:8080/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_read_timeout 120s;
    }
}
```

### 8.5 Systemd 服务（非 Docker 方式）

`/etc/systemd/system/zhiban-backend.service`：

```ini
[Unit]
Description=Zhiban AI Backend Service
After=network.target mysql.service

[Service]
Type=simple
User=zhiban
WorkingDirectory=/opt/zhiban-ai/java-backend
Environment=DB_PASSWORD=your-mysql-password
Environment=JWT_SECRET=your-jwt-secret-key-must-be-at-least-32-chars
Environment=DB_HOST=localhost
Environment=DB_PORT=3306
Environment=DB_NAME=zhiban_ai
Environment=DB_USERNAME=root
ExecStart=/usr/bin/java -jar /opt/zhiban-ai/java-backend/target/zhiban-ai-backend-1.0.0.jar
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable zhiban-backend
sudo systemctl start zhiban-backend
sudo systemctl status zhiban-backend
```

---

## 9. 环境变量完整参考

### 9.1 Python 侧

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `LLM_PROVIDER` | 否 | `deepseek` | LLM 提供商 |
| `DEEPSEEK_API_KEY` | 是* | — | DeepSeek API Key |
| `OPENAI_API_KEY` | — | — | OpenAI API Key（选 OpenAI 时必填） |
| `QWEN_API_KEY` | — | — | 通义千问 API Key（选 Qwen 时必填） |
| `LLM_TEMPERATURE` | 否 | `0.3` | 生成温度 |
| `LLM_MAX_TOKENS` | 否 | `2048` | 最大 Token 数 |
| `BGE_MODEL_NAME` | 否 | `BAAI/bge-small-zh-v1.5` | Embedding 模型 |
| `EMBEDDING_DEVICE` | 否 | `cpu` | Embedding 运行设备 |
| `KB_POLICY_DIR` | 否 | `knowledge_base/policies` | 政策知识库目录 |
| `KB_ELDERLY_DIR` | 否 | `knowledge_base/elderly` | 康养知识库目录 |
| `KB_TOURISM_DIR` | 否 | `knowledge_base/tourism` | 文旅知识库目录 |
| `KB_CHROMA_DIR` | 否 | `knowledge_base/chroma_db` | ChromaDB 持久化目录 |
| `LEDGER_OUTPUT_DIR` | 否 | `output/ledgers` | 台账输出目录 |
| `LTC_LOG_MASK` | 否 | `true` | 日志脱敏开关 |

> \* 根据 `LLM_PROVIDER` 的值，对应的 API Key 必填。

### 9.2 Java 侧

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `DB_HOST` | 否 | `localhost` | MySQL 主机 |
| `DB_PORT` | 否 | `3306` | MySQL 端口 |
| `DB_NAME` | 否 | `zhiban_ai` | 数据库名 |
| `DB_USERNAME` | 否 | `root` | 数据库用户名 |
| `DB_PASSWORD` | **是** | — | 数据库密码 |
| `JWT_SECRET` | **是** | — | JWT 签名密钥（≥32字符） |
| `RAG_VECTOR_API_URL` | 否 | `http://localhost:8081/api/v1/search` | 向量检索服务地址 |
| `RAG_API_KEY` | 否 | — | RAG 服务认证 Key |

### 9.3 微信小程序侧

在 `app.js` 中配置：

| 字段 | 说明 |
|------|------|
| `apiBaseUrl` | 后端 API 基础地址 |
| `elderlyMode` | 适老化模式开关（默认 `true`） |
| `fontSize` | 字体大小（`'large'` / `'normal'`） |

---

## 10. 常见问题排查

### 10.1 Python 智能体

**Q: 首次运行报错 `ModuleNotFoundError: No module named 'langchain'`**

A: 确保已激活虚拟环境并安装依赖：
```bash
source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Q: 构建知识库时长时间卡住**

A: 首次运行会下载 BGE Embedding 模型（约 100MB）。请确保网络畅通，或提前手动下载模型到 `~/.cache/huggingface/`。

**Q: `ChromaDB` 报错 `SQLite version too old`**

A: ChromaDB 要求 SQLite 3.35+。升级方式：
```bash
pip install --upgrade pysqlite3-binary
```

**Q: LLM 调用报 401 Unauthorized**

A: 检查 `.env` 文件中 API Key 是否正确填写，确认 `LLM_PROVIDER` 与对应 Key 匹配。

**Q: 向量检索无结果**

A: 先执行知识库构建 `python govpolicy_agent/main.py --build-kb`，确认 `knowledge_base/chroma_db/` 目录下有数据。

### 10.2 Java 后端

**Q: 启动报错 `JWT_SECRET` 为空**

A: 这是设计行为。必须通过环境变量注入 JWT 密钥：
```bash
export JWT_SECRET="your-secret-key-at-least-32-characters"
```

**Q: 启动报错 `Access denied for user 'root'`**

A: 检查 MySQL 密码是否正确，确认 `DB_PASSWORD` 环境变量已设置。

**Q: 启动报错 `Unknown database 'zhiban_ai'`**

A: 数据库未初始化。执行：
```bash
mysql -u root -p < java-backend/src/main/resources/schema.sql
```

**Q: 接口返回 403 Forbidden**

A: Admin 接口需要 ADMIN 角色。先通过 `/auth/login` 获取 Token，默认管理员 `admin / admin123`。

**Q: 政策问答返回 429**

A: 用户配额已用完。可通过管理后台调整配额，或等待配额重置。

### 10.3 Vue 前端

**Q: 页面空白，控制台报 `Failed to fetch`**

A: 后端未启动或端口不对。确认 Java 后端运行在 8080 端口，Vite 代理配置正确。

**Q: 登录后仍显示未登录**

A: 检查浏览器 LocalStorage 中是否有 `zhiban_ai_token`。清除后重新登录。

**Q: 构建后页面路由 404**

A: Nginx 需配置 `try_files $uri $uri/ /index.html;` 支持 History 模式路由。

### 10.4 微信小程序

**Q: 真机预览无法访问后端**

A: 微信小程序要求后端必须 HTTPS。开发阶段可在微信开发者工具中勾选「不校验合法域名」。生产环境必须配置 SSL 证书。

**Q: `urlCheck` 导致请求失败**

A: `project.config.json` 中已设置 `urlCheck: false`（开发环境）。生产环境需在微信公众平台配置合法域名。

### 10.5 集成问题

**Q: Java 后端调用 Python RAG 服务失败**

A: 检查以下几点：
1. Python RAG 服务是否在运行（端口 8081）
2. `application.yml` 中 `rag.vector-api-url` 配置是否正确
3. 网络防火墙是否放行 8081 端口
4. 注意：Java 后端有关键词兜底检索，即使 Python 服务不可用，政策问答仍可工作（降级模式）

---

## 附录：启动顺序速查

```
1. MySQL 启动 + 初始化 schema.sql
       ↓
2. Python: pip install + 配置 .env + 构建知识库
       ↓
3. Java: 设置环境变量 + mvn spring-boot:run
       ↓
4. Vue: npm install + npm run dev
       ↓
5. 小程序: 导入项目 + 配置 apiBaseUrl
```

各服务可独立启动，但完整功能需要所有服务协同运行。
