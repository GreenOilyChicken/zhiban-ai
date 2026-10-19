# 知伴AI 双端智能体平台 — API 接口文档

> **本文档依据源码实际实现编写，基线：`8653c06`**
>
> ⚠️ **基线说明**：`8653c06` 为编写时 `HEAD` 的提交哈希，
> 但当时工作区**存在未提交的改动**（`git status` 非干净）。
> 文档内容以**工作区实际文件**为准，并已在编写过程中核对到最新状态。
> 若后续源码有变更，请以源码为准并同步更新本文档。
>
> 编写方式：逐文件阅读 `java-backend/src/main/java/com/zhiban/ai/controller/` 下全部 Controller、
> `websocket/ChatWebSocketHandler.java`、`vo/Result.java`、`exception/GlobalExceptionHandler.java`、
> `config/SecurityConfig.java`、`config/RateLimitFilter.java`、`resources/application.yml`，
> 以及 Python 侧 `python/rag_server.py`、`python/config.py`、`python/voice_service.py`。
> 所有路径、参数名、字段名、错误码均以源码为准；凡与既有文档不一致之处，见文末
> [§12 已知实现差异](#12-已知实现差异)。

---

## 目录

1. [全局约定](#1-全局约定)
2. [统一响应格式](#2-统一响应格式)
3. [错误码表](#3-错误码表)
4. [认证接口 `/api/auth`](#4-认证接口-apiauth)
5. [对话接口 `/api/chat`](#5-对话接口-apichat)
6. [WebSocket 实时对话 `/api/ws/chat`](#6-websocket-实时对话-apiwschat)
7. [语音接口 `/api/voice`](#7-语音接口-apivoice)
8. [智能体接口 `/api/agent`](#8-智能体接口-apiagent)
9. [帮助中心接口（双路径）](#9-帮助中心接口双路径)
10. [管理端接口](#10-管理端接口)
11. [Python AI 服务接口 `/api/v1`](#11-python-ai-服务接口-apiv1)
12. [已知实现差异](#12-已知实现差异)
13. [附录：接口权限总表](#13-附录接口权限总表)

---

## 1. 全局约定

### 1.1 服务地址

| 服务 | 默认地址 | 说明 |
|---|---|---|
| Java 后端 | `http://localhost:8080` | `server.port=8080`，`server.servlet.context-path=/api` |
| Python AI 服务 | `http://localhost:8081` | FastAPI + uvicorn，`RAG_PORT` 默认 8081 |
| Vue 前端（开发） | `http://localhost:5173` | Vite dev server，`/api` 代理到 8080 |

**重要：`context-path = /api`。**

Java 后端所有 Controller 的 `@RequestMapping` 路径前都会自动加上 `/api` 前缀。
因此 `AuthController` 上的 `@RequestMapping("/auth")` 对外实际是 `/api/auth`。
**本文件所有 Java 接口路径均写完整路径（含 `/api` 前缀）。**

> 注意：Servlet 容器会剥离 context-path，所以 `SecurityConfig` 里的 `requestMatchers`
> 匹配的是**去掉 `/api` 之后**的路径（源码注释已明确说明）。

### 1.2 请求格式

- 除文件上传外，请求体一律为 `application/json; charset=UTF-8`。
- 文件上传使用 `multipart/form-data`。
- 时间字段序列化格式：`yyyy-MM-dd HH:mm:ss`，时区 `Asia/Shanghai`。
- 日期字段（`LocalDate`）格式：`yyyy-MM-dd`。

### 1.3 认证方式

采用 **JWT 无状态认证**（`SessionCreationPolicy.STATELESS`）。

```
Authorization: Bearer <token>
```

- Token 由 `/api/auth/login`、`/api/auth/guest-login`、`/api/auth/phone-login` 下发。
- 有效期：`jwt.expiration = 86400000` 毫秒（24 小时）。
- 解析逻辑见 `JwtAuthenticationFilter`：解析出 `userId` 作为 `Authentication.principal`，
  并授予 `ROLE_<role 大写>` 权限（如 `ROLE_ADMIN`、`ROLE_USER`）。

### 1.4 公开接口与鉴权边界

依据 `SecurityConfig.filterChain()`（下列路径**已去掉 `/api` 前缀**）：

| 匹配规则 | 放行范围 |
|---|---|
| `POST /auth/login`、`/auth/register`、`/auth/guest-login`、`/auth/phone-login`、`/auth/sms-code`、`/auth/refresh` | 完全公开 |
| `/help/articles`、`/help/article/**` | 完全公开 |
| `/help/gov-policy`、`/help/gov-policy/**` | **完全公开（含 POST，见 §12.2）** |
| `/help/categories`、`/help/faq` | 完全公开 |
| `GET /articles`、`/articles/**` | 公开（仅 GET） |
| `GET /policies`、`/policies/**` | 公开（仅 GET） |
| `/actuator/health`、`/error` | 公开（`/actuator/health` 实际不存在，见 §12.9） |
| `/ws/**` | 公开（握手鉴权由 Handler 自行处理） |
| `/admin/**` | 需要 `ADMIN` 角色（URL 级） |
| 其余所有请求 | 需要认证（`anyRequest().authenticated()`） |

管理端接口还有**第二层方法级校验**：三个 Admin Controller 类上均标注
`@PreAuthorize("hasRole('ADMIN')")`，且每个方法上重复标注一次。

### 1.5 接口频率限制（429）

`RateLimitFilter` 对**每个请求**生效：

- 限流维度：`客户端IP + HTTP方法`（固定窗口计数）。
- 默认阈值：`rate-limit.max-requests = 300` 次 / `rate-limit.window-ms = 60000` 毫秒。
- 客户端 IP 取值顺序：`X-Forwarded-For`（取第一个）→ `X-Real-IP` → `getRemoteAddr()`。
- 超限时**直接由 Filter 写出**，不走 `Result` 封装流程：

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json;charset=UTF-8

{"code":429,"message":"请求过于频繁，请稍后重试","data":null}
```

可通过环境变量关闭：`RATE_LIMIT_ENABLED=false`。

### 1.6 CORS

`SecurityConfig.corsConfigurationSource()`：

- `allowedOriginPatterns = ["*"]`
- `allowedMethods = GET, POST, PUT, DELETE, OPTIONS`
- `allowedHeaders = ["*"]`
- `allowCredentials = true`
- `maxAge = 3600`

---

## 2. 统一响应格式

所有 Controller 返回值均封装为 `com.zhiban.ai.vo.Result<T>`：

```json
{
  "code": 200,
  "message": "success",
  "data": { }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 状态码。`200` = 成功，其他 = 失败 |
| `message` | string | 提示消息 |
| `data` | T | 响应数据，可为 `null` |

`Result` 提供的静态工厂方法：

| 方法 | 产生的 `code` / `message` |
|---|---|
| `Result.success(data)` | `200` / `"success"` |
| `Result.success()` | `200` / `"success"`，`data = null` |
| `Result.success(message, data)` | `200` / 自定义 message |
| `Result.error(code, message)` | 自定义 code，`data = null` |
| `Result.error(message)` | `500` / 自定义 message |

> **重要（易踩坑）**：`application.yml` 配置了
> `spring.jackson.default-property-inclusion: non_null`。
> 因此 **`data` 为 `null` 时该字段在 JSON 中会被整个省略**，实际响应形如：
>
> ```json
> { "code": 401, "message": "未登录或登录已过期" }
> ```
>
> 客户端解析时应按「字段可能缺失」处理，不要强制断言 `data` 存在。

### 2.1 分页响应结构

分页接口返回 MyBatis-Plus 的 `IPage<T>`（`Page<T>` 实现），
经 Jackson 序列化后的**实际字段**如下（已实测验证）：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "records": [ ],
    "total": 37,
    "size": 10,
    "current": 1,
    "pages": 4
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `records` | array | 当前页数据列表 |
| `total` | number | 总记录数 |
| `size` | number | 每页条数 |
| `current` | number | 当前页码 |
| `pages` | number | 总页数 |

> 注意：**不是** Spring Data 风格的 `content` / `totalElements` / `number`。
> 前端部分页面按 `content` / `totalElements` 取值，属于实现差异，见 §12.4。

---

## 3. 错误码表

### 3.1 业务码定义

错误码由 `GlobalExceptionHandler` 与各 Service 抛出的 `BusinessException` 产生。

| code | 含义 | 触发场景 | HTTP 状态 |
|---|---|---|---|
| `200` | 成功 | — | 200 |
| `400` | 参数错误 / 业务校验失败 | `@Valid` 校验失败、`IllegalArgumentException`、`@RequestParam` 约束违反、ID 非法、未知智能体、未知集合、文件类型/大小不合法、用户名已存在、手机号已注册 | 400（`BusinessException` 为 **200**，见下） |
| `401` | 未认证 | 用户名或密码错误、Token 无效/过期、缺少 Token、验证码错误、`SecurityUtils` 取不到用户 | 401（`BusinessException` 为 **200**） |
| `403` | 权限不足 | `AccessDeniedException`、跨用户访问他人会话 | 403 |
| `404` | 资源不存在 | 文章不存在、政策文档不存在、会话不存在 | 200（`BusinessException`） |
| `429` | 请求过于频繁 / 配额耗尽 | 限流 Filter；短信验证码发送过频；政策问答配额用完 | **429**（Filter）/ 200（业务） |
| `500` | 系统内部错误 | 未捕获异常 | 500 |
| `501` | 功能未实现 | Python 侧 TTS / ASR：语音引擎未接入 | 501（Python 直出） |
| `502` | 上游服务不可用 | AI 智能体服务不可用、AI 返回内容为空、TTS/ASR 服务不可用、知识库同步/上传失败 | 200（`BusinessException`） |

### 3.2 关于 HTTP 状态码的重要说明

`GlobalExceptionHandler` 中只有部分处理方法带 `@ResponseStatus`：

| 异常 | 是否带 `@ResponseStatus` | 实际 HTTP 状态 |
|---|---|---|
| `BusinessException` | ❌ 无 | **200**（业务码在 body 里） |
| `MethodArgumentNotValidException` | ✅ `BAD_REQUEST` | 400 |
| `AccessDeniedException` | ✅ `FORBIDDEN` | 403 |
| `BadCredentialsException` | ✅ `UNAUTHORIZED` | 401 |
| `IllegalArgumentException` | ✅ `BAD_REQUEST` | 400 |
| `ConstraintViolationException` | ✅ `BAD_REQUEST` | 400 |
| `Exception`（兜底） | ✅ `INTERNAL_SERVER_ERROR` | 500 |

> **因此**：形如「文章不存在」「未登录或登录已过期」「配额已用完」这类由
> `BusinessException` 抛出的错误，**HTTP 状态码是 200**，业务码在响应体 `code` 字段里。
> 客户端必须同时判断 HTTP 状态码 **和** `body.code`。
>
> 例外：Spring Security 在 Filter 链阶段直接拒绝的请求（如未带 Token 访问 `/chat/send`）
> 会走 Spring Security 默认的 `AuthenticationEntryPoint` / `AccessDeniedHandler`，
> 返回**不带 `Result` 包装**的裸 401 / 403。

### 3.3 错误响应示例

**业务异常（HTTP 200 + code 401）：**

```json
{
  "code": 401,
  "message": "未登录或登录已过期"
}
```

**参数校验失败（HTTP 400）：**

```json
{
  "code": 400,
  "message": "页码最小为1; 每页条数最大为100"
}
```

**权限不足（HTTP 403）：**

```json
{
  "code": 403,
  "message": "权限不足，拒绝访问"
}
```

**系统异常（HTTP 500）：**

```json
{
  "code": 500,
  "message": "系统内部错误，请稍后重试"
}
```

---

## 4. 认证接口 `/api/auth`

**Controller**：`AuthController`（`@RequestMapping("/auth")`）
**Service**：`AuthServiceImpl`

### 4.1 用户名密码登录

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/auth/login` |
| 认证 | 公开 |
| 请求体 | `LoginRequest` |

**请求参数**

| 参数 | 类型 | 必填 | 校验 | 说明 |
|---|---|---|---|---|
| `username` | string | 是 | `@NotBlank`，≤64 | 用户名 |
| `password` | string | 是 | `@NotBlank`，6–64 | 密码 |

**请求示例**

```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'
```

**响应示例**

```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.xxx",
    "userId": 1,
    "username": "admin",
    "role": "ADMIN",
    "avatar": null
  }
}
```

**响应字段（`LoginVO`）**

| 字段 | 类型 | 说明 |
|---|---|---|
| `token` | string | JWT |
| `userId` | number | 用户 ID |
| `username` | string | 用户名 |
| `role` | string | `USER` / `ADMIN` |
| `avatar` | string | 头像 URL，可为 null（会被省略） |

**失败**：`code=401`「用户名或密码错误」（用户不存在或密码不匹配均返回同一文案）。

### 4.2 用户注册

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/auth/register` |
| 认证 | 公开 |
| 请求体 | `RegisterRequest` |

**请求参数**

| 参数 | 类型 | 必填 | 校验 | 说明 |
|---|---|---|---|---|
| `username` | string | 是 | `@NotBlank`，3–64，`^[a-zA-Z0-9_]+$` | 用户名 |
| `password` | string | 是 | `@NotBlank`，6–64 | 密码（BCrypt 存储） |
| `phone` | string | 否 | ≤20，`^1[3-9]\d{9}$` | 手机号 |

**请求示例**

```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"zhangsan","password":"pass1234","phone":"13800138000"}'
```

**响应示例**（`data` 为新用户 ID）

```json
{ "code": 200, "message": "注册成功", "data": 2 }
```

**副作用**：注册成功会调用 `initDefaultQuota(userId)`，为新用户初始化
`POLICY_QA` 配额：`total_amount=100`、`free_amount=10`、`used_amount=0`。
新用户角色固定为 `USER`。

**手机号存储**：手机号以 **AES-256-GCM 密文**存入 `user.phone`
（格式 `enc1:base64(iv‖ct‖tag)`），并同时写入
**HMAC-SHA256 盲索引** `user.phone_hash`（带唯一索引，用于密文下的等值查询与防重复注册）。
详见 `docs/DATABASE.md` §3.1。

**失败**：`code=400`「用户名已存在」/「手机号已被注册」。

### 4.3 游客登录

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/auth/guest-login` |
| 认证 | 公开 |
| 请求体 | 无 |

**请求示例**

```bash
curl -X POST http://localhost:8080/api/auth/guest-login
```

**响应示例**

```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiJ9...",
    "userId": 3,
    "username": "guest_a1b2c3d4e5f60718",
    "role": "USER",
    "avatar": null
  }
}
```

**实现说明**：每次调用都会**新建**一个用户记录，用户名格式为
`guest_` + UUID 前 16 位十六进制；密码写入一个随机 UUID 的 BCrypt 值（不可用于登录）；
同样初始化默认配额。

### 4.4 发送短信验证码

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/auth/sms-code` |
| 认证 | 公开 |
| 请求体 | `SmsCodeRequest` |

**请求参数**

| 参数 | 类型 | 必填 | 校验 | 说明 |
|---|---|---|---|---|
| `phone` | string | 是 | `@NotBlank`，`^1[3-9]\d{9}$` | 手机号 |

**请求示例**

```bash
curl -X POST http://localhost:8080/api/auth/sms-code \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800138000"}'
```

**响应示例**

```json
{ "code": 200, "message": "验证码已发送" }
```

> `data` 为 `null`，因 `non_null` 配置被省略。

**实现说明（`SmsCodeService`）**：

- 验证码为 6 位数字，存于**单机内存** `ConcurrentHashMap`。
- **不通过短信通道下发**，仅在服务端日志中以 `log.info` 打印（手机号已脱敏）。
- 发送间隔限制：同一手机号短时间内重复请求 → `code=429`
  「验证码发送过于频繁，请 N 秒后重试」。
- 校验失败次数上限 `MAX_ATTEMPTS = 5`；校验通过后立即失效（防重放）。

### 4.5 手机号 + 验证码登录

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/auth/phone-login` |
| 认证 | 公开 |
| 请求体 | `PhoneLoginRequest` |

**请求参数**

| 参数 | 类型 | 必填 | 校验 | 说明 |
|---|---|---|---|---|
| `phone` | string | 是 | `@NotBlank`，`^1[3-9]\d{9}$` | 手机号 |
| `code` | string | 是 | `@NotBlank`，`^\d{4,6}$` | 验证码 |

**请求示例**

```bash
curl -X POST http://localhost:8080/api/auth/phone-login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800138000","code":"123456"}'
```

**响应示例**：同 §4.1（`LoginVO`）。

**实现说明**：若该手机号**首次登录**，会自动注册用户：
用户名 `u` + 手机号，密码为随机 UUID 的 BCrypt 值，角色 `USER`，并初始化默认配额。

**失败**：`code=401`「验证码错误或已过期」。

### 4.6 刷新 Token

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/auth/refresh` |
| 认证 | 公开 |
| 请求体 | 可选，`{"token":"..."}` |

**Token 传入方式（二选一，优先取 Header）**

1. 请求头：`Authorization: Bearer <token>`
2. 请求体：`{"token": "<token>"}`

**请求示例**

```bash
# 方式一：Header
curl -X POST http://localhost:8080/api/auth/refresh \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiJ9...'

# 方式二：Body
curl -X POST http://localhost:8080/api/auth/refresh \
  -H 'Content-Type: application/json' \
  -d '{"token":"eyJhbGciOiJIUzI1NiJ9..."}'
```

**响应示例**（`TokenVO`）

```json
{
  "code": 200,
  "message": "刷新成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.yyy",
    "expiresIn": 86400000
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `token` | string | 新签发的 JWT |
| `expiresIn` | number | 有效期（毫秒），等于 `jwt.expiration` |

**失败**：`code=401`「缺少 Token」/「Token 无效或已过期，请重新登录」。

### 4.7 获取当前用户信息

| 项 | 值 |
|---|---|
| 方法 | `GET` |
| 路径 | `/api/auth/user-info` |
| 认证 | **需要登录** |
| 请求参数 | 无 |

**请求示例**

```bash
curl http://localhost:8080/api/auth/user-info \
  -H 'Authorization: Bearer <token>'
```

**响应示例**（`UserInfoVO`）

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "userId": 1,
    "username": "admin",
    "phone": null,
    "role": "ADMIN",
    "avatar": null,
    "guest": false
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `userId` | number | 用户 ID |
| `username` | string | 用户名 |
| `phone` | string | **解密后脱敏**的手机号，如 `138****8000` |
| `role` | string | `USER` / `ADMIN` |
| `avatar` | string | 头像 URL |
| `guest` | boolean | 用户名是否以 `guest_` 开头 |

> **实现说明**：`AuthServiceImpl.currentUser()` 先调用
> `phoneCryptoService.decrypt(user.getPhone())` 解密，再经 `maskPhone()` 脱敏返回。
> 数据库中不落明文手机号。

**失败**：`code=401`「未登录或登录已过期」/「用户不存在或已注销」。

---

## 5. 对话接口 `/api/chat`

**Controller**：`ChatController`（`@RequestMapping("/chat")`，类上有 `@Validated`）
**Service**：`ChatServiceImpl`
**认证**：本组**全部接口都需要登录**（`anyRequest().authenticated()`）。

### 5.1 发送文本消息

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/chat/send` |
| 认证 | 需要登录 |
| 请求体 | `ChatRequest` |

**请求参数**

| 参数 | 类型 | 必填 | 校验 | 说明 |
|---|---|---|---|---|
| `sessionId` | number | 否 | — | 会话 ID；为空则**自动创建新会话** |
| `content` | string | 是 | `@NotBlank`，≤2000 | 消息内容 |
| `messageType` | string | 否 | 默认 `"text"` | `text` / `voice` |
| `agentType` | string | 否 | — | `elderly` / `govpolicy` / `tourism`；为空则用会话默认 |

**请求示例**

```bash
curl -X POST http://localhost:8080/api/chat/send \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"content":"阿司匹林有什么注意事项？","agentType":"elderly","messageType":"text"}'
```

**响应示例**（`ChatResponse`）

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "messageId": 12,
    "sessionId": 3,
    "content": "阿司匹林主要用于……（略）",
    "role": "assistant",
    "agentType": "elderly",
    "model": null,
    "responseTime": 2381,
    "references": null
  }
}
```

**响应字段（`ChatResponse`）**

| 字段 | 类型 | 说明 |
|---|---|---|
| `messageId` | number | 助手消息落库 ID |
| `sessionId` | number | 会话 ID |
| `content` | string | AI 回复内容 |
| `role` | string | 固定 `"assistant"` |
| `agentType` | string | 实际处理该消息的智能体 |
| `model` | string | 使用的模型（当前实现未回填，为 null） |
| `responseTime` | number | 响应耗时（毫秒） |
| `references` | array | 引用知识来源（当前实现未回填，为 null） |

**实现说明**：

- 会持久化两条 `chat_message`：用户消息 + 助手消息。
- 通过 `ChatSessionMapper.touchSession` 原子递增 `message_count` 并更新 `last_message`。
- 底层调用 Python `POST /api/v1/chat`；Python 不可用时抛 `code=502`
  「AI 智能体服务暂时不可用，请稍后重试」。

### 5.2 SSE 流式发送消息

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/chat/send/stream` |
| 认证 | 需要登录 |
| 请求体 | `ChatRequest`（同 §5.1） |
| 响应类型 | `text/event-stream;charset=UTF-8` |

**请求示例**

```bash
curl -N -X POST http://localhost:8080/api/chat/send/stream \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/event-stream' \
  -d '{"content":"介绍一下西湖","agentType":"tourism"}'
```

**SSE 事件序列**

| 事件名 | data 结构 | 说明 |
|---|---|---|
| `session` | `{"sessionId":3,"agentType":"tourism"}` | 会话准备完成，前端可立即渲染 |
| `delta` | `{"content":"文本片段"}` | 增量文本，可多次出现 |
| `done` | `{"messageId":12,"sessionId":3,"agentType":"tourism","responseTime":2381}` | 流结束 |
| `error` | `{"message":"错误信息"}` | 发生异常 |

**响应示例（原始报文）**

```
event:session
data:{"sessionId":3,"agentType":"tourism"}

event:delta
data:{"content":"西湖位于杭州市"}

event:delta
data:{"content":"，是国家5A级景区。"}

event:done
data:{"messageId":12,"sessionId":3,"agentType":"tourism","responseTime":2381}
```

> **实现要点（重要）**：Java 侧当前是「**先拿到完整回复，再切片下发**」，
> 并非真正的逐 token 流式。源码注释已明确说明：
> Python 侧 `/api/v1/chat` 返回完整文本，Java 切成增量推给前端，
> 目的是保证 EventSource 兼容性与前端逐字渲染体验。
>
> 分片规则（`ChatServiceImpl.chunk`）：累积到 **≥12 字符**且在
> `。！？；\n，、：` 之一处断开，或累积到 **≥48 字符**强制断开。

### 5.3 创建会话

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/chat/session` |
| 认证 | 需要登录 |
| 请求体 | `SessionCreateRequest` |

**请求参数**

| 参数 | 类型 | 必填 | 校验 | 说明 |
|---|---|---|---|---|
| `title` | string | 否 | ≤120 | 会话标题；为空默认 `"新对话"` |
| `agentType` | string | 否 | — | `elderly` / `govpolicy` / `tourism`，默认 `elderly` |

**请求示例**

```bash
curl -X POST http://localhost:8080/api/chat/session \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"title":"长护险咨询","agentType":"govpolicy"}'
```

**响应示例**（`ChatSession` 实体）

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 4,
    "userId": 3,
    "title": "长护险咨询",
    "agentType": "govpolicy",
    "lastMessage": null,
    "messageCount": 0,
    "createTime": "2026-10-10 18:20:31",
    "updateTime": "2026-10-10 18:20:31",
    "deleted": 0
  }
}
```

### 5.4 获取会话列表

| 项 | 值 |
|---|---|
| 方法 | `GET` |
| 路径 | `/api/chat/sessions` |
| 认证 | 需要登录 |

**请求参数**

| 参数 | 类型 | 必填 | 默认 | 校验 | 说明 |
|---|---|---|---|---|---|
| `page` | int | 否 | `1` | `@Min(1)` | 页码（**从 1 开始**） |
| `size` | int | 否 | `20` | `@Min(1) @Max(100)` | 每页条数 |

**请求示例**

```bash
curl 'http://localhost:8080/api/chat/sessions?page=1&size=20' \
  -H 'Authorization: Bearer <token>'
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "records": [
      {
        "id": 4,
        "userId": 3,
        "title": "长护险咨询",
        "agentType": "govpolicy",
        "lastMessage": "长护险的申请条件包括……",
        "messageCount": 2,
        "createTime": "2026-10-10 18:20:31",
        "updateTime": "2026-10-10 18:21:02",
        "deleted": 0
      }
    ],
    "total": 1,
    "size": 20,
    "current": 1,
    "pages": 1
  }
}
```

### 5.5 获取会话历史消息

| 项 | 值 |
|---|---|
| 方法 | `GET` |
| 路径 | `/api/chat/history` |
| 认证 | 需要登录 |

**请求参数**

| 参数 | 类型 | 必填 | 默认 | 校验 | 说明 |
|---|---|---|---|---|---|
| `sessionId` | number | **是** | — | — | 会话 ID |
| `page` | int | 否 | `1` | `@Min(1)` | 页码 |
| `size` | int | 否 | `50` | `@Min(1) @Max(200)` | 每页条数 |

**请求示例**

```bash
curl 'http://localhost:8080/api/chat/history?sessionId=4&page=1&size=50' \
  -H 'Authorization: Bearer <token>'
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "records": [
      {
        "id": 21,
        "sessionId": 4,
        "userId": 3,
        "role": "user",
        "content": "长护险怎么申请？",
        "messageType": "text",
        "agentType": "govpolicy",
        "model": null,
        "tokenUsage": null,
        "responseMs": null,
        "references": null,
        "createTime": "2026-10-10 18:20:35",
        "deleted": 0
      }
    ],
    "total": 2,
    "size": 50,
    "current": 1,
    "pages": 1
  }
}
```

**失败**：若 `sessionId` 不属于当前用户 → `code=403`「无权访问该会话」（跨用户越权防护）。

### 5.6 删除会话

| 项 | 值 |
|---|---|
| 方法 | `DELETE` |
| 路径 | `/api/chat/session/{sessionId}` |
| 认证 | 需要登录 |
| 路径参数 | `sessionId`（number，必填） |

**请求示例**

```bash
curl -X DELETE http://localhost:8080/api/chat/session/4 \
  -H 'Authorization: Bearer <token>'
```

**响应示例**

```json
{ "code": 200, "message": "success" }
```

**实现说明**：逻辑删除（`chat_session.deleted = 1`），同时逻辑删除该会话下所有
`chat_message`。

**失败**：`code=404`「会话不存在」；非本人会话 → `code=403`。

---

## 6. WebSocket 实时对话 `/api/ws/chat`

**Handler**：`ChatWebSocketHandler`（`TextWebSocketHandler`）
**注册**：`WebSocketConfig` → `registry.addHandler(chatWebSocketHandler, "/ws/chat").setAllowedOriginPatterns("*")`

> 完整地址（含 context-path）：**`ws://localhost:8080/api/ws/chat`**
> 生产环境需使用 `wss://`。

**认证**：`SecurityConfig` 中 `/ws/**` 为 `permitAll`，握手阶段**不校验 JWT**，
由 Handler 自行处理（当前实现未做鉴权）。

**协议**：JSON 文本帧。

### 6.1 客户端 → 服务端

| type | 报文 | 说明 |
|---|---|---|
| `chat` | `{"type":"chat","content":"你好","agent":"elderly"}` | 发送对话消息 |
| `ping` | `{"type":"ping"}` | 心跳 |

- `content` 为空或全空白 → 返回 `error`「消息内容不能为空」。
- `agent` 缺省为 `elderly`；可选 `elderly` / `govpolicy` / `tourism`。
- 报文不是合法 JSON，或 `type` 非 `chat`/`ping` → 返回 `error`。

### 6.2 服务端 → 客户端

| type | 报文 | 说明 |
|---|---|---|
| `connected` | `{"type":"connected","sessionId":"<wsSessionId>"}` | 连接建立后立即下发 |
| `delta` | `{"type":"delta","content":"文本片段"}` | 增量文本（可多次） |
| `done` | `{"type":"done","agent":"elderly"}` | 本轮回复结束 |
| `pong` | `{"type":"pong","ts":1760000000000}` | 心跳应答 |
| `error` | `{"type":"error","message":"..."}` | 错误 |

> 注意：`connected` 事件里的 `sessionId` 是 **WebSocket 会话 ID（字符串）**，
> **不是**数据库 `chat_session.id`。`done` 事件**不返回**数据库会话 ID。

### 6.3 交互示例

```javascript
const ws = new WebSocket('ws://localhost:8080/api/ws/chat')

ws.onopen = () => {
  ws.send(JSON.stringify({ type: 'ping' }))
  ws.send(JSON.stringify({ type: 'chat', content: '高血压日常注意什么？', agent: 'elderly' }))
}

ws.onmessage = (e) => {
  const msg = JSON.parse(e.data)
  // msg.type ∈ { connected, delta, done, pong, error }
}
```

### 6.4 上下文与心跳

- **上下文**：Handler 在内存中按 WebSocket 会话维护历史（`Map<String, List<HistoryItem>>`），
  保留最近 **10 轮（20 条）**，超出后从头移除。
- **心跳**：客户端需自行定时发送 `{"type":"ping"}`，服务端回 `pong`。
- **断线重连**：服务端不主动重连，需客户端实现；连接关闭时上下文被清除。
- **分片规则**：与 §5.2 相同（≥12 字符遇标点，或 ≥48 字符）。

---

## 7. 语音接口 `/api/voice`

**Controller**：`VoiceController`（`@RequestMapping("/voice")`，类上有 `@Validated`）
**Service**：`VoiceServiceImpl` → `AiAgentClientImpl` → Python `voice_service`
**认证**：本组**全部接口都需要登录**（不在 permitAll 列表内）。

> ⚠️ **重要现状**：语音引擎尚未决策接入。Python 侧 `VOICE_PROVIDER` 默认 `none`，
> TTS / ASR 会抛 `VoiceNotImplementedError` → HTTP **501**。
> Java 侧把该异常统一包装为 `code=502`「语音合成服务暂时不可用」/「语音识别服务暂时不可用」。

### 7.1 文本转语音（TTS）

| 项 | 值 |
|---|---|
| 方法 | `GET` |
| 路径 | `/api/voice/tts` |
| 认证 | 需要登录 |
| 响应类型 | `audio/mpeg`（MP3 二进制） |

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `text` | string | 是 | 待合成文本（`@NotBlank`） |
| `speaker` | string | 否 | 发音人 ID |

**请求示例**

```bash
curl 'http://localhost:8080/api/voice/tts?text=你好&speaker=zh-CN-XiaoxiaoNeural' \
  -H 'Authorization: Bearer <token>' \
  --output tts.mp3
```

**响应**：成功时返回二进制音频流，响应头：

```
Content-Type: audio/mpeg
Content-Disposition: inline; filename="tts.mp3"
Content-Length: <字节数>
```

**实现说明**：

- Java 侧 `VoiceServiceImpl.MAX_TTS_LENGTH = 500`，超长**截断**（仅记 warn 日志，不报错）。
- Python 侧 `POST /api/v1/tts` 在 `VOICE_PROVIDER=none` 时返回 **501**。
- **前端/小程序注意**：该接口需要 `Authorization` 头。
  直接把 URL 赋给 `<audio src>` / `InnerAudioContext.src` 无法带 Token，会得到 401，见 §12.6。

### 7.2 语音识别（ASR）

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/voice/asr` |
| 认证 | 需要登录 |
| Content-Type | `multipart/form-data` |

**请求参数（表单）**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | file | 是 | 音频文件（wav / mp3 / m4a 等） |

**请求示例**

```bash
curl -X POST http://localhost:8080/api/voice/asr \
  -H 'Authorization: Bearer <token>' \
  -F 'file=@recording.mp3'
```

**响应示例**（`data` 为识别文本）

```json
{ "code": 200, "message": "success", "data": "请介绍一下高龄补贴政策" }
```

**失败**：

| 场景 | 结果 |
|---|---|
| 文件为空 | `code=400`「音频文件不能为空」 |
| 超过 10MB | `code=400`「音频文件过大，最大支持 10MB」 |
| 语音引擎未接入 | `code=502`「语音识别服务暂时不可用」 |
| 文件 >1MB（Spring 默认 multipart 上限） | HTTP 500（见 §12.8） |

### 7.3 获取发音人列表

| 项 | 值 |
|---|---|
| 方法 | `GET` |
| 路径 | `/api/voice/speakers` |
| 认证 | 需要登录 |

**请求示例**

```bash
curl http://localhost:8080/api/voice/speakers -H 'Authorization: Bearer <token>'
```

**响应示例**（`data` 为 Python 侧 `speakers` 数组，直接透传）

```json
{
  "code": 200,
  "message": "success",
  "data": [
    { "id": "zh-CN-XiaoxiaoNeural", "name": "晓晓", "gender": "female", "selected": true }
  ]
}
```

**实现说明**：Python 侧 `/api/v1/speakers` 返回
`{"speakers":[...],"enabled":bool,"provider":"none"}`，Java 侧只取 `speakers` 数组。
Python 不可用时，`AiAgentClientImpl.listSpeakers()` 降级返回 `{"speakers":[]}`。

### 7.4 切换发音人

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/voice/speakers` |
| 认证 | 需要登录 |
| 参数位置 | **Query String** |

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `speaker` | string | 是 | 发音人 ID（`@NotBlank`） |

**请求示例**

```bash
curl -X POST 'http://localhost:8080/api/voice/speakers?speaker=zh-CN-YunxiNeural' \
  -H 'Authorization: Bearer <token>'
```

**响应示例**

```json
{ "code": 200, "message": "切换成功" }
```

**失败**：`code=400`「未知发音人: xxx」（校验依据 Python 返回的 `speakers` 列表）。

> ⚠️ **实现现状**：`AiAgentClientImpl.switchSpeaker()` **只打印一行日志，不做任何实际切换**；
> Python 侧也**没有** `POST /api/v1/speakers` 端点。
> 因此该接口仅做参数校验后即返回成功，**不产生持久效果**，见 §12.7。

### 7.5 查询当前发音人

| 项 | 值 |
|---|---|
| 方法 | `GET` |
| 路径 | `/api/voice/speakers/current` |
| 认证 | 需要登录 |

**请求示例**

```bash
curl http://localhost:8080/api/voice/speakers/current -H 'Authorization: Bearer <token>'
```

**响应示例**

```json
{ "code": 200, "message": "success", "data": "zh-CN-XiaoxiaoNeural" }
```

**实现说明**：从发音人列表中找 `selected == true` 的项并返回其 `id`；
找不到或解析失败时返回**空字符串 `""`**。

---

## 8. 智能体接口 `/api/agent`

**Controller**：`AgentController`（`@RequestMapping("/agent")`）
**认证**：本组**全部接口都需要登录**。

### 8.1 获取智能体列表

| 项 | 值 |
|---|---|
| 方法 | `GET` |
| 路径 | `/api/agent/list` |
| 认证 | 需要登录 |

**请求示例**

```bash
curl http://localhost:8080/api/agent/list -H 'Authorization: Bearer <token>'
```

**响应示例**（`List<AgentPersona>`）

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1,
      "agentType": "elderly",
      "name": "银发康养助手",
      "personality": "你是知伴AI银发康养助手，用通俗易懂、耐心温和的语言服务老年用户。……",
      "greeting": "您好，我是知伴AI康养助手。可以帮您查询用药注意事项、慢病护理建议、康复计划，或者了解长护险政策。请问有什么可以帮您？",
      "description": "用药指导、护理建议、康复计划、长护险申请",
      "enabled": 1,
      "sortOrder": 1,
      "createTime": "2026-10-10 17:00:00",
      "updateTime": "2026-10-10 17:00:00"
    }
  ]
}
```

### 8.2 获取智能体人设

| 项 | 值 |
|---|---|
| 方法 | `GET` |
| 路径 | `/api/agent/persona` |
| 认证 | 需要登录 |

**请求参数**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `agentType` | string | 否 | 服务端默认智能体 | `elderly` / `govpolicy` / `tourism` |

**请求示例**

```bash
curl 'http://localhost:8080/api/agent/persona?agentType=govpolicy' \
  -H 'Authorization: Bearer <token>'
```

**响应示例**：`data` 为单个 `AgentPersona` 对象（结构同 §8.1 中一项）。

### 8.3 切换智能体

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/agent/switch/{agentType}` |
| 认证 | 需要登录 |
| 路径参数 | `agentType`（string，必填） |

**请求示例**

```bash
curl -X POST http://localhost:8080/api/agent/switch/tourism \
  -H 'Authorization: Bearer <token>'
```

**响应示例**

```json
{
  "code": 200,
  "message": "切换成功",
  "data": { "id": 3, "agentType": "tourism", "name": "文旅导览助手", "...": "..." }
}
```

**失败**：非法 `agentType` → `code=400`
「未知智能体: xxx，可用值: elderly / govpolicy / tourism」。

> **实现说明**：该接口是无状态的——只校验并返回目标智能体的人设配置，
> **不在服务端保存"当前智能体"**。客户端需自行记住当前选择
> （小程序存在 `wx.setStorageSync('agentType', ...)`）。

---

## 9. 帮助中心接口（双路径）

**Controller**：`HelpCenterController`
**认证**：混合，见下表。

### 9.1 双路径注册说明（务必阅读）

该 Controller **不使用类级 `@RequestMapping` 前缀**，而是通过方法级
`@GetMapping({...})` 为同一功能**同时注册两套路径**：

- **附件一 §3.5 规范路径**（需求文档验收口径）
- **兼容别名路径**（前端 `vue-frontend/src/api/help.js` 与微信小程序历史版本在用）

源码注释原文：

> 附件一 §3.5 规定的是 `/api/articles`、`/api/policies`、`/api/quota`；
> 而前端与小程序历史版本使用 `/api/help/*`。为保证「按需求文档验收」与
> 「既有客户端不破坏」同时成立，每个接口同时注册两套路径。

**路径对照表（以源码 `@GetMapping` 为准）**

| 功能 | 规范路径（附件一） | 兼容别名 | 认证 |
|---|---|---|---|
| 文章列表 | `GET /api/articles` | `GET /api/help/articles` | 公开 |
| 文章详情 | `GET /api/articles/{id}` | `GET /api/help/article/{id}` | 公开 |
| 相关推荐 | `GET /api/articles/{id}/related` | `GET /api/help/article/{id}/related` | 公开 |
| 政策列表 | `GET /api/policies` | `GET /api/help/gov-policy` | 公开 |
| 政策详情 | `GET /api/policies/{id}` | `GET /api/help/gov-policy/{id}` | 公开 |
| 政策问答 | `POST /api/policies/ask` | `POST /api/help/gov-policy/ask` | **见 §9.6** |
| 用户配额 | `GET /api/quota` | `GET /api/help/quota` | 需要登录 |
| FAQ | —（**无规范路径**） | `GET /api/help/faq` | 公开 |
| 分类列表 | —（**无规范路径**） | `GET /api/help/categories` | 公开 |

> ⚠️ **注意不对称之处**：
> 1. `FAQ` 与 `分类列表` **只有 `/api/help/*` 一套路径**，没有规范路径别名。
> 2. 文章详情：规范路径是复数 `{id}`（`/articles/{id}`），
>    但兼容别名是**单数** `article`（`/help/article/{id}`）——这是源码事实，
>    前端 `getArticleDetail()` 用的正是单数别名。
> 3. `related` 同理：`/articles/{id}/related` vs `/help/article/{id}/related`。

### 9.2 文章列表

| 项 | 值 |
|---|---|
| 方法 | `GET` |
| 路径 | `/api/articles` **或** `/api/help/articles` |
| 认证 | 公开 |

**请求参数**

| 参数 | 类型 | 必填 | 默认 | 校验 | 说明 |
|---|---|---|---|---|---|
| `page` | int | 否 | `1` | `@Min(1)` | 页码（**从 1 开始**） |
| `size` | int | 否 | `10` | `@Min(1) @Max(100)` | 每页条数 |
| `category` | string | 否 | — | — | 分类精确匹配 |
| `keyword` | string | 否 | — | — | **标题**模糊搜索 |

**请求示例**

```bash
curl 'http://localhost:8080/api/articles?page=1&size=10&category=老年人&keyword=康复'
```

**响应示例**（`IPage<HelpArticleVO>`）

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "records": [
      {
        "id": 1,
        "title": "老年人冬季防跌倒指南",
        "content": "<p>正文……</p>",
        "category": "老年人",
        "coverImage": null,
        "videoUrl": null,
        "tags": ["防跌倒", "冬季"],
        "isPublished": 1,
        "createTime": "2026-10-10 17:00:00",
        "updateTime": "2026-10-10 17:00:00"
      }
    ],
    "total": 1,
    "size": 10,
    "current": 1,
    "pages": 1
  }
}
```

**实现说明**：仅返回 `deleted = 0 AND is_published = 1` 的文章，
排序 `ORDER BY create_time DESC`。`tags` 由逗号分隔字符串解析为数组。

### 9.3 文章详情

| 项 | 值 |
|---|---|
| 方法 | `GET` |
| 路径 | `/api/articles/{id}` **或** `/api/help/article/{id}` |
| 认证 | 公开 |
| 路径参数 | `id`（number，必填） |

**请求示例**

```bash
curl http://localhost:8080/api/help/article/1
```

**响应示例**：`data` 为单个 `HelpArticleVO`（结构同 §9.2 中一项）。

**失败**：

| 场景 | 结果 |
|---|---|
| `id <= 0` 或 null | `code=400`「文章ID无效」 |
| 不存在 / 已逻辑删除 | `code=404`「文章不存在」 |

> ⚠️ **实现现状**：`getArticleById` **不校验 `is_published`**。
> 源码注释明确说明「此处不做角色判断，由 Controller 的公开/保护路由决定可见性」。
> 而该路由是公开的，因此**未发布的文章（`is_published=0`）也能被任何人按 ID 读取**，
> 见 §12.3。

### 9.4 相关推荐文章

| 项 | 值 |
|---|---|
| 方法 | `GET` |
| 路径 | `/api/articles/{id}/related` **或** `/api/help/article/{id}/related` |
| 认证 | 公开 |

**请求参数**

| 参数 | 类型 | 必填 | 默认 | 校验 | 说明 |
|---|---|---|---|---|---|
| `id` | number | 是（路径） | — | — | 当前文章 ID |
| `limit` | int | 否 | `5` | `@Min(1) @Max(20)` | 返回条数 |

**请求示例**

```bash
curl 'http://localhost:8080/api/articles/1/related?limit=5'
```

**响应示例**（`List<HelpArticleVO>`，注意**不是分页对象**）

```json
{
  "code": 200,
  "message": "success",
  "data": [ { "id": 2, "title": "……", "category": "老年人" } ]
}
```

**策略**：优先取同分类的其他已发布文章；不足 `limit` 时用最新其他已发布文章补齐并去重；
结果**排除当前文章自身**。

### 9.5 政策列表

| 项 | 值 |
|---|---|
| 方法 | `GET` |
| 路径 | `/api/policies` **或** `/api/help/gov-policy` |
| 认证 | 公开 |
| 绑定对象 | `GovPolicyQuery`（**Query String 绑定，非 JSON**） |

**请求参数（`GovPolicyQuery`）**

| 参数 | 类型 | 必填 | 默认 | 校验 | 说明 |
|---|---|---|---|---|---|
| `page` | int | 否 | `1` | `@Min(1)` | 页码 |
| `size` | int | 否 | `10` | `@Min(1) @Max(100)` | 每页条数 |
| `policyType` | string | 否 | — | — | 政策类型**精确匹配** |
| `keyword` | string | 否 | — | — | 模糊匹配 **title / summary / issuing_authority** |
| `status` | int | 否 | — | — | `0`=失效 `1`=有效 |
| `region` | string | 否 | — | — | 适用地区**模糊匹配** |

> ⚠️ **没有 `category` 参数**。前端部分页面传 `category`，会被静默忽略，见 §12.5。

**请求示例**

```bash
curl 'http://localhost:8080/api/policies?page=1&size=10&policyType=养老&status=1&region=浙江'
```

**响应示例**（`IPage<GovPolicyVO>`）

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "records": [
      {
        "id": 1,
        "docNumber": "浙政发〔2026〕1号",
        "title": "关于推进养老服务高质量发展的实施意见",
        "issuingAuthority": "浙江省人民政府",
        "policyType": "养老",
        "effectiveDate": "2026-03-01",
        "publishDate": "2026-02-10",
        "region": "浙江省",
        "status": 1,
        "summary": "……",
        "fullText": "……",
        "keyPoints": ["要点一", "要点二"],
        "faq": [ { "question": "如何申请？", "answer": "……" } ],
        "createTime": "2026-10-10 17:00:00",
        "updateTime": "2026-10-10 17:00:00"
      }
    ],
    "total": 1,
    "size": 10,
    "current": 1,
    "pages": 1
  }
}
```

**字段映射提示（易错）**：`GovPolicyVO` 的字段名与前端部分页面使用的名称**不一致**：

| 前端部分页面使用 | 后端 `GovPolicyVO` 实际字段 |
|---|---|
| `documentNumber` | `docNumber` |
| `category` | `policyType` |
| `content` | `fullText` |
| `expiryDate` | **不存在**（无该字段） |

**实现说明**：仅返回 `deleted = 0` 的记录，排序 `ORDER BY publish_date DESC, create_time DESC`。
`keyPoints` 与 `faq` 由 JSON 字符串解析为数组（解析失败时返回空集合）。

### 9.6 政策智能问答

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/policies/ask` **或** `/api/help/gov-policy/ask` |
| 认证 | **需要登录（业务层强制）** |
| 请求体 | `PolicyQuestionRequest` |

**请求参数**

| 参数 | 类型 | 必填 | 校验 | 说明 |
|---|---|---|---|---|
| `question` | string | 是 | `@NotBlank` | 用户问题 |
| `policyType` | string | 否 | — | 政策类型筛选（作为向量检索的 `filter`） |

**请求示例**

```bash
curl -X POST http://localhost:8080/api/help/gov-policy/ask \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"question":"高龄补贴如何申请？"}'
```

**响应示例**（`PolicyAnswerVO`）

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "answer": "根据《……》，高龄补贴的申请流程如下：……",
    "sources": [
      {
        "id": 1,
        "title": "关于推进养老服务高质量发展的实施意见",
        "docNumber": "浙政发〔2026〕1号",
        "issuingAuthority": "浙江省人民政府",
        "score": 0.86
      }
    ]
  }
}
```

**响应字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `answer` | string | AI 生成的回答 |
| `sources` | array | 引用的政策文档来源列表 |
| `sources[].id` | number | 政策文档 ID |
| `sources[].title` | string | 标题 |
| `sources[].docNumber` | string | 文号 |
| `sources[].issuingAuthority` | string | 发文机关 |
| `sources[].score` | number | 相似度分数 |

**处理流程（`HelpCenterServiceImpl.askPolicyQuestion`）**

1. 取当前用户 ID（未登录 → `code=401`「未登录或登录已过期」）。
2. **先原子扣减配额**：`deductQuota(userId, "POLICY_QA")`。
   使用 SQL `UPDATE ... WHERE used_amount < total_amount`，返回 0 行即配额不足。
3. 配额不足 → `code=429`「您的政策问答配额已用完，请明日再来或联系管理员」。
4. 扣减成功后调用 `RagService.searchAndAnswer(question, policyType)`。

**配额不足响应示例**

```json
{
  "code": 429,
  "message": "您的政策问答配额已用完，请明日再来或联系管理员"
}
```

> ⚠️ **鉴权不对称（重要）**：`SecurityConfig` 中
> `/help/gov-policy` 与 `/help/gov-policy/**` 是 **`permitAll`（不限方法）**，
> 所以 `POST /api/help/gov-policy/ask` 在 URL 层是**放行**的；
> 而规范路径 `POST /api/policies/ask` 落到 `anyRequest().authenticated()`，需要 Token。
> 两者最终都会因业务层的 `getCurrentUserId()` 而要求登录，
> 但**拒绝方式不同**：别名路径返回 HTTP 200 + `code=401`，
> 规范路径返回 Spring Security 的 HTTP 401。详见 §12.2。

### 9.7 政策详情

| 项 | 值 |
|---|---|
| 方法 | `GET` |
| 路径 | `/api/policies/{id}` **或** `/api/help/gov-policy/{id}` |
| 认证 | 公开 |
| 路径参数 | `id`（number，必填） |

**请求示例**

```bash
curl http://localhost:8080/api/help/gov-policy/1
```

**响应示例**：`data` 为单个 `GovPolicyVO`（结构同 §9.5 中一项）。

**失败**：`code=400`「政策文档ID无效」/ `code=404`「政策文档不存在」。

### 9.8 FAQ 列表

| 项 | 值 |
|---|---|
| 方法 | `GET` |
| 路径 | **仅** `/api/help/faq`（无规范路径别名） |
| 认证 | 公开 |

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `policyType` | string | 否 | 政策类型筛选 |

**请求示例**

```bash
curl 'http://localhost:8080/api/help/faq?policyType=养老'
```

**响应示例**（`List<GovPolicyVO>`，**非分页**）

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1,
      "title": "关于推进养老服务高质量发展的实施意见",
      "policyType": "养老",
      "faq": [
        { "question": "高龄补贴如何申请？", "answer": "……" }
      ]
    }
  ]
}
```

**实现说明**：仅取 `status = 1`（有效）且 `faq IS NOT NULL AND faq != '[]'` 的政策，
SQL 只 `SELECT id, title, faq, policy_type`，因此其余字段为 null 并在 JSON 中被省略。

### 9.9 用户配额查询

| 项 | 值 |
|---|---|
| 方法 | `GET` |
| 路径 | `/api/quota` **或** `/api/help/quota` |
| 认证 | **需要登录** |

**请求参数**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `quotaType` | string | 否 | `POLICY_QA` | 配额类型 |

**请求示例**

```bash
curl 'http://localhost:8080/api/quota?quotaType=POLICY_QA' \
  -H 'Authorization: Bearer <token>'
```

**响应示例**（`QuotaVO`）

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "userId": 3,
    "quotaType": "POLICY_QA",
    "totalAmount": 100,
    "usedAmount": 4,
    "remainingAmount": 96,
    "freeAmount": 10
  }
}
```

**字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `remainingAmount` | number | `totalAmount - usedAmount` |
| `freeAmount` | number | 免费配额 |

**实现说明**：若该用户该类型配额不存在，会调用
`initQuotaIfAbsent` 自动创建（默认 `total=100`、`free=10`、`used=0`）。

### 9.10 分类列表

| 项 | 值 |
|---|---|
| 方法 | `GET` |
| 路径 | **仅** `/api/help/categories`（无规范路径别名） |
| 认证 | 公开 |

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `type` | string | 否 | `POLICY` / `HELP` |

**请求示例**

```bash
curl 'http://localhost:8080/api/help/categories?type=POLICY'
```

**响应示例**（`List<CategoryVO>`）

```json
{
  "code": 200,
  "message": "success",
  "data": [
    { "id": 1, "name": "养老", "type": "POLICY", "sortOrder": 1 },
    { "id": 2, "name": "旅游", "type": "POLICY", "sortOrder": 2 }
  ]
}
```

---

## 10. 管理端接口

> **所有管理端接口都需要 `ADMIN` 角色**，且为 **URL 级（`/admin/**` → `hasRole("ADMIN")`）
> + 方法级（`@PreAuthorize("hasRole('ADMIN')")`）双重校验**。
> 非 ADMIN 用户访问 → HTTP 403 / `code=403`「权限不足，拒绝访问」。

### 10.1 文章管理

**Controller**：`AdminHelpController`（`@RequestMapping("/admin/help")`）

#### 10.1.1 创建文章

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/admin/help/article` |
| 认证 | ADMIN |
| 请求体 | `HelpArticleRequest` |

**请求参数**

| 参数 | 类型 | 必填 | 校验 | 说明 |
|---|---|---|---|---|
| `title` | string | 是 | `@NotBlank`，≤256 | 标题 |
| `content` | string | 是 | `@NotBlank` | 正文（富文本/Markdown） |
| `category` | string | 是 | `@NotBlank`，≤64 | 分类 |
| `coverImage` | string | 否 | ≤512 | 封面图 URL |
| `videoUrl` | string | 否 | ≤512 | 视频 URL |
| `tags` | string | 否 | ≤512 | 标签（**逗号分隔字符串**） |
| `isPublished` | int | 否 | 默认 `0` | `0`=未发布 `1`=已发布 |

> ⚠️ **没有 `author` 字段**。前端 `AdminArticle.vue` 提交了 `author`，会被忽略，见 §12.5。

**请求示例**

```bash
curl -X POST http://localhost:8080/api/admin/help/article \
  -H 'Authorization: Bearer <admin-token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "title":"老年人冬季防跌倒指南",
    "content":"<p>正文……</p>",
    "category":"老年人",
    "tags":"防跌倒,冬季",
    "isPublished":1
  }'
