"""
voice_service — 语音合成（TTS）与语音识别（ASR）

设计目标（附件一 §3.3 / §10.1）：
  - TTS：文本转语音，返回 MP3 音频，支持多种发音人
  - ASR：语音转文字，支持多种音频格式
  - 发音人可切换

实现策略（可插拔）：
  1. 首选云端（阿里云 NLS）—— 需配置 ALIYUN_ACCESS_KEY_ID 等
  2. 回退本地/免费通道：
     - TTS: edge-tts（微软在线语音，无需密钥）
     - ASR: faster-whisper / openai-whisper 本地模型；不可用时返回明确错误

所有外部依赖均为惰性导入，缺失时给出可操作的错误信息，不影响 RAG 主流程。
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── 发音人配置 ────────────────────────────────────────────

# 默认发音人：龙小淳风格（甜美年轻女声，贴近"小芯"童声人设）
DEFAULT_VOICE = os.getenv("TTS_VOICE", "zh-CN-XiaoxiaoNeural")

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
    """
    if not text or not text.strip():
        raise ValueError("text 不能为空")

    text = text.strip()
    if len(text) > 500:
        logger.warning("TTS 文本超过 500 字，已截断")
        text = text[:500]

    voice = voice or _current_voice

    # 1) 阿里云 NLS（若已配置）
    if _aliyun_configured():
        try:
            return _aliyun_tts(text, voice)
        except Exception as e:
            logger.warning("阿里云 TTS 失败，回退 edge-tts: %s", e)

    # 2) edge-tts（默认）
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
    """
    if not data:
        raise ValueError("音频数据为空")

    # 1) 阿里云 NLS（若配置了 token）
    if os.getenv("ALIYUN_NLS_TOKEN") and os.getenv("ALIYUN_NLS_APP_KEY"):
        try:
            return _aliyun_asr(data, filename)
        except Exception as e:
            logger.warning("阿里云 ASR 失败，回退本地模型: %s", e)

    # 2) 本地 whisper
    return _local_asr(data, filename)


def _aliyun_asr(data: bytes, filename: str) -> str:
    """阿里云一句话识别（惰性导入）"""
    import requests  # type: ignore

    app_key = os.getenv("ALIYUN_NLS_APP_KEY", "")
    token = os.getenv("ALIYUN_NLS_TOKEN", "")
    url = (
        "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/asr"
        f"?appkey={app_key}&format=pcm&sample_rate=16000&enable_punctuation_prediction=true"
    )
    headers = {
        "X-NLS-Token": token,
        "Content-Type": "application/octet-stream",
    }
    resp = requests.post(url, headers=headers, data=data, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    if result.get("status") != 20000000:
        raise RuntimeError(f"阿里云 ASR 失败: {result.get('message')}")
    return result.get("result", "")


def _local_asr(data: bytes, filename: str) -> str:
    """本地 whisper 识别（faster-whisper 优先，回退 openai-whisper）"""
    suffix = Path(filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        # faster-whisper
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError:
            WhisperModel = None  # type: ignore

        if WhisperModel is not None:
            model_size = os.getenv("ASR_MODEL", "small")
            device = os.getenv("ASR_DEVICE", "cpu")
            compute = os.getenv("ASR_COMPUTE_TYPE", "int8")
            model = _get_whisper_model(model_size, device, compute)
            segments, _info = model.transcribe(tmp_path, language="zh", beam_size=5)
            text = "".join(seg.text for seg in segments).strip()
            logger.info("ASR(faster-whisper) 识别完成: %d 字", len(text))
            return text

        # openai-whisper
        try:
            import whisper  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "ASR 依赖缺失：请安装 faster-whisper（pip install faster-whisper），"
                "或配置阿里云 NLS 的 ALIYUN_NLS_TOKEN"
            ) from e

        model = whisper.load_model(os.getenv("ASR_MODEL", "small"))
        result = model.transcribe(tmp_path, language="zh")
        text = (result.get("text") or "").strip()
        logger.info("ASR(whisper) 识别完成: %d 字", len(text))
        return text
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


_whisper_models: dict = {}


def _get_whisper_model(model_size: str, device: str, compute_type: str):
    """缓存 whisper 模型实例，避免重复加载"""
    key = (model_size, device, compute_type)
    if key not in _whisper_models:
        from faster_whisper import WhisperModel  # type: ignore
        logger.info("加载 ASR 模型: %s (%s/%s)", model_size, device, compute_type)
        _whisper_models[key] = WhisperModel(model_size, device=device, compute_type=compute_type)
    return _whisper_models[key]
