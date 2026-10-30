# -*- coding: utf-8 -*-
"""混合检索：向量召回 + BM25 召回 -> RRF 融合。

为什么要混合：
  向量检索擅长“语义相近”，但对「动火作业」「盲板抽堵」这类专有名词、
  以及对「第 4.2 条」这类编号不敏感；
  BM25 恰好擅长精确词命中。两者互补，用 RRF 融合不需要调权重。
"""
import pickle
from pathlib import Path

import jieba
from openai import OpenAI
from rank_bm25 import BM25Okapi

import config as C

jieba.setLogLevel(20)

_cache: dict = {}


def _load():
    if _cache:
        return _cache
    pkl = C.INDEX_DIR / "chunks.pkl"
    if not pkl.exists():
        raise SystemExit("索引不存在，先运行：python ingest.py")

    import chromadb

    with open(pkl, "rb") as f:
        data = pickle.load(f)
    client = chromadb.PersistentClient(path=str(C.INDEX_DIR))
    col = client.get_collection(C.COLLECTION)

    _cache.update(
        chunks=data["chunks"],
        metas=data["metas"],
        col=col,
        bm25=BM25Okapi(data["tokens"]),
    )
    return _cache


def embed_query(text: str) -> list[float]:
    client = OpenAI(api_key=C.EMBED_API_KEY, base_url=C.EMBED_BASE_URL)
    resp = client.embeddings.create(model=C.EMBED_MODEL, input=[text])
    return resp.data[0].embedding


def rrf(vec_ids: list[str], bm25_ids: list[str], k: int = 60) -> dict[str, float]:
    """倒数排名融合。只看名次不看分数，避免两路分数量纲不一致。"""
    score: dict[str, float] = {}
    for rank, _id in enumerate(vec_ids):
        score[_id] = score.get(_id, 0.0) + 1.0 / (k + rank + 1)
    for rank, _id in enumerate(bm25_ids):
        score[_id] = score.get(_id, 0.0) + 1.0 / (k + rank + 1)
    return score


def search(query: str, top_k: int = C.TOP_K) -> dict:
    """返回 {hits: [...], max_sim: float}

    每个 hit: {id, text, clause, source, sim, rrf}
    max_sim 用最高向量相似度，作为“该不该拒答”的置信信号。
    """
    d = _load()
    qv = embed_query(query)

    # 1) 向量召回
    n = max(1, min(C.RECALL_N, d["col"].count()))
    res = d["col"].query(
        query_embeddings=[qv],
        n_results=n,
        include=["documents", "metadatas", "distances"],
    )
    vec_ids = res["ids"][0]
    sims = {i: 1.0 - dist for i, dist in zip(vec_ids, res["distances"][0])}

    # 2) BM25 召回
    scores = d["bm25"].get_scores(jieba.lcut(query))
    order = scores.argsort()[::-1][: C.RECALL_N]
    bm25_ids = [str(i) for i in order if scores[i] > 0]

    # 3) RRF 融合
    fused = rrf(vec_ids, bm25_ids)
    ranked = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:top_k]

    hits = []
    for _id, rrf_score in ranked:
        i = int(_id)
        hits.append({
            "id": _id,
            "text": d["chunks"][i],
            "clause": d["metas"][i].get("clause", ""),
            "source": d["metas"][i].get("source", ""),
            "sim": sims.get(_id, 0.0),
            "rrf": rrf_score,
        })
    # 置信度取「向量候选里的最高相似度」，而不是只看最终 5 条：
    # 融合后可能有纯 BM25 命中（没有向量分），只看最终结果会低估置信度
    max_sim = max(sims.values(), default=0.0)
    return {"hits": hits, "max_sim": max_sim}


if __name__ == "__main__":
    import sys

    q = sys.argv[1] if len(sys.argv) > 1 else "动火作业分几级"
    out = search(q)
    print(f"问题：{q}   最高相似度：{out['max_sim']:.3f}\n")
    for n, h in enumerate(out["hits"], 1):
        print(f"[{n}] {h['clause']}  sim={h['sim']:.3f}")
        print(h["text"][:160].replace("\n", " "))
        print()