```

**响应示例**

```json
{ "code": 200, "message": "创建成功", "data": 7 }
```

#### 10.1.2 更新文章

| 项 | 值 |
|---|---|
| 方法 | `PUT` |
| 路径 | `/api/admin/help/article/{id}` |
| 认证 | ADMIN |
| 路径参数 | `id`（number，必填） |
| 请求体 | `HelpArticleRequest`（同 §10.1.1，全量覆盖） |

**请求示例**

```bash
curl -X PUT http://localhost:8080/api/admin/help/article/7 \
  -H 'Authorization: Bearer <admin-token>' \
  -H 'Content-Type: application/json' \
  -d '{"title":"新标题","content":"<p>新正文</p>","category":"老年人","isPublished":1}'
```

**响应示例**

```json
{ "code": 200, "message": "success" }
```

**失败**：`code=404`「文章不存在」。

#### 10.1.3 删除文章

| 项 | 值 |
|---|---|
| 方法 | `DELETE` |
| 路径 | `/api/admin/help/article/{id}` |
| 认证 | ADMIN |
| 路径参数 | `id`（number，必填） |

**请求示例**

```bash
curl -X DELETE http://localhost:8080/api/admin/help/article/7 \
  -H 'Authorization: Bearer <admin-token>'
```

**响应示例**

```json
{ "code": 200, "message": "success" }
```

**实现说明**：**逻辑删除**（`help_content.deleted = 1`），数据仍在库中。

### 10.2 政策管理

**Controller**：`AdminHelpController`（`@RequestMapping("/admin/help")`）

#### 10.2.1 创建政策

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/admin/help/gov-policy` |
| 认证 | ADMIN |
| 请求体 | `GovPolicyRequest` |

