# -*- coding: utf-8 -*-
"""把 PDF 变成可检索的条款块。

流程：PDF 解析 -> 去页眉页脚 -> 按「章/节/条」结构化切片 -> 向量化入库 + BM25 索引

这是整个项目最脏、也最能讲的一段：清洗和切片决定了后面所有效果的上限。
切片逻辑在 splitter.py（纯标准库、可单测），这里只负责 IO 和建库。
"""
import pickle
import sys
from pathlib import Path

import fitz  # PyMuPDF
import jieba
from openai import OpenAI
from rank_bm25 import BM25Okapi

import config as C
from splitter import chunk_text, clean_lines, split_by_clause

jieba.setLogLevel(20)


def pdf_to_text(pdf_path: Path) -> str:
    doc = fitz.open(pdf_path)
    pages = [p.get_text("text") for p in doc]
    doc.close()
    if not pages or sum(len(p.strip()) for p in pages) < 200:
        raise ValueError(f"读不到足够文本，可能是扫描件，需要先 OCR：{pdf_path}")
    return clean_lines(pages)


def embed_texts(texts: list[str], batch: int = 16) -> list[list[float]]:
    client = OpenAI(api_key=C.EMBED_API_KEY, base_url=C.EMBED_BASE_URL)
    vectors: list[list[float]] = []
    for i in range(0, len(texts), batch):
        resp = client.embeddings.create(model=C.EMBED_MODEL, input=texts[i: i + batch])
        vectors.extend([d.embedding for d in resp.data])
        print(f"  向量化 {min(i + batch, len(texts))}/{len(texts)}", end="\r")
    print()
    return vectors


def build(pdf_path: Path) -> None:
    C.check_keys()
    import chromadb

    print(f"[1/4] 解析 {pdf_path.name}")
    text = pdf_to_text(pdf_path)
    print(f"      {len(text)} 字符")

    print("[2/4] 结构化切片")
    clauses = split_by_clause(text)
    chunks, metas, ids = [], [], []
    for no, body in clauses:
        for piece in chunk_text(no, body, C.CHUNK_MAX_CHARS):
            chunks.append(piece)
            metas.append({"clause": no, "source": pdf_path.name})
            ids.append(str(len(chunks) - 1))
    print(f"      {len(clauses)} 条 -> {len(chunks)} 个块")

    print("[3/4] 向量化并写入 Chroma")
    vectors = embed_texts(chunks)
    C.INDEX_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(C.INDEX_DIR))
    try:
        client.delete_collection(C.COLLECTION)
    except Exception:
        pass
    col = client.get_or_create_collection(
        C.COLLECTION, metadata={"hnsw:space": "cosine"}
    )
    for i in range(0, len(chunks), 256):
        col.add(
            ids=ids[i: i + 256],
            documents=chunks[i: i + 256],
            metadatas=metas[i: i + 256],
            embeddings=vectors[i: i + 256],
        )

    print("[4/4] 建 BM25 索引")
    tokens = [jieba.lcut(c) for c in chunks]
    with open(C.INDEX_DIR / "chunks.pkl", "wb") as f:
        pickle.dump({"chunks": chunks, "metas": metas, "tokens": tokens}, f)

    avg = sum(len(c) for c in chunks) / max(len(chunks), 1)
    print(f"完成：{len(chunks)} 块，平均 {avg:.0f} 字，索引在 {C.INDEX_DIR}")


if __name__ == "__main__":
    C.check_keys()
    pdfs = [Path(sys.argv[1])] if len(sys.argv) > 1 else sorted(C.DATA_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"没找到 PDF，请把文件放到 {C.DATA_DIR}")
    for p in pdfs:
        build(p)
