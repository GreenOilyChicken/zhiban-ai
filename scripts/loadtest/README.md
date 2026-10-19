# 知伴AI — 并发压测工具（loadtest）

仅使用 **Python 3 标准库**（`threading` + `http.client`）实现的并发压测工具，
用于验证《附件一 项目功能需求清单 V1.0》**§10.2** 的性能验收指标：

| 指标 | 要求 |
|---|---|
| 并发用户数 | 系统支持至少 **50 个并发用户**同时在线 |
| 对话响应时间 | 单次对话响应时间 **≤ 3 秒**（不含网络延迟） |

> 不依赖 `requests` / `locust` / `aiohttp` / `wrk` 等任何第三方组件，
> 保证在**无法联网 pip install** 的交付/验收环境里可直接运行。

---

## 1. 文件说明

| 文件 | 作用 |
|---|---|
| `load_test.py` | 压测主程序（可执行） |
| `stub_server.py` | 本地桩服务，用于在无真实后端时**自检压测脚本本身**可用 |
| `README.md` | 本文档 |

被测系统架构（依据 `README.md` / `docker-compose.yml` / `application.yml` 核实）：

```
Vue3 前端 ──► Nginx ──► Java Spring Boot 3.2.5  (context-path=/api, :8080)
                              └──► Python FastAPI AI 服务 (:8081) + MySQL 8
```

关键事实（已从源码核实，非推测）：

- `server.port: 8080`、`server.servlet.context-path: /api`（`java-backend/src/main/resources/application.yml`）
- `POST /api/auth/guest-login` 公开、无需凭证（`AuthController` + `SecurityConfig`）
- `GET /api/agent/list`、`GET /api/agent/persona` 需要 JWT（`AgentController`）
- `GET /api/help/articles` 公开（`HelpCenterController`，同时映射 `/articles`）
- 统一响应体为 `Result<T>`：`{"code":200,"message":"...","data":{...}}`，JWT 在 `data.token`

---

## 2. 快速开始

```bash
cd scripts/loadtest

# 场景 1：并发游客登录（验证 JWT 签发在并发下正确）
python3 load_test.py --scenario auth --concurrency 50 --duration 30

# 场景 2：登录一次，并发混合调用只读接口（默认场景）
python3 load_test.py --scenario mixed --concurrency 50 --duration 30

# 场景 3：并发真实对话（验证「单次对话 ≤3s」，需后端 + Python AI 服务均可用）
python3 load_test.py --scenario chat --concurrency 50 --duration 30 \
    --chat-message "高血压老人日常饮食要注意什么？"

# 固定总请求数 + JSON 输出（便于写入报告或 CI 断言）
python3 load_test.py --scenario mixed --requests 2000 --json

# 若被测服务无 context-path（例如桩服务），显式置空
python3 load_test.py --base-url http://127.0.0.1:18080 --context-path '' --scenario auth
```

`--base-url` 默认 `http://localhost:8080`，脚本会**自动补上 `/api`** 前缀；
写成 `http://localhost:8080/api` 也不会重复拼接成 `/api/api`。

---

## 3. 命令行参数

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--base-url` | `http://localhost:8080` | 被测服务基址；也可用环境变量 `LOADTEST_BASE_URL` |
| `--context-path` | `/api` | 后端 servlet context-path；传 `''` 表示不加前缀 |
| `--concurrency` | `50` | 并发用户数（= worker 线程数），每个线程一条 keep-alive 连接 |
| `--duration` | `30` | 压测持续秒数（与 `--requests` 互斥） |
| `--requests` | 无 | 固定总请求数模式，覆盖 `--duration` |
| `--scenario` | `mixed` | `auth` / `mixed` / `chat` |
| `--timeout` | `10` | 单请求超时秒数 |
| `--chat-message` | `你好，请介绍一下你自己。` | `chat` 场景发送的消息内容 |
| `--json` | 关 | 以 JSON 输出完整报告到 stdout |
| `--json-out FILE` | 无 | 额外把 JSON 报告写入文件 |
| `--version` / `-h` | — | 版本 / 帮助 |

### 退出码

| 码 | 含义 |
|---|---|
| `0` | 压测完成（**可能含请求级失败**，请以报告里的 `error_rate` 为准） |
| `1` | 参数错误（如 `--concurrency 0`） |
| `2` | **目标不可达** / 前置登录失败 |
| `3` | 运行期致命错误（如未发出任何请求） |

> 注意：退出码 `0` **不代表验收通过**。它只表示压测跑完了。
> 是否达标看报告里的「§10.2 验收对照」小节，或用 `--json` 读 `acceptance.criteria`。

---

## 4. 三种场景测什么

### `auth` — 并发登录 / JWT 签发正确性

50 个线程在 `threading.Barrier` 处对齐后**同时**发起 `POST /api/auth/guest-login`。

除通用指标外，额外输出 **JWT 签发校验**：签发总数、唯一 Token 数、重复数。
并发下若出现 token 串号或重复，`重复 Token` 会 > 0、`全部唯一` 为「否」。
这是并发正确性（而非仅性能）的证据。

### `mixed` — 并发只读接口（默认）

主线程先登录一次取 Token，再由 N 个线程并发轮询三个只读接口：

- `GET /api/agent/list`
- `GET /api/help/articles?page=1&size=10`
- `GET /api/agent/persona`

每个请求带 `Authorization: Bearer <token>`。报告按接口分组给出 n / fail / avg / p95 / p99。
若 Token 传递有问题，会集中出现 **401**，一眼可见。

### `chat` — 并发真实对话