**请求参数**

| 参数 | 类型 | 必填 | 校验 | 说明 |
|---|---|---|---|---|
| `docNumber` | string | 否 | ≤128 | 文号 |
| `title` | string | 是 | `@NotBlank`，≤512 | 标题 |
| `issuingAuthority` | string | 否 | ≤256 | 发文机关 |
| `policyType` | string | 是 | `@NotBlank`，≤64 | 政策类型 |
| `effectiveDate` | string(date) | 否 | — | 生效日期 `yyyy-MM-dd` |
| `publishDate` | string(date) | 否 | — | 发布日期 `yyyy-MM-dd` |
| `region` | string | 否 | ≤128 | 适用地区 |
| `status` | int | 否 | — | `0`=失效 `1`=有效；**为空时后端默认写入 `1`** |
| `summary` | string | 否 | — | 摘要 |
| `fullText` | string | 否 | — | 全文 |
| `keyPoints` | string | 否 | — | 要点列表（**JSON 数组字符串**，如 `["要点一"]`） |
| `faq` | string | 否 | — | 常见问题（**JSON 数组字符串**） |
| `vectorId` | string | 否 | — | 向量库 ID |

> ⚠️ 前端 `AdminPolicy.vue` 提交的是 `documentNumber` / `category` / `content` / `expiryDate`，
> **均不是本接口的字段名**，见 §12.5。

