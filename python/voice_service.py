"""
voice_service — 语音能力（TTS / ASR）

当前状态
------------------------------------------------------------------
TTS  ✅ 已接入：默认走 edge-tts（无需密钥），配置阿里云 NLS 密钥后优先走云端。
ASR  ⚠️ 待实现：接口契约已固定，但引擎未接入，`_transcribe_impl` 抛
     VoiceNotImplementedError，由 HTTP 层转 501 Not Implemented。

两者相互独立：TTS 已可用不影响 ASR 仍为 501。

ASR 候选方案（供决策参考）
------------------------------------------------------------------
  A. 第三方云服务：阿里云 NLS、腾讯云 ASR、讯飞
     - 优点：准确率高、支持实时流式
     - 缺点：按量计费、依赖公网
  B. 自建部署：FunASR、Whisper / faster-whisper
     - 优点：可控、离线可用
     - 缺点：需算力，长音频延迟较高

待决策后，只需在本文件内实现 `_transcribe_impl` 函数，接口与调用方无需改动。

统一约定
------------------------------------------------------------------
- 发音人目录（VOICE_CATALOG）与切换逻辑已实现，与具体引擎无关
- 未实现的能力抛 VoiceNotImplementedError，由 HTTP 层转 501 Not Implemented，
  错误信息中说明「待确认语音方案」，便于前端友好提示
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# 语音引擎标识：none = 未接入（默认）；后续可设为 aliyun / tencent / selfhosted
VOICE_PROVIDER = os.getenv("VOICE_PROVIDER", "edge").lower()


class VoiceNotImplementedError(RuntimeError):
    """语音能力尚未接入具体实现"""

    def __init__(self, capability: str):
        self.capability = capability
        super().__init__(
            f"{capability} 功能尚未启用：语音方案（第三方云服务 / 自建部署）待确认。"
            f"当前 VOICE_PROVIDER={VOICE_PROVIDER}"
        )


# ── 发音人目录（与引擎无关，可先行固定）──────────────────

# 默认发音人：甜美年轻女声，贴近"小芯"人设
DEFAULT_VOICE = os.getenv("TTS_VOICE", "zh-CN-XiaoxiaoNeural")

# 说明：此处 id 采用通用命名。确定引擎后需映射为对应厂商的发音人编码。
VOICE_CATALOG = [
    {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓（女声·甜美）", "gender": "female", "default": True},
    {"id": "zh-CN-XiaoyiNeural", "name": "晓伊（女声·活泼）", "gender": "female"},
    {"id": "zh-CN-YunxiNeural", "name": "云希（男声·阳光）", "gender": "male"},
    {"id": "zh-CN-YunjianNeural", "name": "云健（男声·沉稳）", "gender": "male"},
    {"id": "zh-CN-YunyangNeural", "name": "云扬（男声·播音）", "gender": "male"},
    {"id": "zh-CN-liaoning-XiaobeiNeural", "name": "晓北（女声·东北）", "gender": "female"},
    {"id": "zh-CN-shaanxi-XiaoniNeural", "name": "晓妮（女声·陕西）", "gender": "female"},
]

_current_voice = DEFAULT_VOICE


def is_voice_enabled() -> bool:
    """语音能力是否已接入实际实现"""
    return VOICE_PROVIDER != "none"


def list_voices() -> list[dict]:
    """返回可用发音人列表，并标注当前选中项"""
    result = []
    for v in VOICE_CATALOG:
        item = dict(v)
        item["selected"] = (v["id"] == _current_voice)
        result.append(item)
    return result


def get_current_voice() -> str:
    return _current_voice


def set_voice(voice: str) -> str:
    """切换发音人（校验合法性）"""
    global _current_voice
    known = {v["id"] for v in VOICE_CATALOG}
    if voice not in known:
        raise ValueError(f"未知发音人: {voice}，可用: {', '.join(sorted(known))}")
    _current_voice = voice
    logger.info("发音人已切换: %s", voice)
    return _current_voice


# ── TTS ───────────────────────────────────────────────────

def synthesize(text: str, voice: Optional[str] = None) -> bytes:
    """
    文本转语音，返回 MP3 字节。

    Args:
        text: 待合成文本（最长 500 字，超出截断）
        voice: 发音人 ID，默认使用当前发音人

    Returns:
        MP3 音频字节

    Raises:
        ValueError: 参数不合法
        VoiceNotImplementedError: 语音引擎尚未接入
    """
    if not text or not text.strip():
        raise ValueError("text 不能为空")

    text = text.strip()
    if len(text) > 500:
        logger.warning("TTS 文本超过 500 字，已截断")
        text = text[:500]

    return _synthesize_impl(text, voice or _current_voice)


def _synthesize_impl(text: str, voice: str) -> bytes:
    """
    TTS 实际实现入口。

    实现策略（可插拔）：
      1) 阿里云 NLS —— 配置了 ALIYUN_ACCESS_KEY_ID / SECRET 时优先
      2) edge-tts   —— 默认通道，无需密钥

    说明：ASR 与 TTS 相互独立。本函数实现后 TTS 可用，
    但 ASR（_transcribe_impl）仍保持「待实现」并返回 501，
    不影响 §3.3 中两者各自的语义。
    """
    # 1) 阿里云 NLS（若已配置）
    if _aliyun_configured():
        try:
            return _aliyun_tts(text, voice)
        except Exception as e:
            logger.warning("阿里云 TTS 失败，回退 edge-tts: %s", e)

    # 2) edge-tts（默认，无需密钥）
    return _edge_tts(text, voice)


def _aliyun_configured() -> bool:
    return bool(os.getenv("ALIYUN_ACCESS_KEY_ID") and os.getenv("ALIYUN_ACCESS_KEY_SECRET"))


def _aliyun_tts(text: str, voice: str) -> bytes:
    """阿里云 NLS TTS（惰性导入，需配置密钥）"""
    import requests  # type: ignore

    app_key = os.getenv("ALIYUN_NLS_APP_KEY", "")
    token = os.getenv("ALIYUN_NLS_TOKEN", "")
    if not app_key or not token:
        raise RuntimeError("缺少 ALIYUN_NLS_APP_KEY / ALIYUN_NLS_TOKEN")

    url = "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/tts"
    payload = {
        "appkey": app_key,
        "token": token,
        "text": text,
        "format": "mp3",
        "voice": voice if voice.startswith("long") else "longxiaochun_v2",
        "sample_rate": 16000,
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "")
    if "audio" not in content_type and "mpeg" not in content_type:
        raise RuntimeError(f"阿里云 TTS 返回非音频: {resp.text[:200]}")
    return resp.content


def _edge_tts(text: str, voice: str) -> bytes:
    """使用 edge-tts 合成（无需密钥）"""
    try:
        import edge_tts  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "TTS 依赖缺失：请安装 edge-tts（pip install edge-tts），"
            "或配置阿里云 NLS 密钥"
        ) from e

    # edge-tts 的发音人是 zh-CN-XXXNeural；若传入阿里云风格名称则用默认
    if not voice.startswith("zh-"):
        voice = DEFAULT_VOICE

    async def _run() -> bytes:
        communicate = edge_tts.Communicate(text, voice)
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                buf.write(chunk["data"])
        return buf.getvalue()

    try:
        audio = asyncio.run(_run())
    except RuntimeError:
        # 已在事件循环中（如被 FastAPI 调用），改用新线程
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            audio = pool.submit(lambda: asyncio.run(_run())).result()

    if not audio:
        raise RuntimeError("edge-tts 未返回音频数据")
    logger.info("TTS 合成完成: voice=%s, bytes=%d", voice, len(audio))
    return audio


# ── ASR ───────────────────────────────────────────────────

def transcribe(data: bytes, filename: str = "audio.wav") -> str:
    """
    语音识别，返回文本。

    Args:
        data: 音频字节
        filename: 原始文件名（用于推断格式）

    Returns:
        识别文本

    Raises:
        ValueError: 参数不合法
        VoiceNotImplementedError: 语音引擎尚未接入
    """
    if not data:
        raise ValueError("音频数据为空")

    return _transcribe_impl(data, filename)


def _transcribe_impl(data: bytes, filename: str) -> str:
    """
    ASR 实际实现入口 —— 待语音方案确定后在此接入。

    可参考的实现骨架：

        if VOICE_PROVIDER == "aliyun":
            return _aliyun_asr(data, filename)
        if VOICE_PROVIDER == "selfhosted":
            return _selfhosted_asr(data, filename)
        raise VoiceNotImplementedError("ASR")
    """
    raise VoiceNotImplementedError("ASR")