并发调用 `POST /api/chat/send`，body 为 `{"content":"...","messageType":"text"}`。
这是**唯一能验证「单次对话 ≤3s」的场景**，因为它会真正触发 Java → Python AI → LLM 全链路。
`mixed` 场景的延迟**不能**用来论证对话延迟指标。

---

## 5. 如何解读指标

### 吞吐与成功率

| 指标 | 含义 | 怎么用 |
|---|---|---|
| 总请求数 | 本轮实际完成的请求数 | 样本量。太少（如 <1000）结论不稳，建议延长 `--duration` |
| 成功 / 失败 | HTTP 200 / 其他或网络错误 | — |
| **错误率** | 失败 / 总数 | 验收要求 **0%**。>0 必须定位到具体状态码 |
| **QPS** | 完成请求数 / 墙钟耗时 | 吞吐能力。固定时长模式下含起跑对齐开销，属正常 |

### 延迟（毫秒）

| 指标 | 含义 | 怎么用 |
|---|---|---|
| 平均 | 算术平均 | **最容易被长尾掩盖，不要单独用它下结论** |
| **P50** | 中位数，一半请求快于此值 | 反映「典型用户体验」 |
| **P90 / P95** | 90% / 95% 请求快于此值 | **验收主口径**（本工具用 P95 判 ≤3000ms） |
| **P99** | 99% 请求快于此值 | 暴露长尾抖动 |
| Min / Max | 极值 | Max 异常高（如恰好 ~1s 倍数）通常是连接层问题而非业务慢 |

> 为什么用 P95 而不是平均值判「≤3 秒」：平均值会把少数超时请求稀释掉。
> P95 意味着「95% 的对话都在 3 秒内返回」，是更严格也更贴近用户感受的口径。
> 如果验收方要求更严，请改看 `--json` 输出里的 `p99` 与 `max`。

### 状态码分布

- 全是 `200` → 正常
- 出现 **401** → Token 未正确传递 / 已过期
- 出现 **404** → 路径或 `--context-path` 配错（最常见）
- 出现 **429** → 触发后端限流（`RATE_LIMIT_MAX`，默认 300 次/60 秒）。**压测时建议临时调高或关闭**，否则会把限流当成性能问题
- 出现 `网络错误` → 连接被拒 / 超时，检查服务是否被打挂或 `--timeout` 太小

### §10.2 验收对照

报告末尾自动给出三项判定：

| 判定项 | 通过条件 |
|---|---|
| 并发 ≥50 | 本轮 `--concurrency >= 50`（否则显示「本轮未覆盖」） |
| P95 ≤3000ms | 本轮 P95 ≤ 3000ms |
| 错误率 = 0 | 失败数为 0 |

---

## 6. 复现压测的标准步骤

```bash
# 1) 启动后端（需要 MySQL；详见 DEPLOYMENT.md）
cd java-backend
export DB_PASSWORD=xxx JWT_SECRET=<32位以上随机串> AI_SERVICE_URL=http://localhost:8081
mvn spring-boot:run

# 2) 确认可达
curl -s http://localhost:8080/api/agent/list

# 3) 先小规模试跑，确认无 404/401
python3 scripts/loadtest/load_test.py --scenario mixed --concurrency 5 --duration 5

# 4) 正式跑两轮
python3 scripts/loadtest/load_test.py --scenario mixed --concurrency 50 --duration 60 --json-out mixed.json
python3 scripts/loadtest/load_test.py --scenario chat  --concurrency 50 --duration 60 --json-out chat.json

# 5) 把结果填进 docs/PERFORMANCE.md 的结果表格
```

**压测前建议**：临时把 `RATE_LIMIT_ENABLED=false`（或调大 `RATE_LIMIT_MAX`），
否则 50 并发持续 60 秒会撞上限流阈值，报告里会混入大量 429。
另需注意 `chat` 场景会真实消耗 LLM Token 配额。

---

## 7. 无真实后端时：用桩服务自检脚本

真实后端未运行时，可用内置桩服务验证**压测脚本本身**是否工作：

```bash
# 终端 A：启动桩服务（人为注入 20ms 延迟，模拟后端处理耗时）
python3 stub_server.py --port 18080 --latency-ms 20

# 终端 B：对它压测（注意 --context-path ''，因为桩服务默认不带 /api 前缀）
python3 load_test.py --base-url http://127.0.0.1:18080 --context-path '' \
    --scenario mixed --concurrency 50 --duration 10
```

桩服务实现了 `Result<T>` 响应结构、JWT 签发（每次唯一）、
以及受保护接口的 `Authorization` 校验（无 Token 返回 401），
因此能真实验证 Token 传递与并发逻辑。

> ⚠️ **桩服务数据不能当作后端性能结论。** 它只是脚本自检工具。
> 真实的 §10.2 验收数据必须来自运行中的 Java 后端。

---

## 8. 实现要点（为什么这样测才可信）

1. **真并发**：N 个 `threading.Thread`，每个持有独立 `http.client` 连接，
   在 `threading.Barrier` 处对齐后同时起跑 —— 不是串行 for 循环。
2. **keep-alive 连接复用**：贴近真实用户会话，避免把 TCP 握手开销算进业务延迟。
3. **关闭 Nagle（`TCP_NODELAY`）**：否则 keep-alive 短请求会叠加 ~40ms
   延迟确认（delayed ACK），凭空制造出 40ms 的「假地板延迟」。
4. **百分位用线性插值**，与 `numpy.percentile` 默认行为一致，结果可交叉验证。
5. **失败不中断**：网络层异常被折叠为 `status=0` 的失败样本继续统计；
   连接被服务端关闭时自动重连一次。
6. **启动预检**：先做 TCP 连通性检查，不可达时立即以退出码 2 退出并给出排查建议，
   而不是让用户干等超时。