**请求示例**

```bash
curl -X POST http://localhost:8080/api/admin/help/gov-policy \
  -H 'Authorization: Bearer <admin-token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "docNumber":"浙政发〔2026〕1号",
    "title":"关于推进养老服务高质量发展的实施意见",
    "issuingAuthority":"浙江省人民政府",
    "policyType":"养老",
    "publishDate":"2026-02-10",
    "effectiveDate":"2026-03-01",
    "region":"浙江省",
    "status":1,
    "summary":"……",
    "fullText":"……",
    "keyPoints":"[\"要点一\",\"要点二\"]",
    "faq":"[{\"question\":\"如何申请？\",\"answer\":\"……\"}]",
    "vectorId":"gov-policy-001"
  }'
```

**响应示例**

```json
{ "code": 200, "message": "创建成功", "data": 9 }
```

#### 10.2.2 更新政策

| 项 | 值 |
|---|---|
| 方法 | `PUT` |
| 路径 | `/api/admin/help/gov-policy/{id}` |
| 认证 | ADMIN |
| 路径参数 | `id`（number，必填） |
| 请求体 | `GovPolicyRequest`（全量覆盖） |

**响应示例**

```json
{ "code": 200, "message": "success" }
```

**失败**：`code=404`「政策文档不存在」。

