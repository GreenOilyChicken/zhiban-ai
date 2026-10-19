#!/usr/bin/env python3
"""
Embedding 模型质量基准测试
==========================

目的：在客户环境部署前，量化「本地 bge-small-zh-v1.5」与「云端 bge-m3」
      在真实知识库语料上的检索质量差异，作为选型与验收依据。

用法：
    # 1) 用本地模型跑（需先 pip install sentence-transformers）
    python benchmark_embeddings.py --provider local

    # 2) 用云端 bge-m3 跑（需要可用的 OpenAI 兼容 /v1/embeddings）
    python benchmark_embeddings.py --provider cloud \
        --base-url http://127.0.0.1:3800/v1 --api-key <key>

    # 3) 两个都跑并输出对比
    python benchmark_embeddings.py --provider both --base-url ... --api-key ...

测试集构造：
    不手写问题，而是从三个 Chroma 集合中抽取真实 chunk，
    每个 chunk 生成一个「该 chunk 应当能召回自己」的查询：
    取 chunk 正文的前 N 个汉字作为 query，检查该 chunk 是否排在 Top-K。
    这避免了人工出题的主观性，直接反映真实文档上的检索行为。

指标：
    HitRate@K   —— query 的正确 chunk 出现在前 K 名的比例（主指标）
    MRR         —— Mean Reciprocal Rank，正确 chunk 排名倒数的平均值
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

COLLECTIONS = ["govpolicy", "elderly", "tourism"]
CHROMA_DIR = PROJECT_ROOT / "knowledge_base" / "chroma_db"
QUERY_CHARS = 24          # 每个 chunk 取前 24 个汉字作为查询
MAX_CHUNKS_PER_COLLECTION = 30
TOP_K = 5


# ── 测试集构造 ────────────────────────────────────────

def load_chunks() -> List[Tuple[str, str, str]]:
    """从 Chroma 抽取 (collection, source, document) 三元组"""
    chunks: List[Tuple[str, str, str]] = []
    for coll in COLLECTIONS:
        db = CHROMA_DIR / coll / "chroma.sqlite3"
        if not db.exists():
            print(f"[WARN] 缺少 {db}，跳过 {coll}")
            continue
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        con.text_factory = lambda b: b.decode("utf-8", errors="replace")
        # chroma 1.0: document 存在 embedding_metadata 的 'chroma:document' 键
        rows = con.execute(
            "SELECT em.string_value, em2.string_value "
            "FROM embedding_metadata em "
            "JOIN embedding_metadata em2 ON em.id = em2.id "
            "WHERE em.key = 'chroma:document' AND em2.key = 'source' "
            "LIMIT ?",
            (MAX_CHUNKS_PER_COLLECTION,),
        ).fetchall()
        con.close()
        for doc, src in rows:
            if doc and len(doc.strip()) > QUERY_CHARS:
                chunks.append((coll, src or "unknown", doc.strip()))
    return chunks


def build_queries(chunks: List[Tuple[str, str, str]]):
    """每个 chunk 取其正文前 QUERY_CHARS 字作为 query，答案是该 chunk 自身"""
    queries, answers = [], []
    for coll, src, doc in chunks:
        q = doc[:QUERY_CHARS]
        if not q:
            continue
        queries.append(q)
        answers.append(doc)
    return queries, answers


# ── Embedding 提供方 ─────────────────────────────────

def local_embed(texts: List[str], model_name: str) -> List[List[float]]:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name)
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [v.tolist() for v in vecs]


def cloud_embed(texts: List[str], base_url: str, api_key: str, model: str) -> List[List[float]]:
    import urllib.request
    req = urllib.request.Request(
        base_url.rstrip("/") + "/embeddings",
        data=json.dumps({"model": model, "input": texts}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    data = sorted(payload["data"], key=lambda d: d.get("index", 0))
    return [d["embedding"] for d in data]


# ── 检索与评分 ───────────────────────────────────────

def cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def evaluate(queries, answers, qvecs, dvecs) -> dict:
    """对每个 query，在所有候选文档中按余弦相似度排序，检查正确答案的名次"""
    hits_at_k = 0
    reciprocal_ranks = []
    for i, (q, qv) in enumerate(zip(queries, qvecs)):
        scores = [cosine(qv, dv) for dv in dvecs]
        order = sorted(range(len(scores)), key=lambda j: scores[j], reverse=True)
        rank = order.index(i) + 1 if i in order else len(order)
        if rank <= TOP_K:
            hits_at_k += 1
        reciprocal_ranks.append(1.0 / rank)
    n = len(queries)
    return {
        "queries": n,
        f"HitRate@{TOP_K}": round(hits_at_k / n, 4),
        "MRR": round(sum(reciprocal_ranks) / n, 4),
    }


# ── 主流程 ───────────────────────────────────────────

def run(label: str, embed_fn) -> dict:
    chunks = load_chunks()
    if not chunks:
        print("[ERROR] 未能从 Chroma 抽取任何 chunk，请先构建知识库")
        sys.exit(1)
    docs = [c[2] for c in chunks]
    queries, answers = build_queries(chunks)

    print(f"\n=== {label} ===")
    print(f"候选文档 {len(docs)} 篇，查询 {len(queries)} 条")

    t0 = time.time()
    dvecs = embed_fn(docs)
    t_doc = time.time() - t0

    t0 = time.time()
    qvecs = embed_fn(queries)
    t_q = time.time() - t0

    print(f"维度: {len(dvecs[0]) if dvecs else 'n/a'}")
    print(f"编码耗时: 文档 {t_doc:.1f}s / 查询 {t_q:.1f}s "
          f"({1000 * t_q / max(len(queries), 1):.0f} ms/条)")

    metrics = evaluate(queries, answers, qvecs, dvecs)
    print(f"HitRate@{TOP_K}: {metrics[f'HitRate@{TOP_K}']}   MRR: {metrics['MRR']}")
    return {"label": label, "dim": len(dvecs[0]) if dvecs else None,
            "metrics": metrics, "doc_encode_s": round(t_doc, 2),
            "query_ms_per_item": round(1000 * t_q / max(len(queries), 1), 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=["local", "cloud", "both"], default="both")
    ap.add_argument("--local-model", default=str(PROJECT_ROOT / "models" / "bge-small-zh-v1.5"))
    ap.add_argument("--base-url", default=os.getenv("CODEBUDDY_BASE_URL", "http://127.0.0.1:3800/v1"))
    ap.add_argument("--api-key", default=os.getenv("CODEBUDDY_API_KEY", ""))
    ap.add_argument("--cloud-model", default="bge-m3")
    ap.add_argument("--out", default=str(PROJECT_ROOT / "embedding_benchmark.json"))
    args = ap.parse_args()

    results = []
    if args.provider in ("local", "both"):
        results.append(run("local bge-small-zh-v1.5", lambda t: local_embed(t, args.local_model)))
    if args.provider in ("cloud", "both"):
        if not args.api_key:
            print("[ERROR] cloud provider 需要 --api-key 或 CODEBUDDY_API_KEY")
            sys.exit(1)
        results.append(run(f"cloud {args.cloud_model}",
                           lambda t: cloud_embed(t, args.base_url, args.api_key, args.cloud_model)))

    if args.out and args.out != "-":
        try:
            Path(args.out).write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"\n结果已写入 {args.out}")
        except OSError as exc:
            print(f"\n[WARN] 无法写入 {args.out}（{exc}），以下为 JSON 结果：")
            print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    if len(results) == 2:
        a, b = results
        print("\n=== 对比 ===")
        print(f"{a['label']}: HitRate@{TOP_K}={a['metrics'][f'HitRate@{TOP_K}']} MRR={a['metrics']['MRR']}")
        print(f"{b['label']}: HitRate@{TOP_K}={b['metrics'][f'HitRate@{TOP_K}']} MRR={b['metrics']['MRR']}")
        gap = b["metrics"]["MRR"] - a["metrics"]["MRR"]
        print(f"MRR 差值（cloud - local）: {gap:+.4f}")


if __name__ == "__main__":
    main()
