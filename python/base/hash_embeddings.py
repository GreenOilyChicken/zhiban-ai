"""
hash_embeddings — 离线兜底 Embedding 实现

用途
----
当运行环境无法下载 BGE 模型（无外网 / 无 sentence-transformers）时，
提供确定性向量以保证「文档写入 -> 向量存储 -> 检索」整条链路可验证。

特点
----
- 纯 Python，无第三方依赖
- 确定性：同一文本永远得到同一向量
- 字符 n-gram + 词频归一化，对中文短文本有一定区分度

⚠️ 这不是语义模型，检索质量远低于 BGE。
   生产环境必须使用 EMBEDDING_PROVIDER=bge。
"""
from __future__ import annotations

import hashlib
import logging
import math
import re
from typing import List

logger = logging.getLogger(__name__)


class HashEmbeddings:
    """确定性哈希 Embedding（兼容 LangChain Embeddings 接口）"""

    def __init__(self, dim: int = 512):
        self.dim = dim

    # ── 向量计算 ────────────────────────────────────────

    def _tokens(self, text: str) -> List[str]:
        """切分为中文字 + 二元组 + 英文单词"""
        text = (text or "").strip()
        if not text:
            return []

        tokens: List[str] = []

        # 英文/数字词
        tokens.extend(w.lower() for w in re.findall(r"[A-Za-z0-9]+", text))

        # 中文字符及相邻二元组（提升区分度）
        han = re.findall(r"[\u4e00-\u9fff]", text)
        tokens.extend(han)
        tokens.extend(han[i] + han[i + 1] for i in range(len(han) - 1))

        return tokens

    def _vec(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        tokens = self._tokens(text)
        if not tokens:
            return vec

        for tok in tokens:
            h = hashlib.md5(tok.encode("utf-8")).digest()
            # 用两个独立位置做散列，降低冲突影响
            idx1 = int.from_bytes(h[:4], "big") % self.dim
            idx2 = int.from_bytes(h[4:8], "big") % self.dim
            sign = 1.0 if h[8] % 2 == 0 else -1.0
            vec[idx1] += 1.0
            vec[idx2] += 0.5 * sign

        # L2 归一化，保证与 BGE（normalize_embeddings=True）行为一致
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    # ── LangChain 接口 ──────────────────────────────────

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._vec(text)

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.embed_documents(texts)

    async def aembed_query(self, text: str) -> List[float]:
        return self.embed_query(text)