#### 10.2.3 删除政策

| 项 | 值 |
|---|---|
| 方法 | `DELETE` |
| 路径 | `/api/admin/help/gov-policy/{id}` |
| 认证 | ADMIN |
| 路径参数 | `id`（number，必填） |

**响应示例**

```json
{ "code": 200, "message": "success" }
```

**实现说明**：逻辑删除。

### 10.3 配额管理

**Controller**：`AdminQuotaController`（`@RequestMapping("/admin/quota")`）

#### 10.3.1 查询配额列表

| 项 | 值 |
|---|---|
| 方法 | `GET` |
| 路径 | `/api/admin/quota` |
| 认证 | ADMIN |

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `userId` | number | 否 | 按用户过滤；为空查全部 |
| `quotaType` | string | 否 | 按类型过滤；为空查全部 |

**请求示例**

```bash
curl 'http://localhost:8080/api/admin/quota?userId=3&quotaType=POLICY_QA' \
  -H 'Authorization: Bearer <admin-token>'
```

**响应示例**（`List<QuotaVO>`，**非分页**）

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1,
      "userId": 3,
      "quotaType": "POLICY_QA",
      "totalAmount": 100,
      "usedAmount": 4,
      "remainingAmount": 96,
      "freeAmount": 10
    }
  ]
}
```

**排序**：`ORDER BY user_id ASC, quota_type ASC`。

#### 10.3.2 调整配额

| 项 | 值 |
|---|---|
| 方法 | `PUT` |
| 路径 | `/api/admin/quota/{userId}/{quotaType}` |
| 认证 | ADMIN |
| 请求体 | `QuotaAdjustRequest` |

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `userId` | number | 是 | 用户 ID |
| `quotaType` | string | 是 | 配额类型，如 `POLICY_QA` |

**请求参数（`QuotaAdjustRequest`，三字段均为可选）**

| 参数 | 类型 | 必填 | 校验 | 说明 |
|---|---|---|---|---|
| `totalAmount` | int | 否 | `@Min(0)` | 新总配额；`null` = 不修改 |
| `usedAmount` | int | 否 | `@Min(0)` | 新已用配额；`null` = 不修改 |
| `freeAmount` | int | 否 | `@Min(0)` | 新免费配额；`null` = 不修改 |

**请求示例**

```bash
curl -X PUT http://localhost:8080/api/admin/quota/3/POLICY_QA \
  -H 'Authorization: Bearer <admin-token>' \
  -H 'Content-Type: application/json' \
  -d '{"totalAmount":200,"usedAmount":0,"freeAmount":20}'
