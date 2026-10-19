# Embedding 模型选型与基准测试报告

> 项目：知伴AI双端智能体APP
> 日期：2026-10-19
> 结论：**生产环境使用本地 `bge-small-zh-v1.5`（随镜像分发），云端 `bge-m3` 仅用于开发期基准对照。**

---

## 1. 为什么不能用云端 Embedding

本项目交付给客户私有部署，**客户环境无法访问开发者的本地代理**
（`http://127.0.0.1:3800`）。因此：

| 方案 | 客户生产环境 | 检索质量 | 结论 |
|---|---|---|---|
| `hash` 兜底向量 | ✅ 零依赖 | ❌ 字面重合，换问法即漏 | **不可用于生产** |
| 云端 `bge-m3`（开发者代理）| ❌ 客户连不到 | ✅ 1024 维 | **仅开发期对照** |
| **本地 `bge-small-zh-v1.5`** | ✅ 完全自包含 | ✅ 真语义 | **生产选用** |

同时 `rag_server` 的 LLM 链路本身也依赖外部 API，但那是**可配置的厂商 Key**
（DeepSeek / OpenAI / Qwen），与"必须连到开发者个人代理"有本质区别。
Embedding 若上云则会形成对开发者个人机器的硬依赖，交付上不可接受。

---

## 2. 基准测试方法

测试脚本：[`python/benchmark_embeddings.py`](../python/benchmark_embeddings.py)

为避免人工出题的主观性，测试集**直接从三个 Chroma 集合抽取真实 chunk**
（govpolicy / elderly / tourism，共 61 篇），每个 chunk 取其正文前 24 个汉字
作为查询，检验该 chunk 能否被自身召回。

| 参数 | 值 |
|---|---|
| 候选文档 | 61 篇（每集合上限 30） |
| 查询数 | 61 条 |
| 主指标 | HitRate@5（正确 chunk 进入前 5 名的比例） |
| 辅指标 | MRR（平均倒数排名） |
| 相似度 | 余弦相似度 |

---

## 3. 基准结果（云端 bge-m3，2026-10-19 实测）

| 指标 | 数值 |
|---|---|
| 向量维度 | 1024 |
| HitRate@5 | **1.0000**（61/61） |
| MRR | **0.9918** |
| 文档编码 | 61 篇 / 1.49 s |
| 查询延迟 | 16.5 ms/条 |

复现命令：

```bash
cd python
python benchmark_embeddings.py --provider cloud \
    --base-url http://127.0.0.1:3800/v1 --api-key <key> --out -
```

---

## 4. 本地 bge-small-zh-v1.5 验收标准

客户环境构建完成后，执行：

```bash
cd python
python benchmark_embeddings.py --provider both \
    --base-url <开发代理> --api-key <key>
```

**判定标准**（相对上表基准）：

| 指标 | 本地模型最低要求 | 说明 |
|---|---|---|
| HitRate@5 | ≥ 0.90 | 允许 6 条以内未进前 5 |
| MRR | ≥ 0.85 | 平均排名需在第 1.2 名以内 |
| 查询延迟 | ≤ 100 ms/条（CPU）| 超过则考虑换机器或调小模型 |

若本地 `bge-small-zh-v1.5` 不达标，升级路径为换用 `bge-m3`（约 2.2GB，CPU 推理
慢 3–5 倍）：只需设置 `BGE_MODEL_NAME` 环境变量指向新模型目录，
代码无需改动。语料库需相应重建（维度从 512 变为 1024）。

---

## 5. 本次交付的配置改动

| 文件 | 改动 | 原因 |
|---|---|---|
| `python/requirements.lock.txt` | 新增 `torch==2.4.1` / `sentence-transformers==3.0.1` / `transformers==4.44.2`，`numpy` 锁定 2.5.3 | **原 lock 缺少 torch 与 sentence-transformers，`EMBEDDING_PROVIDER` 默认 `bge` 会导致容器启动即 ImportError** |
| `python/Dockerfile` | torch 单独经 `--index-url https://download.pytorch.org/whl/cpu` 安装 | 默认 PyPI 源会拉入 2GB+ CUDA 依赖 |
| `python/config.py` | 新增 `BGE_MODEL_DIR`，`BGE_MODEL_NAME` 默认指向本地 `models/bge-small-zh-v1.5` | 客户环境无外网，不能依赖 HuggingFace 在线下载 |
| `python/base/model_factory.py` | bge 加载失败自动降级 `hash` 并打 ERROR 告警 | 避免客户机缺依赖导致服务整体起不来；降级可被发现 |
| `python/.dockerignore` | 排除 `.pylibs/`（cp313 Linux 包，与镜像 3.11 不兼容且与 lock 重复）；**保留 `models/`** | 保证模型随镜像分发 |
| `.gitignore` | 新增 `python/models/` | 95MB 模型二进制不进 git 历史 |

---

## 6. 已知限制

1. **本地模型质量未经实测**：开发机无外网且无 `torch`，`sentence-transformers`
   无法安装，故本地 `bge-small-zh-v1.5` 的指标尚未采集。需在客户环境
   `docker build` 后按 §4 标准验收。
2. **测试集偏易**：查询取自 chunk 自身前缀，与真实用户的口语化提问
   （如"长护险咋申请"）存在分布差异。HitRate@5=1.0 应理解为"链路正确性
   达标"，而非真实场景的上限。建议上线前补充人工问答集复测。
3. **语料规模小**：21 篇示例语料，向量库仅 61 个 chunk。规模扩大后需复测
   召回率。
