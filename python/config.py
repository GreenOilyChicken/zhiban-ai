"""
知伴AI — 全局配置模块
支持多 Provider（DeepSeek / OpenAI / Qwen / CodeBuddy 代理）切换
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _env_int(key: str, default: int) -> int:
    raw = _env(key, str(default))
    try:
        return int(raw)
    except ValueError:
        print(f"[WARN] 环境变量 {key} 值 '{raw}' 不是合法整数，回退默认值 {default}")
        return default


def _env_float(key: str, default: float) -> float:
    raw = _env(key, str(default))
    try:
        return float(raw)
    except ValueError:
        print(f"[WARN] 环境变量 {key} 值 '{raw}' 不是合法浮点数，回退默认值 {default}")
        return default


def _env_path(key: str, default: Path) -> Path:
    raw = _env(key, "")
    if not raw:
        return default
    p = Path(raw)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p


# ── LLM 配置 ──────────────────────────────────────────
LLM_PROVIDER = _env("LLM_PROVIDER", "deepseek")
DEEPSEEK_API_KEY = _env("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = _env("DEEPSEEK_MODEL", "deepseek-chat")

OPENAI_API_KEY = _env("OPENAI_API_KEY", "")
OPENAI_BASE_URL = _env("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = _env("OPENAI_MODEL", "gpt-4o-mini")

QWEN_API_KEY = _env("QWEN_API_KEY", "")
QWEN_BASE_URL = _env("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL = _env("QWEN_MODEL", "qwen-plus")

# ── CodeBuddy 代理（本地测试用，OpenAI 兼容接口）──────
# 把 LLM_PROVIDER 设为 codebuddy 即可走本地代理，无需真实厂商 Key。
CODEBUDDY_API_KEY = _env("CODEBUDDY_API_KEY", "")
CODEBUDDY_BASE_URL = _env("CODEBUDDY_BASE_URL", "http://127.0.0.1:3800/v1")
CODEBUDDY_MODEL = _env("CODEBUDDY_MODEL", "deepseek-v4-flash")

LLM_TEMPERATURE = _env_float("LLM_TEMPERATURE", 0.3)
LLM_MAX_TOKENS = _env_int("LLM_MAX_TOKENS", 2048)

# ── Embedding 配置 ────────────────────────────────────
# EMBEDDING_PROVIDER:
#   bge    —— 生产默认，BGE 中文语义向量（需 sentence-transformers + 本地模型）
#   hash   —— 离线兜底，确定性哈希向量，仅用于无网络/无模型环境的链路验证
EMBEDDING_PROVIDER = _env("EMBEDDING_PROVIDER", "bge").lower()
# 默认指向随项目分发的本地模型目录（客户环境无外网，不能依赖 HuggingFace 下载）。
# 容器内路径为 /app/models/bge-small-zh-v1.5，本地开发为 <repo>/python/models/...
# 如需改用其他模型（如 bge-m3），设置环境变量 BGE_MODEL_NAME 即可，
# 可传本地目录路径，也可传 HuggingFace repo id（需可联网下载）。
BGE_MODEL_DIR = _env_path("BGE_MODEL_DIR", PROJECT_ROOT / "models" / "bge-small-zh-v1.5")
BGE_MODEL_NAME = _env("BGE_MODEL_NAME", str(BGE_MODEL_DIR))
EMBEDDING_DEVICE = _env("EMBEDDING_DEVICE", "cpu")
# 离线兜底向量的维度（仅 hash provider 使用）
HASH_EMBEDDING_DIM = _env_int("HASH_EMBEDDING_DIM", 512)

# ── 知识库路径 ────────────────────────────────────────
KB_POLICY_DIR = _env_path("KB_POLICY_DIR", PROJECT_ROOT / "knowledge_base" / "policies")
KB_ELDERLY_DIR = _env_path("KB_ELDERLY_DIR", PROJECT_ROOT / "knowledge_base" / "elderly")
KB_TOURISM_DIR = _env_path("KB_TOURISM_DIR", PROJECT_ROOT / "knowledge_base" / "tourism")
KB_CHROMA_DIR = _env_path("KB_CHROMA_DIR", PROJECT_ROOT / "knowledge_base" / "chroma_db")

# ── 知识库 Collection 命名（三库统一，供 Java/Python 双方对齐）──
COLLECTION_GOVPOLICY = _env("COLLECTION_GOVPOLICY", "govpolicy")
COLLECTION_ELDERLY = _env("COLLECTION_ELDERLY", "elderly")
COLLECTION_TOURISM = _env("COLLECTION_TOURISM", "tourism")

# collection -> 源文档目录
KB_COLLECTIONS = {
    COLLECTION_GOVPOLICY: KB_POLICY_DIR,
    COLLECTION_ELDERLY: KB_ELDERLY_DIR,
    COLLECTION_TOURISM: KB_TOURISM_DIR,
}

# ── 台账输出 ──────────────────────────────────────────
LEDGER_OUTPUT_DIR = _env_path("LEDGER_OUTPUT_DIR", PROJECT_ROOT / "output" / "ledgers")

# ── 日志脱敏 ──────────────────────────────────────────
LTC_LOG_MASK = _env("LTC_LOG_MASK", "true").lower() == "true"


def dump(key_name: str, value: str) -> str:
    """对 API Key 做掩码输出，用于日志"""
    if not value:
        return f"{key_name}=(empty)"
    if len(value) <= 12:
        return f"{key_name}=***"
    return f"{key_name}={value[:4]}***{value[-4:]}"


def print_config_summary():
    """打印配置摘要（脱敏）"""
    print("=" * 60)
    print("知伴AI 配置摘要")
    print("=" * 60)
    print(f"  LLM Provider  : {LLM_PROVIDER}")
    if LLM_PROVIDER == "deepseek":
        print(f"  {dump('API Key', DEEPSEEK_API_KEY)}")
        print(f"  Model        : {DEEPSEEK_MODEL}")
        print(f"  Base URL     : {DEEPSEEK_BASE_URL}")
    elif LLM_PROVIDER == "openai":
        print(f"  {dump('API Key', OPENAI_API_KEY)}")
        print(f"  Model        : {OPENAI_MODEL}")
    elif LLM_PROVIDER == "qwen":
        print(f"  {dump('API Key', QWEN_API_KEY)}")
        print(f"  Model        : {QWEN_MODEL}")
    elif LLM_PROVIDER == "codebuddy":
        print(f"  {dump('API Key', CODEBUDDY_API_KEY)}")
        print(f"  Model        : {CODEBUDDY_MODEL}")
        print(f"  Base URL     : {CODEBUDDY_BASE_URL}")
    print(f"  Temperature  : {LLM_TEMPERATURE}")
    print(f"  Max Tokens   : {LLM_MAX_TOKENS}")
    print(f"  BGE Model    : {BGE_MODEL_NAME}")
    print(f"  Embed Device : {EMBEDDING_DEVICE}")
    print(f"  KB Dir       : {KB_CHROMA_DIR}")
    print("=" * 60)