```

**响应示例**（返回调整后的 `QuotaVO`）

```json
{
  "code": 200,
  "message": "配额调整成功",
  "data": {
    "id": 1,
    "userId": 3,
    "quotaType": "POLICY_QA",
    "totalAmount": 200,
    "usedAmount": 0,
    "remainingAmount": 200,
    "freeAmount": 20
  }
}
```

**实现说明**：

- 若该用户该类型配额不存在，先 `initQuotaIfAbsent` 创建再调整。
- 字段为 `null` 时保持原值不变。
- 全量更新后重新查询返回。

**失败**：`quotaType` 为空 → `code=400`。

### 10.4 知识库管理

**Controller**：`AdminKnowledgeController`（`@RequestMapping("/admin/kb")`）

**可用集合（`COLLECTIONS`，与 Python 侧 `COLLECTION_MAP` 对齐）**：
`govpolicy` / `elderly` / `tourism`

#### 10.4.1 同步（重建）知识库索引

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/admin/kb/sync` |
| 认证 | ADMIN |
| 参数位置 | **Query String** |

**请求参数**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `collection` | string | 否 | `govpolicy` | 集合名：`govpolicy` / `elderly` / `tourism` |
| `rebuild` | boolean | 否 | `true` | `true`=清库全量重建；`false`=增量更新 |

**请求示例**

```bash
curl -X POST 'http://localhost:8080/api/admin/kb/sync?collection=govpolicy&rebuild=true' \
  -H 'Authorization: Bearer <admin-token>'
```

**响应示例**（`data` 为 Python 侧返回的 message）

```json
{ "code": 200, "message": "success", "data": "知识库构建成功: govpolicy" }
```

**失败**：

| 场景 | 结果 |
|---|---|
| 未知集合 | `code=400`「未知集合: xxx，可用值: govpolicy / elderly / tourism」 |
| Python 服务不可用 | `code=502`「知识库同步失败：AI 服务不可用或构建出错」 |

#### 10.4.2 上传知识库文档

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/admin/kb/upload` |
| 认证 | ADMIN |
| Content-Type | `multipart/form-data` |

**请求参数（表单）**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `file` | file | 是 | — | 文档文件，**仅 `.txt` / `.md` / `.markdown`**，UTF-8，≤5MB |
| `collection` | string | 否 | `govpolicy` | 目标集合 |
| `rebuild` | boolean | 否 | `true` | 上传后是否立即重建索引 |

**请求示例**

```bash
curl -X POST http://localhost:8080/api/admin/kb/upload \
  -H 'Authorization: Bearer <admin-token>' \
  -F 'file=@policy-2026.md' \
  -F 'collection=govpolicy' \
  -F 'rebuild=true'
```

**响应示例**

```json
{ "code": 200, "message": "success", "data": "文件已上传并同步知识库: policy-2026.md" }
```

**服务端校验（`AdminKnowledgeController`）**

| 校验项 | 失败结果 |
|---|---|
| 文件为空 | `code=400`「上传文件不能为空」 |
| 大小 > 5MB | `code=400`「文件过大，上限 5MB」 |
| 文件名为空 | `code=400`「文件名不能为空」 |
| 扩展名不在白名单 | `code=400`「仅支持 .txt / .md 文档」 |
| 未知集合 | `code=400`「未知集合: xxx，可用值: govpolicy / elderly / tourism」 |
| 读取失败 | `code=400`「读取上传文件失败: …」 |
| Python 上传失败 | `code=502`「文档上传失败：AI 服务不可用或文件不被接受」 |

**安全处理**：文件名会剥离所有路径成分（`\` 和 `/` 之后的部分），
防止目录穿越；Python 侧再做一次 `Path(...).name` 与目录归属二次校验。

> ⚠️ **Spring multipart 默认上限为 1MB**，而本接口声明允许 5MB。
> 超过 1MB 的文件会在进入 Controller 之前被 Spring 拒绝，
> 抛 `MaxUploadSizeExceededException`，落到兜底处理器 → **HTTP 500 + code=500**，
> 而不是预期的 400。详见 §12.8。

---

## 11. Python AI 服务接口 `/api/v1`

**服务**：`python/rag_server.py`（FastAPI，`title="知伴AI 智能体与RAG服务"`, `version="1.1.0"`）
**默认端口**：8081（`RAG_PORT`）
**调用方**：Java 后端通过 `AiAgentClientImpl` + `AiServiceConfig` 调用；
`ai-service.base-url` 默认 `http://localhost:8081`。

> **鉴权说明**：Python 侧**不校验 JWT**，仅支持可选的 `X-API-Key` / `Authorization: Bearer`
> 头（由 `ai-service.api-key` / `rag.api-key` 配置）。
> 这些接口**不应直接暴露到公网**，应由 Java 后端或内网网关保护。

> **错误格式差异**：Python 侧使用 FastAPI 默认错误格式，与 Java 的 `Result` **不同**：
>
> ```json
> { "detail": "错误信息" }
> ```

### 11.1 健康检查

| 项 | 值 |
|---|---|
| 方法 | `GET` |
| 路径 | `/api/v1/health` |

**响应示例**

```json
{
  "status": "ok",
  "service": "zhiban-ai-agent",
  "version": "1.1.0",
  "llmProvider": "deepseek",
  "collections": ["govpolicy", "elderly", "tourism"],
  "loaded": ["govpolicy"]
}
```

| 字段 | 说明 |
|---|---|
| `llmProvider` | 当前 LLM Provider（`deepseek`/`openai`/`qwen`/`codebuddy`） |
| `collections` | 支持的集合列表 |
| `loaded` | 已加载进缓存的向量库集合 |

### 11.2 向量检索

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/v1/search` |
| 请求体 | `SearchRequest` |

**请求参数**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `query` | string | 是 | — | 检索文本，最大 10000 字符 |
| `topK` | int | 否 | `5` | 返回结果数量 |
| `collection` | string | 否 | `govpolicy` | 集合名 |
| `filter` | object | 否 | — | 元数据过滤，如 `{"policy_type":"养老"}` |

**请求示例**

```bash
curl -X POST http://localhost:8081/api/v1/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"高龄补贴","topK":5,"collection":"govpolicy"}'
```

**响应示例**（`SearchResponse`）

```json
{
  "results": [
    {
      "vectorId": "policy-2026-001.md",
      "score": 0.0,
      "content": "……知识片段……",
      "metadata": { "source": "policy-2026-001.md", "category": "silver_economy" }
    }
  ],
  "total": 1
}
```

**字段说明**

| 字段 | 说明 |
|---|---|
| `vectorId` | 优先取元数据 `vector_id`，否则取 `source`（**已剥离路径，仅文件名**） |
| `score` | 取元数据 `score`，**缺失时为 `0.0`**（见 §12.10） |
| `content` | 知识片段正文 |
| `metadata` | 元数据；`source` 会被规范化为纯文件名 |

**失败**：`query` 为空 → HTTP 400 `{"detail":"query不能为空"}`；
`query` 超长 → HTTP 400 `{"detail":"query过长，最大10000字符"}`。

**降级行为**：向量库不可用时**不报错**，返回 `{"results":[],"total":0}`。

### 11.3 构建知识库

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/v1/build` |
| 请求体 | `BuildRequest` |

**请求参数**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `collection` | string | 否 | `govpolicy` | 集合名 |
| `rebuild` | boolean | 否 | `false` | `true`=清库全量重建 |

**请求示例**

```bash
curl -X POST http://localhost:8081/api/v1/build \
  -H 'Content-Type: application/json' \
  -d '{"collection":"elderly","rebuild":true}'
```

**响应示例**（`BuildResponse`）

```json
{ "success": true, "message": "知识库构建成功: elderly", "collection": "elderly" }
```

**失败**：未知集合 → HTTP 400 `{"detail":"未知集合: xxx"}`；
构建异常 → HTTP 500 `{"detail":"构建失败: …"}`。

