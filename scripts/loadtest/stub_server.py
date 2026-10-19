#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知伴AI — 压测脚本自检用的本地桩服务（仅 Python 3 标准库）

存在的唯一目的：在没有真实 Java 后端的环境里，验证 `load_test.py` 本身
「能跑、能并发、能算指标」，而不是声称它可用。

它模拟了 Java 后端 `Result<T>` 的响应结构与附件一 §3.1/§3.4/§3.5 的接口：

    POST /auth/guest-login   → {"code":200,"message":"登录成功","data":{"token":"...","userId":N,...}}
    GET  /agent/list         → {"code":200,"data":[...]}
    GET  /agent/persona      → {"code":200,"data":{...}}
    GET  /help/articles      → {"code":200,"data":{"records":[...],"total":N}}

注意：**默认不带 /api 前缀**，因此对它压测时要用 `--context-path ''`。
加 `--with-context-path` 可让其监听在 /api 前缀下，用于验证前缀拼接逻辑。

用法：
    python3 stub_server.py --port 18080
    python3 stub_server.py --port 18080 --latency-ms 5 --with-context-path
"""

from __future__ import annotations

import argparse
import json
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_LATENCY_MS = 0.0
_PREFIX = ""
_COUNTER = 0
_COUNTER_LOCK = threading.Lock()


class StubHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # 启用 keep-alive，贴近真实后端
    server_version = "zhiban-stub/1.0"
    # 关闭 Nagle：否则 keep-alive 短请求会叠加 ~40ms 延迟确认（delayed ACK），
    # 让桩服务自身成为延迟瓶颈、污染压测基线。
    disable_nagle_algorithm = True

    # ── 工具 ────────────────────────────────────────────────
    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _strip_prefix(self) -> str:
        path = self.path
        if _PREFIX and path.startswith(_PREFIX):
            path = path[len(_PREFIX):]
        return path or "/"

    def _authorized(self) -> bool:
        """模拟 SecurityConfig：受保护接口必须带合法 Bearer 头。"""
        header = self.headers.get("Authorization") or ""
        return header.startswith("Bearer ") and len(header) > len("Bearer ") + 8

    def _handle(self, method: str) -> None:
        if _LATENCY_MS > 0:
            time.sleep(_LATENCY_MS / 1000.0)

        path = self._strip_prefix()
        bare = path.split("?", 1)[0]

        if method == "POST" and bare == "/auth/guest-login":
            global _COUNTER
            with _COUNTER_LOCK:
                _COUNTER += 1
                seq = _COUNTER
            # 每次签发不同 token，便于验证并发下的唯一性
            token = f"stub.jwt.{seq}.{random.getrandbits(48):012x}"
            self._send_json(
                200,
                {
                    "code": 200,
                    "message": "登录成功",
                    "data": {
                        "token": token,
                        "userId": 1000 + seq,
                        "username": f"guest_{seq}",
                        "role": "USER",
                    },
                },
            )
            return

        if method == "GET" and bare in ("/agent/list", "/agent/persona"):
            if not self._authorized():
                self._send_json(401, {"code": 401, "message": "未认证", "data": None})
                return

        if method == "GET" and bare == "/agent/list":
            self._send_json(
                200,
                {
                    "code": 200,
                    "message": "success",
                    "data": [
                        {"agentType": "elderly", "name": "银发康养智能体"},
                        {"agentType": "govpolicy", "name": "政务政策智能体"},
                        {"agentType": "tourism", "name": "文旅导览智能体"},
                    ],
                },
            )
            return

        if method == "GET" and bare == "/agent/persona":
            self._send_json(
                200,
                {
                    "code": 200,
                    "message": "success",
                    "data": {
                        "agentType": "elderly",
                        "name": "银发康养智能体",
                        "greeting": "您好，我是知伴康养助手。",
                    },
                },
            )
            return

        if method == "GET" and bare == "/help/articles":
            self._send_json(
                200,
                {
                    "code": 200,
                    "message": "success",
                    "data": {"records": [], "total": 0, "current": 1, "size": 10},
                },
            )
            return

        if method == "GET" and bare == "/actuator/health":
            self._send_json(200, {"status": "UP"})
            return

        if method == "POST" and bare == "/chat/send":
            if not self._authorized():
                self._send_json(401, {"code": 401, "message": "未认证", "data": None})
                return
            # 模拟一次 LLM 生成（延迟由 --latency-ms 控制）
            self._send_json(
                200,
                {
                    "code": 200,
                    "message": "success",
                    "data": {
                        "sessionId": 1,
                        "content": "您好，我是知伴康养助手，请问有什么可以帮您？",
                        "messageType": "text",
                    },
                },
            )
            return

        self._send_json(404, {"code": 404, "message": f"stub 未实现: {method} {bare}", "data": None})

    # ── HTTP 动词 ───────────────────────────────────────────
    def do_GET(self) -> None:  # noqa: N802
        self._handle("GET")

    def do_POST(self) -> None:  # noqa: N802
        # 读取并丢弃请求体，保证 keep-alive 连接状态正确
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        self._handle("POST")

    def log_message(self, fmt: str, *args) -> None:  # 静音，避免压测时刷屏
        pass


class StubServer(ThreadingHTTPServer):
    daemon_threads = True
    # 默认 listen backlog 只有 5；50 并发建连时会溢出并触发 ~1s SYN 重传，
    # 在 P99/max 上伪造出假尖刺。调到 256 与 Tomcat 的默认 acceptCount 同量级。
    request_queue_size = 256


def main() -> int:
    parser = argparse.ArgumentParser(description="压测自检用本地桩服务")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--latency-ms", type=float, default=0.0, help="人为注入的固定延迟")
    parser.add_argument("--with-context-path", action="store_true", help="在 /api 前缀下提供服务")
    args = parser.parse_args()

    global _LATENCY_MS, _PREFIX
    _LATENCY_MS = args.latency_ms
    _PREFIX = "/api" if args.with_context_path else ""

    server = StubServer((args.host, args.port), StubHandler)
    print(
        f"[stub] 监听 http://{args.host}:{args.port}{_PREFIX} "
        f"(latency={_LATENCY_MS}ms, keep-alive=on)",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[stub] 收到中断，退出。", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
