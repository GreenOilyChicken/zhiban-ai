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