### 11.4 上传知识库文档

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/v1/kb/upload` |
| Content-Type | `multipart/form-data` |

**请求参数（表单）**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `file` | file | 是 | — | 仅 `.txt` / `.md` / `.markdown`，≤5MB，必须 UTF-8 |
| `collection` | string | 否 | `govpolicy` | 目标集合 |
| `rebuild` | boolean | 否 | `true` | 上传后是否重建索引 |

**响应示例**：同 `BuildResponse`。

```json
{ "success": true, "message": "文件已上传并同步知识库: policy.md", "collection": "govpolicy" }
```

**失败**

| 场景 | 结果 |
|---|---|
| 未知集合 | 400 `{"detail":"未知集合: xxx"}` |
| 文件名为空 | 400 `{"detail":"文件名不能为空"}` |
| 不支持的类型 | 400 `{"detail":"不支持的文件类型: .pdf，仅支持 ['.md', '.markdown', '.txt']"}` |
| 文件为空 | 400 `{"detail":"文件内容为空"}` |
| 文件过大 | 400 `{"detail":"文件过大（N 字节），上限 5242880 字节"}` |
| 非 UTF-8 | 400 `{"detail":"文件必须为 UTF-8 编码的文本"}` |
| 无有效文本 | 400 `{"detail":"文件无有效文本内容"}` |
| 非法文件名 | 400 `{"detail":"非法文件名"}` |
| 保存失败 | 500 `{"detail":"保存文件失败: …"}` |
| 重建失败 | 500 `{"detail":"文件已保存，但重建索引失败: …"}` |

### 11.5 智能体列表

| 项 | 值 |
|---|---|
| 方法 | `GET` |
| 路径 | `/api/v1/agents` |

**响应示例**

```json
{
  "agents": [
    { "key": "elderly", "name": "银发康养智能体", "desc": "用药指导、护理建议、康复计划、长护险" },
    { "key": "govpolicy", "name": "政务政策智能体", "desc": "政策检索、培训台账" },
    { "key": "tourism", "name": "文旅导览智能体", "desc": "景点导览、路线规划、文化故事" }
  ]
}
```

### 11.6 智能体对话

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/v1/chat` |
| 请求体 | `ChatRequest` |

**请求参数**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `message` | string | 是 | — | 用户消息 |
| `agent` | string | 否 | `elderly` | `elderly` / `govpolicy` / `tourism` |
| `history` | array | 否 | — | `[{"role":"user","content":"…"}]`，**只取最后 20 条** |
| `sessionId` | string | 否 | — | 会话 ID（当前实现未使用） |

**agent 别名映射（`AGENT_ALIASES`）**

| 输入 | 归一化为 |
|---|---|
| `elderly` / `elderly_care` / `health` / `康养` / `银发` | `elderly` |
| `govpolicy` / `gov` / `government` / `policy` / `政务` | `govpolicy` |
| `tourism` / `travel` / `文旅` | `tourism` |
| 其他任意值 | `elderly`（**兜底，不报错**） |

**请求示例**

```bash
curl -X POST http://localhost:8081/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"高血压日常注意什么？","agent":"elderly","history":[]}'
```

**响应示例**（`ChatResponse`）

```json
{
  "content": "高血压患者日常应注意……",
  "agent": "elderly",
  "model": "deepseek",
  "references": []
}
```

| 字段 | 说明 |
|---|---|
| `content` | 智能体回复 |
| `agent` | 实际使用的智能体 |
| `model` | 取自 `config.LLM_PROVIDER` |
| `references` | 引用来源（当前实现**恒为空数组**） |

**失败**：`message` 为空 → 400 `{"detail":"message不能为空"}`；
智能体初始化失败 → 503 `{"detail":"智能体不可用: …"}`；
对话异常 → 500 `{"detail":"对话失败: …"}`。

### 11.7 智能体对话（SSE 流式）

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/v1/chat/stream` |
| 响应类型 | `text/event-stream` |

**请求体**：同 §11.6。

**SSE 事件格式**

```
data: {"delta":"文本片段","done":false,"agent":"tourism"}

data: {"delta":"","done":true,"agent":"tourism"}
```

| 字段 | 说明 |
|---|---|
| `delta` | 文本片段 |
| `done` | 是否结束 |
| `agent` | 智能体标识 |
| `error` | 出错时的错误信息（存在即表示失败） |

**响应头**：`Cache-Control: no-cache`、`X-Accel-Buffering: no`。

**失败**：`message` 为空 → 400 `{"detail":"message不能为空"}`。

### 11.8 发音人列表

| 项 | 值 |
|---|---|
| 方法 | `GET` |
| 路径 | `/api/v1/speakers` |

**响应示例**

```json
{
  "speakers": [
    { "id": "zh-CN-XiaoxiaoNeural", "name": "晓晓", "gender": "female", "selected": true }
  ],
  "enabled": false,
  "provider": "none"
}
```

| 字段 | 说明 |
|---|---|
| `speakers` | 发音人目录（与具体引擎无关，已先行固定） |
| `enabled` | `provider != "none"` |
| `provider` | `VOICE_PROVIDER`，默认 `none` |

> **没有 `POST /api/v1/speakers` 端点**。

### 11.9 文本转语音（TTS）

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/v1/tts` |
| 请求体 | `{"text":"...","speaker":"..."}` |

**响应**：成功时返回 `audio/mpeg` 二进制流，
响应头 `Content-Disposition: inline; filename="tts.mp3"`。

**当前状态（重要）**：`VOICE_PROVIDER` 默认 `none`，语音引擎未接入，
调用会抛 `VoiceNotImplementedError` → **HTTP 501**：

```json
{ "detail": "TTS 功能尚未启用：语音方案（第三方云服务 / 自建部署）待确认。当前 VOICE_PROVIDER=none" }
```

**失败**

| 场景 | 结果 |
|---|---|
| `text` 为空 | 400 `{"detail":"text不能为空"}` |
| 引擎未接入 | **501**（如上） |
| 参数非法 | 400 |
| 合成异常 | 500 `{"detail":"TTS失败: …"}` |
| 无音频返回 | 500 `{"detail":"TTS 未返回音频"}` |

### 11.10 语音识别（ASR）

| 项 | 值 |
|---|---|
| 方法 | `POST` |
| 路径 | `/api/v1/asr` |
| Content-Type | `multipart/form-data` |
| 表单参数 | `file`（音频文件，必填） |

**响应示例（成功）**

```json
{ "text": "请介绍一下高龄补贴政策" }
```

**当前状态**：同 TTS，`VOICE_PROVIDER=none` 时返回 **HTTP 501**：

```json
{ "detail": "ASR 功能尚未启用：语音方案（第三方云服务 / 自建部署）待确认。当前 VOICE_PROVIDER=none" }
```

**失败**：文件为空 → 400 `{"detail":"音频文件为空"}`；读取失败 → 400；
识别异常 → 500 `{"detail":"ASR失败: …"}`。

### 11.11 启动时自动建库

`startup_event` 在服务启动时执行：若环境变量 `KB_AUTO_BUILD`（默认 `true`）为真，
则为**尚无数据**的 collection 自动构建索引（已存在的跳过，保证幂等）。
设为 `false` 可跳过，改用 `POST /api/v1/build` 手动构建。

---

## 12. 已知实现差异

以下条目均为**阅读源码时发现的、文档/前端/后端之间不一致之处**，如实记录，供交付说明与后续修复参考。

> ### ⚠️ 第二轮修复说明（阅读本章前必读）
>
> 本文档初稿基于 commit `8653c06` 的工作区快照编写。此后项目进行了
> **第二轮需求补齐与缺陷修复**，本章部分条目**已不再成立**。对应关系如下：
>
> | 条目 | 第二轮状态 |
> |---|---|
> | 12.1 默认管理员账号 | ✅ 已修复（哈希校正为可登录，含回归用例）|
> | 12.2 政策问答两套路径鉴权不一致 | ⚠️ 仍存在（`/help/gov-policy/**` 为不限方法放行）|
> | 12.3 未发布文章可匿名读取 | ⚠️ 仍存在 |
> | 12.4 分页字段名/页码不匹配 | ✅ 已修复（统一为 1 基页码，兼容 `records`/`content`）|
> | 12.5 前端字段名与 DTO/VO 不一致 | ✅ 已修复（政策/文章字段已对齐，含发布开关）|
> | 12.6 语音接口裸 URL 无 Token | ✅ 已修复（支持查询参数 `token`）|
> | 12.7 切换发音人无实际效果 | ⚠️ 仍存在 |
> | 12.8 multipart 上限冲突 | ✅ 已修复（配置 10MB，超限返回 400）|
> | 12.9 `/actuator/health` 不存在 | ✅ 已修复（新增 `GET /api/health`）|
> | 12.10 向量 `score` 恒为 0 | ✅ 已修复（距离→相似度换算 + 阈值兜底 + 关键词切分）|
> | 12.11 SSE 非真流式 | ⚠️ 仍存在 |
> | 12.12 WebSocket 会话 ID 差异 | ⚠️ 仍存在 |
>
> 另：本轮新增的接口（`/api/articles/{id}/related`、`/api/admin/quota`、
> `/api/admin/kb/upload`、`/api/admin/kb/sync`、`/api/health`）已在上文各章补齐，
> 并以 **🆕 第二轮新增** 标注。

### 12.1 默认管理员账号（已验证可用）

- `schema.sql` 与 `schema-h2.sql` 中的默认管理员为 **`admin` / `admin123`**，
  角色 `ADMIN`。
- 种子哈希为
  `$2a$10$KqJA7uOT0CcRpebowhg45u/m3GQ3dqpf/HkTdgXzlF1Onsit34gAy`，
  **长度为 60**（合法 BCrypt）。
- 使用与项目相同的
  `org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder` 实测：
  ```
  stored length = 60
  admin123 -> matches=true
  ```
- 即默认管理员可正常登录，管理端接口可用。

> 生产环境请务必修改默认密码。

### 12.2 政策问答两套路径的鉴权方式不一致

`SecurityConfig` 中：

```java
.requestMatchers("/help/gov-policy", "/help/gov-policy/**").permitAll()   // 不限方法
.requestMatchers(HttpMethod.GET, "/policies", "/policies/**").permitAll() // 仅 GET
```

- `POST /api/help/gov-policy/ask` → URL 层**放行**，最终由业务层
  `getCurrentUserId()` 抛 `BusinessException(401)` → **HTTP 200 + `code=401`**。
- `POST /api/policies/ask` → 不匹配任何 permitAll，落到
  `anyRequest().authenticated()` → **Spring Security 直接返回 HTTP 401**（无 `Result` 包装）。

两者都要求登录，但**响应形态不同**，客户端需要分别兼容。

### 12.3 未发布的帮助文章可被匿名读取

`HelpCenterServiceImpl.getArticleById()` 只校验 `deleted`，**不校验 `is_published`**；
源码注释说明这是有意为之（"由 Controller 的公开/保护路由决定可见性"），
但该路由（`GET /api/articles/{id}` 与 `GET /api/help/article/{id}`）是**公开**的。
因此任何人拿到 ID 即可读取 `is_published = 0` 的草稿文章。

### 12.4 分页字段名不匹配（前端）

后端返回 `{records, total, size, current, pages}`，但部分前端页面按
Spring Data 风格取值：

