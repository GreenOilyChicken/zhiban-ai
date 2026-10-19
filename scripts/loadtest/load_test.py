#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知伴AI — 并发压测脚本（Python 3 标准库实现，零第三方依赖）

用途
----
为《附件一 项目功能需求清单 V1.0》§10.2 的性能验收指标提供可复现的压测能力：

    - 系统支持至少 50 个并发用户同时在线
    - 单次对话响应时间不超过 3 秒（不含网络延迟）

设计要点
--------
1. **仅用标准库**：`threading` + `http.client`，不依赖 requests / locust / aiohttp，
   保证在离线、无法 pip install 的交付环境里也能直接运行。
2. **真并发**：N 个 worker 线程各自持有独立 `http.client.HTTPConnection`
   （HTTP/1.1 keep-alive 长连接复用），在 `threading.Barrier` 处对齐后同时起跑，
   而不是串行 for 循环。
3. **固定时长 / 固定请求数** 两种驱动模式。
4. 输出 QPS、平均延迟、P50/P90/P95/P99、状态码分布、错误率；支持 `--json` 机器可读输出。
5. 目标不可达时快速失败（启动前做一次 TCP 预检），退出码非 0，并给出清晰提示。

用法示例
--------
    # 默认：50 并发跑 30 秒，混合只读场景
    python3 load_test.py --base-url http://localhost:8080 --scenario mixed

    # 登录场景，10 并发跑 5 秒
    python3 load_test.py --scenario auth --concurrency 10 --duration 5

    # 固定 2000 个请求 + JSON 输出（便于写入报告）
    python3 load_test.py --scenario mixed --requests 2000 --json

    # 对话接口（需要后端 + Python AI 服务均可用）
    python3 load_test.py --scenario chat --concurrency 10 --duration 20 \
        --chat-message "高血压老人日常饮食要注意什么？"

退出码
------
    0  压测完成（可能含请求级失败，详见报告的 error_rate）
    1  参数错误
    2  目标不可达 / 启动预检失败
    3  运行期致命错误（所有请求均未发出等）