| 文件 | 取值方式 | 结果 |
|---|---|---|
| `ArticleList.vue` | `res.data?.content \|\| res.data?.records` | ✅ 有 `records` 兜底 |
| `AdminArticle.vue` | 同上 | ✅ |
| `AdminPolicy.vue` | 同上 | ✅ |
| `PolicyList.vue` | 同上 | ✅ |
| `HelpCenter.vue` | `res.data?.content \|\| res.data` | ⚠️ 无 `records` 兜底，会拿到整个分页对象 |

另：`totalElements` 在全部页面均不存在，实际应读 `total`（多数页面有 `total` 兜底）。

### 12.5 前端提交/读取的字段名与后端 DTO/VO 不一致

**页码从 0 开始 vs 后端要求 ≥1**

以下页面传 `page: currentPage - 1`，首页时为 **`page=0`**，
而后端 `@Min(1)` → `ConstraintViolationException` → **HTTP 400 + `code=400`「页码最小为1」**：

- `ArticleList.vue`、`AdminArticle.vue`、`AdminPolicy.vue`、`HelpCenter.vue`（`loadGovPolicies` / `loadSilverPolicies` / `loadArticles`）
- `Home.vue` 与 `PolicyQA.vue` 传的是 `page: 1`，正常。

**文章：`author` 字段不存在**

- `AdminArticle.vue` 提交 `author`，`HelpArticleRequest` **无此字段**，被静默忽略。
- 且表单**未提交 `isPublished`**，`HelpArticleRequest.isPublished` 默认 `0`，
  新建文章恒为「未发布」，不会出现在用户端列表（用户端只查 `is_published = 1`）。
- `ArticleDetail.vue` / `ArticleList.vue` 读取 `article.author`、`article.updatedAt`、`article.createdAt`，
  而后端 `HelpArticleVO` 只有 `createTime` / `updateTime`，这些字段恒为空。

**政策：字段名整体错位**

| `AdminPolicy.vue` / `PolicyList.vue` 使用 | 后端 `GovPolicyRequest` / `GovPolicyVO` |
|---|---|
| `documentNumber` | `docNumber` |
| `category` | `policyType` |
| `content` | `fullText` |
| `expiryDate` | **不存在** |

后果：政策列表页多列显示为空；新建/编辑政策时 `title` 能写入，
但文号、类型、正文均丢失（`policyType` 为 `@NotBlank`，会直接 400 校验失败）。

**政策列表筛选参数无效**

`HelpCenter.vue` 与 `PolicyList.vue` 传 `category`，但 `GovPolicyQuery` **只有 `policyType`**，
该参数被静默忽略，筛选不生效。

### 12.6 语音接口需要 Token，但前端/小程序以裸 URL 访问

`/api/voice/**` 均需登录（`anyRequest().authenticated()`），但：

- `vue-frontend/src/api/auth.js` 的 `ttsUrl()` 返回 `/api/voice/tts?...`，
  直接用于 `audio.src` 时**不带 `Authorization` 头** → 401。
- 微信小程序 `chat.js` 的 `speak()`：`this.audioCtx.src = apiBaseUrl + '/voice/tts?text=...'`，
  同样不带 Token → 401。

（小程序 `uploadAudio()` 走 `wx.uploadFile` 并手动附加了 `Authorization` 头，ASR 路径正常。）

### 12.7 切换发音人接口无实际效果

- `AiAgentClientImpl.switchSpeaker()` 仅 `log.info` 后返回，**不改变任何状态**。
- Python 侧**没有** `POST /api/v1/speakers` 端点。
- 因此 `POST /api/voice/speakers` 只做发音人存在性校验，返回「切换成功」但无副作用。

### 12.8 multipart 大小上限冲突

- `AdminKnowledgeController` 声明允许上传 ≤5MB。
- `VoiceServiceImpl` 声明音频 ≤10MB。
- 但 `application.yml` **未配置** `spring.servlet.multipart.max-file-size` /
  `max-request-size`，使用 Spring Boot 默认值 **1MB**。
- 后果：1MB–5MB 的文档上传、1MB–10MB 的音频上传会在进入 Controller 前被拒绝，
  抛 `MaxUploadSizeExceededException`；该异常**未被 `GlobalExceptionHandler` 单独处理**，
  落到 `Exception` 兜底 → **HTTP 500 + `code=500`「系统内部错误」**，
  而非预期的 400 提示。

### 12.9 `/actuator/health` 实际不存在

`SecurityConfig` 放行了 `/actuator/health`，但 `pom.xml` **未引入
`spring-boot-starter-actuator`**，`application.yml` 也无 `management` 配置。
该端点实际返回 404。健康检查应改用 Python 侧 `GET /api/v1/health`。

### 12.10 向量检索的 `score` 恒为 0，政策问答实际走关键词兜底

- `build_kb._load_documents()` 写入的元数据只有 `source` 与 `category`，
  **没有 `score`，也没有 `vector_id`**。
- `rag_server.search()` 返回 `score=float(metadata.get("score", 0.0))` → **恒为 `0.0`**；
  `vectorId` 退化为 `source`（文件名）。
- Java `RagService` 用 `score >= ragConfig.getScoreThreshold()`（默认 **0.75**）过滤，
  且通过 `selectByVectorIds(vectorIds)` 用**文件名**去匹配 `gov_policy_document.vector_id`。
- 后果：向量路径几乎必然被过滤为空 → 降级到 `keywordFallbackAnswer()`
  （按 `title` / `summary` / `full_text` 做 `LIKE` 检索）。
  即**政策问答当前实质是关键词检索 + LLM 生成**，而非向量召回。
- 另注：`query_knowledge_base()` 内部调用的是
  `similarity_search_with_score()`，Chroma 返回的是**距离**（越小越相似），
  与「分数越大越相似」的阈值语义相反，即使回填分数也需重新定义阈值口径。

### 12.11 SSE 并非真正的 token 级流式

`ChatServiceImpl.sendStream()` 源码注释已明确：Java 侧先调用 Python
`/api/v1/chat`（**非流式**）拿到完整回复，再在本地切片下发。
Python 侧虽提供真正的流式端点 `/api/v1/chat/stream`，但 Java 未使用。

### 12.12 WebSocket 会话 ID 与数据库会话 ID 不同

- `ChatWebSocketHandler` 的 `connected` 事件返回的是 **WebSocket 会话 ID（字符串）**。
- `done` 事件只回 `agent`，**不回数据库 `chat_session.id`**。
- 且 WebSocket 对话**不落库**（`ChatWebSocketHandler` 直接调用 `AiAgentClient`，
  不经 `ChatService`），因此 WS 通道的对话不会出现在 `/api/chat/history` 中。

---

## 13. 附录：接口权限总表

| # | 方法 | 完整路径 | 认证 | Controller |
|---|---|---|---|---|
| 1 | POST | `/api/auth/login` | 公开 | AuthController |
| 2 | POST | `/api/auth/register` | 公开 | AuthController |
| 3 | POST | `/api/auth/guest-login` | 公开 | AuthController |
| 4 | POST | `/api/auth/sms-code` | 公开 | AuthController |
| 5 | POST | `/api/auth/phone-login` | 公开 | AuthController |
| 6 | POST | `/api/auth/refresh` | 公开 | AuthController |
| 7 | GET | `/api/auth/user-info` | 登录 | AuthController |
| 8 | POST | `/api/chat/send` | 登录 | ChatController |
| 9 | POST | `/api/chat/send/stream` | 登录 | ChatController |
| 10 | POST | `/api/chat/session` | 登录 | ChatController |
| 11 | GET | `/api/chat/sessions` | 登录 | ChatController |
| 12 | GET | `/api/chat/history` | 登录 | ChatController |
| 13 | DELETE | `/api/chat/session/{sessionId}` | 登录 | ChatController |
| 14 | WS | `/api/ws/chat` | 无（Handler 自行处理） | ChatWebSocketHandler |
| 15 | GET | `/api/voice/tts` | 登录 | VoiceController |
| 16 | POST | `/api/voice/asr` | 登录 | VoiceController |
| 17 | GET | `/api/voice/speakers` | 登录 | VoiceController |
| 18 | POST | `/api/voice/speakers` | 登录 | VoiceController |
| 19 | GET | `/api/voice/speakers/current` | 登录 | VoiceController |
| 20 | GET | `/api/agent/list` | 登录 | AgentController |
| 21 | GET | `/api/agent/persona` | 登录 | AgentController |
| 22 | POST | `/api/agent/switch/{agentType}` | 登录 | AgentController |
| 23 | GET | `/api/articles` | 公开 | HelpCenterController |
| 24 | GET | `/api/help/articles` | 公开 | HelpCenterController |
| 25 | GET | `/api/articles/{id}` | 公开 | HelpCenterController |
| 26 | GET | `/api/help/article/{id}` | 公开 | HelpCenterController |
| 27 | GET | `/api/articles/{id}/related` | 公开 | HelpCenterController |
| 28 | GET | `/api/help/article/{id}/related` | 公开 | HelpCenterController |
| 29 | GET | `/api/policies` | 公开 | HelpCenterController |
| 30 | GET | `/api/help/gov-policy` | 公开 | HelpCenterController |
| 31 | GET | `/api/policies/{id}` | 公开 | HelpCenterController |
| 32 | GET | `/api/help/gov-policy/{id}` | 公开 | HelpCenterController |
| 33 | POST | `/api/policies/ask` | 登录 | HelpCenterController |
| 34 | POST | `/api/help/gov-policy/ask` | URL 放行 / 业务需登录 | HelpCenterController |
| 35 | GET | `/api/help/faq` | 公开 | HelpCenterController |
| 36 | GET | `/api/quota` | 登录 | HelpCenterController |
| 37 | GET | `/api/help/quota` | 登录 | HelpCenterController |
| 38 | GET | `/api/help/categories` | 公开 | HelpCenterController |
| 39 | POST | `/api/admin/help/article` | ADMIN | AdminHelpController |
| 40 | PUT | `/api/admin/help/article/{id}` | ADMIN | AdminHelpController |
| 41 | DELETE | `/api/admin/help/article/{id}` | ADMIN | AdminHelpController |
| 42 | POST | `/api/admin/help/gov-policy` | ADMIN | AdminHelpController |
| 43 | PUT | `/api/admin/help/gov-policy/{id}` | ADMIN | AdminHelpController |
| 44 | DELETE | `/api/admin/help/gov-policy/{id}` | ADMIN | AdminHelpController |
| 45 | GET | `/api/admin/quota` | ADMIN | AdminQuotaController |
| 46 | PUT | `/api/admin/quota/{userId}/{quotaType}` | ADMIN | AdminQuotaController |
| 47 | POST | `/api/admin/kb/sync` | ADMIN | AdminKnowledgeController |
| 48 | POST | `/api/admin/kb/upload` | ADMIN | AdminKnowledgeController |
| 49 | GET | `/api/v1/health` | 内网 | rag_server.py |
| 50 | POST | `/api/v1/search` | 内网 | rag_server.py |
| 51 | POST | `/api/v1/build` | 内网 | rag_server.py |
| 52 | POST | `/api/v1/kb/upload` | 内网 | rag_server.py |
| 53 | GET | `/api/v1/agents` | 内网 | rag_server.py |
| 54 | POST | `/api/v1/chat` | 内网 | rag_server.py |
| 55 | POST | `/api/v1/chat/stream` | 内网 | rag_server.py |
| 56 | GET | `/api/v1/speakers` | 内网 | rag_server.py |
| 57 | POST | `/api/v1/tts` | 内网（当前 501） | rag_server.py |
| 58 | POST | `/api/v1/asr` | 内网（当前 501） | rag_server.py |