"""

from __future__ import annotations

import argparse
import http.client
import json
import math
import os
import random
import socket
import sys
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

__version__ = "1.0.0"

# ─────────────────────────────────────────────────────────────
# 退出码
# ─────────────────────────────────────────────────────────────
EXIT_OK = 0
EXIT_BAD_ARGS = 1
EXIT_UNREACHABLE = 2
EXIT_FATAL = 3

# 压测脚本自身的 User-Agent，便于后端日志区分压测流量
USER_AGENT = f"zhiban-loadtest/{__version__} (stdlib)"

# 视为「业务成功」的 HTTP 状态码集合（3xx 由 client 自动跟随，一般不出现）
OK_STATUS = {200}


# ═════════════════════════════════════════════════════════════
# 数据模型
# ═════════════════════════════════════════════════════════════
@dataclass
class Response:
    """一次请求的观测结果。"""

    ok: bool
    status: int  # HTTP 状态码；网络层失败时为 0
    latency_ms: float
    error: Optional[str] = None
    body: bytes = b""
    headers: Dict[str, str] = field(default_factory=dict)
    endpoint: str = ""

    def json(self) -> Optional[Any]:
        try:
            return json.loads(self.body.decode("utf-8", errors="replace"))
        except Exception:
            return None


class TargetUnreachable(Exception):
    """目标主机 / 端口不可达。"""


# 后端 `server.servlet.context-path`，取自 java-backend/src/main/resources/application.yml
DEFAULT_CONTEXT_PATH = "/api"


def resolve_base_path(url_path: str, context_path: str) -> str:
    """
    决定请求要拼接的路径前缀。

    Java 后端的 context-path 是 `/api`（见 application.yml），所以：
      - `--base-url http://host:8080`        → 前缀 `/api`
      - `--base-url http://host:8080/api`    → 前缀 `/api`（避免重复成 /api/api）
      - `--base-url http://host/backend`     → 前缀 `/backend/api`（经 Nginx 转发到网关前缀时）
      - `--context-path ''`                  → 不加前缀（用于无 context-path 的桩服务）
    """
    prefix = url_path.rstrip("/")
    ctx = (context_path or "").rstrip("/")
    if ctx and not prefix.endswith(ctx):
        prefix = prefix + ctx
    return prefix


class HttpClient:
    """
    极简 HTTP/1.1 客户端，基于 `http.client`。

    每个线程持有一个实例，内部维护一条 keep-alive 连接，失败后自动重连一次。
    """

    def __init__(self, base_url: str, timeout: float, context_path: str = "/api"):
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"仅支持 http/https，收到: {base_url!r}")
        if not parsed.hostname:
            raise ValueError(f"base-url 缺少主机名: {base_url!r}")

        self.scheme = parsed.scheme
        self.host = parsed.hostname
        self.port = parsed.port or (443 if parsed.scheme == "https" else 80)
        self.base_path = resolve_base_path(parsed.path, context_path)
        self.timeout = timeout
        self._conn: Optional[http.client.HTTPConnection] = None
        self._lock = threading.Lock()

    # ── 连接管理 ────────────────────────────────────────────
    def _connect(self) -> http.client.HTTPConnection:
        if self._conn is None:
            if self.scheme == "https":
                import ssl

                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                conn: http.client.HTTPConnection = http.client.HTTPSConnection(
                    self.host, self.port, timeout=self.timeout, context=ctx
                )
            else:
                conn = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
            # 立刻建连并关闭 Nagle，避免小请求叠加 delayed-ACK 造成 ~40ms 假延迟
            conn.connect()
            if conn.sock is not None:
                try:
                    conn.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                except OSError:
                    pass
            self._conn = conn
        return self._conn

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

    # ── 请求 ────────────────────────────────────────────────
    def request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
        endpoint: str = "",
        retry_on_conn_error: bool = True,
    ) -> Response:
        """
        发起一次请求并测量端到端耗时。

        返回 Response；网络层异常被折叠为 status=0 的失败结果，不向上抛出，
        以保证压测过程中单个请求失败不会中断整个 worker。
        """
        url_path = self.base_path + path
        hdrs = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Connection": "keep-alive",
        }
        if body is not None:
            hdrs["Content-Type"] = "application/json; charset=utf-8"
        if headers:
            hdrs.update(headers)

        attempt = 0
        while True:
            attempt += 1
            started = time.perf_counter()
            try:
                conn = self._connect()
                conn.request(method, url_path, body=body, headers=hdrs)
                resp = conn.getresponse()
                raw = resp.read()
                elapsed = (time.perf_counter() - started) * 1000.0
                status = resp.status
                return Response(
                    ok=status in OK_STATUS,
                    status=status,
                    latency_ms=elapsed,
                    error=None if status in OK_STATUS else f"HTTP {status}",
                    body=raw,
                    headers={k.lower(): v for k, v in resp.getheaders()},
                    endpoint=endpoint or f"{method} {path}",
                )
            except (http.client.HTTPException, OSError, socket.error) as exc:
                elapsed = (time.perf_counter() - started) * 1000.0
                # 连接被服务端关闭 / 超时 → 丢弃旧连接，重试一次
                self.close()
                if attempt == 1 and retry_on_conn_error:
                    continue
                return Response(
                    ok=False,
                    status=0,
                    latency_ms=elapsed,
                    error=f"{type(exc).__name__}: {exc}",
                    endpoint=endpoint or f"{method} {path}",
                )


# ═════════════════════════════════════════════════════════════
# 预检：目标可达性
# ═════════════════════════════════════════════════════════════
def preflight(base_url: str, timeout: float = 3.0, context_path: str = DEFAULT_CONTEXT_PATH) -> Tuple[bool, str]:
    """
    启动前 TCP 预检 + 一次探活请求。

    返回 (ok, detail)。ok=False 时 detail 为人类可读的失败原因。
    """
    parsed = urllib.parse.urlsplit(base_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    # 1) TCP 连通性
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except socket.timeout:
        return False, f"TCP 连接超时：{host}:{port}（{timeout}s 内无响应）"
    except OSError as exc:
        return False, f"TCP 连接失败：{host}:{port} → {exc}"

    # 2) HTTP 探活（任何状态码都算「服务在监听」）
    probe_path = resolve_base_path(parsed.path, context_path) + "/actuator/health"
    url = f"{parsed.scheme}://{host}:{port}{probe_path}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, f"TCP 可达，探活 {probe_path} → HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        # 404/401 等同样说明 HTTP 服务活着
        return True, f"TCP 可达，探活 {probe_path} → HTTP {exc.code}"
    except Exception as exc:
        return True, f"TCP 可达，探活未成功（{type(exc).__name__}），继续压测"


# ═════════════════════════════════════════════════════════════
# 场景定义
# ═════════════════════════════════════════════════════════════
@dataclass
class Scenario:
    """一个压测场景：如何取 Token、每个请求打哪个接口。"""

    name: str
    description: str
    requires_token: bool
    pick: Callable[["ScenarioContext"], Tuple[str, str, Optional[bytes]]]
    # pick 返回 (endpoint_label, path, body)


class ScenarioContext:
    """worker 线程共享的运行时上下文。"""

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.token: Optional[str] = None
        self.rng = random.Random()

    def auth_header(self) -> Dict[str, str]:
        if not self.token:
            raise RuntimeError("场景需要 Token，但 token 为空")
        return {"Authorization": f"Bearer {self.token}"}


# 只读接口池（mixed 场景）—— 全部来自 AgentController / HelpCenterController
READONLY_ENDPOINTS: List[Tuple[str, str]] = [
    ("GET /api/agent/list", "/agent/list"),
    ("GET /api/help/articles", "/help/articles?page=1&size=10"),
    ("GET /api/agent/persona", "/agent/persona"),
]


def _pick_auth(ctx: ScenarioContext) -> Tuple[str, str, Optional[bytes]]:
    return ("POST /api/auth/guest-login", "/auth/guest-login", b"{}")


def _pick_mixed(ctx: ScenarioContext) -> Tuple[str, str, Optional[bytes]]:
    label, path = ctx.rng.choice(READONLY_ENDPOINTS)
    return (label, path, None)


def _pick_chat(ctx: ScenarioContext) -> Tuple[str, str, Optional[bytes]]:
    payload = json.dumps(
        {"content": ctx.args.chat_message, "messageType": "text"},
        ensure_ascii=False,
    ).encode("utf-8")
    return ("POST /api/chat/send", "/chat/send", payload)


SCENARIOS: Dict[str, Scenario] = {
    "auth": Scenario(
        name="auth",
        description="并发游客登录，验证 JWT 签发在并发下正确（唯一性 + 可解析）",
        requires_token=False,
        pick=_pick_auth,
    ),
    "mixed": Scenario(
        name="mixed",
        description="登录一次取 Token，并发混合调用只读接口（agent/list、help/articles、agent/persona）",
        requires_token=True,
        pick=_pick_mixed,
    ),
    "chat": Scenario(
        name="chat",
        description="并发调用 POST /api/chat/send（含 LLM 生成，验证 §10.2「单次对话 ≤3s」）",
        requires_token=True,
        pick=_pick_chat,
    ),
}


# ═════════════════════════════════════════════════════════════
# 压测引擎
# ═════════════════════════════════════════════════════════════
class LoadTest:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.scenario = SCENARIOS[args.scenario]
        self.ctx = ScenarioContext(args)
        self.stop_event = threading.Event()
        self.barrier = threading.Barrier(args.concurrency)
        self.lock = threading.Lock()
        self.results: List[Response] = []
        self.issued = 0  # 已发出的请求数（用于 --requests 模式的全局配额）
        self.tokens_seen: List[str] = []
        self.started_at = 0.0
        self.started_wall = ""
        self.finished_at = 0.0
        self.thread_errors: List[str] = []
        self.warmup_note: Optional[str] = None

    # ── 登录取 Token ────────────────────────────────────────
    def acquire_token(self) -> str:
        client = HttpClient(self.args.base_url, self.args.timeout, self.args.context_path)
        try:
            resp = client.request(
                "POST",
                "/auth/guest-login",
                body=b"{}",
                endpoint="POST /api/auth/guest-login",
            )
            if not resp.ok:
                raise RuntimeError(
                    f"游客登录失败：status={resp.status} error={resp.error} "
                    f"body={resp.body[:200]!r}"
                )
            payload = resp.json() or {}
            data = payload.get("data") or {}
            token = data.get("token")
            if not token:
                raise RuntimeError(
                    f"登录响应中未找到 data.token，响应片段：{resp.body[:300]!r}"
                )
            return str(token)
        finally:
            client.close()

    # ── worker ─────────────────────────────────────────────
    def _next_request_index(self) -> Optional[int]:
        """--requests 模式下分配全局请求序号；超出配额返回 None。"""
        if self.args.requests is None:
            return 0
        with self.lock:
            if self.issued >= self.args.requests:
                return None
            self.issued += 1
            return self.issued

    def worker(self, worker_id: int) -> None:
        client = HttpClient(self.args.base_url, self.args.timeout, self.args.context_path)
        local: List[Response] = []
        try:
            # 所有线程在栅栏处对齐 → 真正的同时起跑
            try:
                self.barrier.wait(timeout=max(30.0, self.args.timeout * 2))
            except threading.BrokenBarrierError:
                return

            if self.args.requests is not None:
                self._run_fixed_count(client, local)
            else:
                self._run_fixed_duration(client, local)
        except Exception as exc:  # worker 内部异常不应静默吞掉
            with self.lock:
                self.thread_errors.append(f"worker#{worker_id}: {type(exc).__name__}: {exc}")
        finally:
            client.close()
            if local:
                with self.lock:
                    self.results.extend(local)

    def _run_fixed_count(self, client: HttpClient, local: List[Response]) -> None:
        while not self.stop_event.is_set():
            if self._next_request_index() is None:
                return
            resp = self._issue(client)
            local.append(resp)

    def _run_fixed_duration(self, client: HttpClient, local: List[Response]) -> None:
        deadline = self.started_at + self.args.duration
        while not self.stop_event.is_set() and time.perf_counter() < deadline:
            resp = self._issue(client)
            local.append(resp)

    def _issue(self, client: HttpClient) -> Response:
        label, path, body = self.scenario.pick(self.ctx)
        headers = self.ctx.auth_header() if self.scenario.requires_token else None
        resp = client.request(
            "POST" if body is not None else "GET",
            path,
            body=body,
            headers=headers,
            endpoint=label,
        )
        # auth 场景：额外校验 JWT 签发正确性
        if self.scenario.name == "auth" and resp.ok:
            payload = resp.json() or {}
            token = (payload.get("data") or {}).get("token")
            if not token:
                resp.ok = False
                resp.error = "响应缺少 data.token"
            else:
                with self.lock:
                    self.tokens_seen.append(str(token))
        return resp

    # ── 主流程 ─────────────────────────────────────────────
    def run(self) -> Dict[str, Any]:
        # 0) 目标预检
        ok, detail = preflight(self.args.base_url, context_path=self.args.context_path)
        if not ok:
            print(f"[错误] 目标不可达：{self.args.base_url}", file=sys.stderr)
            print(f"       原因：{detail}", file=sys.stderr)
            print(
                "       排查建议：确认后端已启动（cd java-backend && mvn spring-boot:run），"
                "或先用 --base-url 指向可达地址。",
                file=sys.stderr,
            )
            raise TargetUnreachable(detail)

        # 1) 需要 Token 的场景：先登录一次
        if self.scenario.requires_token:
            try:
                self.ctx.token = self.acquire_token()
                print(f"[准备] 已获取 JWT（长度 {len(self.ctx.token)}），开始并发压测…")
            except Exception as exc:
                print(f"[错误] 前置登录失败：{exc}", file=sys.stderr)
                raise TargetUnreachable(str(exc))

        # 2) 起跑
        self.started_wall = time.strftime("%Y-%m-%d %H:%M:%S")
        self.started_at = time.perf_counter()
        threads = [
            threading.Thread(target=self.worker, args=(i,), name=f"lt-worker-{i}", daemon=True)
            for i in range(self.args.concurrency)
        ]
        for t in threads:
            t.start()

        # 固定时长模式下，主线程负责到点拉闸；固定请求数模式等待自然收敛
        if self.args.requests is None:
            while time.perf_counter() - self.started_at < self.args.duration:
                time.sleep(0.05)
            self.stop_event.set()

        for t in threads:
            t.join(timeout=self.args.timeout + 30)
        self.finished_at = time.perf_counter()

        return self.build_report()

    # ── 指标计算 ───────────────────────────────────────────
    @staticmethod
    def _percentile(sorted_values: List[float], pct: float) -> float:
        """线性插值百分位（与 numpy.percentile 默认行为一致）。"""
        if not sorted_values:
            return 0.0
        if len(sorted_values) == 1:
            return sorted_values[0]
        rank = (pct / 100.0) * (len(sorted_values) - 1)
        low = math.floor(rank)
        high = math.ceil(rank)
        if low == high:
            return sorted_values[int(rank)]
        frac = rank - low
        return sorted_values[low] * (1 - frac) + sorted_values[high] * frac

    def build_report(self) -> Dict[str, Any]:
        results = list(self.results)
        wall = max(self.finished_at - self.started_at, 1e-9)

        total = len(results)
        successes = sum(1 for r in results if r.ok)
        failures = total - successes
        error_rate = (failures / total) if total else 0.0

        latencies = sorted(r.latency_ms for r in results)
        # QPS 口径：完成请求数 / 实际墙钟耗时（含各线程起跑对齐开销）
        qps = total / wall

        status_counts: Dict[str, int] = {}
        for r in results:
            key = str(r.status) if r.status else "网络错误"
            status_counts[key] = status_counts.get(key, 0) + 1

        error_samples: Dict[str, int] = {}
        for r in results:
            if not r.ok:
                key = r.error or "unknown"
                error_samples[key] = error_samples.get(key, 0) + 1

        endpoint_stats: Dict[str, Dict[str, Any]] = {}
        for r in results:
            st = endpoint_stats.setdefault(
                r.endpoint, {"count": 0, "failures": 0, "latencies": []}
            )
            st["count"] += 1
            if not r.ok:
                st["failures"] += 1
            st["latencies"].append(r.latency_ms)
        endpoint_summary = {}
        for name, st in sorted(endpoint_stats.items()):
            lats = sorted(st["latencies"])
            endpoint_summary[name] = {
                "count": st["count"],
                "failures": st["failures"],
                "avg_ms": round(sum(lats) / len(lats), 2) if lats else 0.0,
                "p95_ms": round(self._percentile(lats, 95), 2),
                "p99_ms": round(self._percentile(lats, 99), 2),
            }

        # auth 场景：JWT 唯一性校验
        jwt_info: Optional[Dict[str, Any]] = None
        if self.scenario.name == "auth":
            unique = len(set(self.tokens_seen))
            jwt_info = {
                "tokens_issued": len(self.tokens_seen),
                "unique_tokens": unique,
                "duplicate_tokens": len(self.tokens_seen) - unique,
                "all_unique": unique == len(self.tokens_seen) and unique > 0,
            }

        return {
            "meta": {
                "script": "load_test.py",
                "version": __version__,
                "scenario": self.scenario.name,
                "scenario_description": self.scenario.description,
                "base_url": self.args.base_url,
                "concurrency": self.args.concurrency,
                "mode": "fixed_requests" if self.args.requests is not None else "fixed_duration",
                "duration_s": self.args.duration if self.args.requests is None else None,
                "target_requests": self.args.requests,
                "timeout_s": self.args.timeout,
                "started_at": self.started_wall,
                "context_path": self.args.context_path,
                "python": sys.version.split()[0],
                "platform": sys.platform,
            },
            "summary": {
                "total_requests": total,
                "success": successes,
                "failures": failures,
                "error_rate": round(error_rate, 6),
                "error_rate_pct": round(error_rate * 100, 4),
                "wall_time_s": round(wall, 3),
                "qps": round(qps, 2),
                "latency_ms": {
                    "min": round(latencies[0], 2) if latencies else 0.0,
                    "avg": round(sum(latencies) / total, 2) if total else 0.0,
                    "p50": round(self._percentile(latencies, 50), 2),
                    "p90": round(self._percentile(latencies, 90), 2),
                    "p95": round(self._percentile(latencies, 95), 2),
                    "p99": round(self._percentile(latencies, 99), 2),
                    "max": round(latencies[-1], 2) if latencies else 0.0,
                },
                "status_codes": dict(sorted(status_counts.items())),
            },
            "endpoints": endpoint_summary,
            "errors": dict(sorted(error_samples.items(), key=lambda kv: -kv[1])[:10]),
            "jwt": jwt_info,
            "worker_errors": self.thread_errors,
            "acceptance": self._acceptance(total, error_rate, latencies),
        }

    def _acceptance(
        self, total: int, error_rate: float, latencies: List[float]
    ) -> Dict[str, Any]:
        """对照附件一 §10.2 的判定（仅对本次压测所测接口有效）。"""
        conc_ok = self.args.concurrency >= 50
        # 「单次对话响应时间 ≤3s」以 P95 作为代表性口径，另附 P99 / max
        p95 = self._percentile(latencies, 95)
        latency_ok = bool(latencies) and p95 <= 3000.0
        error_ok = total > 0 and error_rate == 0.0
        return {
            "criteria": {
                "concurrency_ge_50": conc_ok,
                "p95_le_3000ms": latency_ok,
                "zero_errors": error_ok,
            },
            "p95_ms": round(p95, 2),
            "note": (
                "并发用户数指标需 concurrency>=50 的独立压测轮次；"
                "对话延迟指标应以 --scenario chat 的结果为准（本次场景: "
                f"{self.scenario.name}）。"
            ),
        }


# ═════════════════════════════════════════════════════════════
# 输出
# ═════════════════════════════════════════════════════════════
def render_text(report: Dict[str, Any]) -> str:
    meta = report["meta"]
    s = report["summary"]
    lat = s["latency_ms"]
    lines: List[str] = []
    add = lines.append

    add("=" * 68)
    add(" 知伴AI 并发压测报告 / zhiban-ai load_test.py")
    add("=" * 68)
    add(f"  目标地址    : {meta['base_url']}")
    add(f"  场景        : {meta['scenario']} — {meta['scenario_description']}")
    add(
        "  模式        : "
        + (
            f"固定请求数 {meta['target_requests']}"
            if meta["mode"] == "fixed_requests"
            else f"固定时长 {meta['duration_s']}s"
        )
    )
    add(f"  并发用户数  : {meta['concurrency']}")
    add(f"  请求超时    : {meta['timeout_s']}s")
    add(f"  运行环境    : Python {meta['python']} / {meta['platform']}")
    add("-" * 68)
    add("  【吞吐与成功率】")
    add(f"    总请求数    : {s['total_requests']}")
    add(f"    成功        : {s['success']}")
    add(f"    失败        : {s['failures']}")
    add(f"    错误率      : {s['error_rate_pct']}%")
    add(f"    墙钟耗时    : {s['wall_time_s']}s")
    add(f"    QPS         : {s['qps']}")
    add("-" * 68)
    add("  【延迟（毫秒）】")
    add(f"    平均        : {lat['avg']}")
    add(f"    P50         : {lat['p50']}")
    add(f"    P90         : {lat['p90']}")
    add(f"    P95         : {lat['p95']}")
    add(f"    P99         : {lat['p99']}")
    add(f"    Min / Max   : {lat['min']} / {lat['max']}")
    add("-" * 68)
    add("  【状态码分布】")
    for code, cnt in s["status_codes"].items():
        add(f"    {code:<12}: {cnt}")
    if report["endpoints"]:
        add("-" * 68)
        add("  【分接口指标】")
        for name, st in report["endpoints"].items():
            add(
                f"    {name:<32} n={st['count']:<6} fail={st['failures']:<5} "
                f"avg={st['avg_ms']}ms p95={st['p95_ms']}ms p99={st['p99_ms']}ms"
            )
    if report.get("jwt"):
        j = report["jwt"]
        add("-" * 68)
        add("  【JWT 签发校验】")
        add(f"    签发总数    : {j['tokens_issued']}")
        add(f"    唯一 Token  : {j['unique_tokens']}")
        add(f"    重复 Token  : {j['duplicate_tokens']}")
        add(f"    全部唯一    : {'是' if j['all_unique'] else '否'}")
    if report["errors"]:
        add("-" * 68)
        add("  【错误样本（Top 10）】")
        for err, cnt in report["errors"].items():
            add(f"    x{cnt:<6} {err[:120]}")
    if report["worker_errors"]:
        add("-" * 68)
        add("  【Worker 异常】")
        for e in report["worker_errors"][:10]:
            add(f"    {e}")
    add("-" * 68)
    acc = report["acceptance"]
    add("  【§10.2 验收对照】")
    add(f"    并发 ≥50          : {'通过' if acc['criteria']['concurrency_ge_50'] else '本轮未覆盖'}")
    add(f"    P95 ≤3000ms       : {'通过' if acc['criteria']['p95_le_3000ms'] else '未通过'} (实测 {acc['p95_ms']}ms)")
    add(f"    错误率 = 0        : {'通过' if acc['criteria']['zero_errors'] else '未通过'}")
    add(f"    说明              : {acc['note']}")
    add("=" * 68)
    return "\n".join(lines)


# ═════════════════════════════════════════════════════════════
# CLI
# ═════════════════════════════════════════════════════════════
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="load_test.py",
        description="知伴AI 并发压测工具（仅 Python 3 标准库）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python3 load_test.py --scenario auth --concurrency 10 --duration 5\n"
            "  python3 load_test.py --scenario mixed --concurrency 50 --duration 30\n"
            "  python3 load_test.py --scenario mixed --requests 2000 --json\n"
            "  python3 load_test.py --scenario chat --chat-message '你好' --concurrency 10\n"
        ),
    )
    p.add_argument(
        "--base-url",
        default=os.environ.get("LOADTEST_BASE_URL", "http://localhost:8080"),
        help="被测服务基址（默认 http://localhost:8080，含 context-path /api 由脚本自动拼接）",
    )
    p.add_argument(
        "--context-path",
        default=DEFAULT_CONTEXT_PATH,
        help=(
            "后端 servlet context-path（默认 /api，见 application.yml）；"
            "传空字符串 '' 表示不加前缀（用于无 context-path 的桩服务）"
        ),
    )
    p.add_argument(
        "--concurrency",
        type=int,
        default=50,
        help="并发用户数 / worker 线程数（默认 50）",
    )
    p.add_argument(
        "--duration",
        type=float,
        default=30.0,
        help="压测持续秒数（默认 30；与 --requests 互斥）",
    )
    p.add_argument(
        "--requests",
        type=int,
        default=None,
        help="固定总请求数模式（覆盖 --duration）",
    )
    p.add_argument(
        "--scenario",
        choices=sorted(SCENARIOS.keys()),
        default="mixed",
        help="压测场景：auth / mixed / chat（默认 mixed）",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="单请求超时秒数（默认 10）",
    )
    p.add_argument(
        "--chat-message",
        default="你好，请介绍一下你自己。",
        help="chat 场景发送的消息内容",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 输出完整报告（便于写入文档 / CI 断言）",
    )
    p.add_argument(
        "--json-out",
        default=None,
        help="同时把 JSON 报告写入指定文件",
    )
    p.add_argument("--version", action="version", version=f"load_test.py {__version__}")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.concurrency < 1:
        print("[错误] --concurrency 必须 ≥ 1", file=sys.stderr)
        return EXIT_BAD_ARGS
    if args.requests is not None and args.requests < 1:
        print("[错误] --requests 必须 ≥ 1", file=sys.stderr)
        return EXIT_BAD_ARGS
    if args.requests is None and args.duration <= 0:
        print("[错误] --duration 必须 > 0", file=sys.stderr)
        return EXIT_BAD_ARGS
    if args.timeout <= 0:
        print("[错误] --timeout 必须 > 0", file=sys.stderr)
        return EXIT_BAD_ARGS

    try:
        runner = LoadTest(args)
    except ValueError as exc:
        print(f"[错误] 参数无效：{exc}", file=sys.stderr)
        return EXIT_BAD_ARGS

    try:
        report = runner.run()
    except TargetUnreachable:
        return EXIT_UNREACHABLE
    except KeyboardInterrupt:
        print("\n[中断] 用户取消压测。", file=sys.stderr)
        return EXIT_FATAL
    except Exception as exc:
        print(f"[错误] 压测运行失败：{type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_FATAL

    if report["summary"]["total_requests"] == 0:
        print(
            "[错误] 未发出任何请求，请检查 --concurrency / --duration / 目标服务状态。",
            file=sys.stderr,
        )
        return EXIT_FATAL

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
        print(f"\n[输出] JSON 报告已写入 {args.json_out}")

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
