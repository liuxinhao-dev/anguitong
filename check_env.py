# -*- coding: utf-8 -*-
"""环境自检：一条命令告诉你缺什么、下一步做什么。

用法（在 anguitong 目录下）：
    py -3.12 check_env.py

只用标准库，没装依赖也能跑。
"""
import importlib.metadata as md
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

PACKAGES = [
    ("openai", "openai", "调用 DeepSeek / 智谱接口"),
    ("pymupdf", "fitz", "解析 PDF"),
    ("chromadb", "chromadb", "向量库"),
    ("rank-bm25", "rank_bm25", "关键词检索"),
    ("jieba", "jieba", "中文分词"),
    ("streamlit", "streamlit", "网页界面"),
    ("python-dotenv", "dotenv", "读取 .env"),
]


def head(title):
    print(f"\n{'=' * 52}\n{title}\n{'=' * 52}")


def main():
    problems, hints = [], []

    # ---------- Python ----------
    head("1. Python 版本")
    v = sys.version_info
    print(f"   解释器：{sys.executable}")
    print(f"   版本：  {v.major}.{v.minor}.{v.micro}")
    if v < (3, 10):
        problems.append("Python 版本过低")
        hints.append("换 3.12：用 `py -3.12` 代替 `python` 执行所有命令")
        print("   ✗ 需要 3.10 以上。你现在的 `python` 可能指向了旧版本。")
    else:
        print("   ✓ 版本满足要求")

    # ---------- 依赖 ----------
    head("2. 依赖包")
    missing = []
    for pip_name, module, purpose in PACKAGES:
        try:
            __import__(module)
            try:
                ver = md.version(pip_name)
            except Exception:
                ver = "?"
            print(f"   ✓ {pip_name:<16} {ver:<10} {purpose}")
        except Exception:
            print(f"   ✗ {pip_name:<16} {'未安装':<10} {purpose}")
            missing.append(pip_name)
    if missing:
        problems.append(f"缺 {len(missing)} 个依赖")
        hints.append("装依赖：.venv\\Scripts\\python.exe -m pip install -r requirements.txt")

    # ---------- 密钥 ----------
    head("3. API 密钥（.env）")
    env = HERE / ".env"
    if not env.exists():
        problems.append("没有 .env")
        hints.append("复制 .env.example 为 .env，填入两个 key")
        print("   ✗ 没有 .env 文件")
    else:
        pairs = {}
        for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, val = line.partition("=")
                pairs[k.strip()] = val.strip()
        for key in ("DEEPSEEK_API_KEY", "EMBED_API_KEY"):
            val = pairs.get(key, "")
            if not val or "填" in val or "xxx" in val.lower():
                problems.append(f"{key} 未填")
                print(f"   ✗ {key} 没填或还是占位符")
            else:
                print(f"   ✓ {key} = {val[:6]}…{val[-4:]}（{len(val)} 位）")
        hints.append("key 去 platform.deepseek.com 和 open.bigmodel.cn 申请")

    # ---------- 数据 ----------
    head("4. 数据与索引")
    pdfs = sorted((HERE / "data").glob("*.pdf"))
    if pdfs:
        for p in pdfs:
            print(f"   ✓ {p.name}  ({p.stat().st_size / 1024:.0f} KB)")
    else:
        problems.append("data/ 里没有 PDF")
        hints.append("把规程 PDF 放进 data/ 目录")
        print("   ✗ data/ 里没有 PDF")

    idx = HERE / "index" / "chunks.pkl"
    if idx.exists():
        print(f"   ✓ 索引已建：{idx.stat().st_size / 1024:.0f} KB")
    else:
        print("   - 索引还没建（首次运行 python ingest.py 会生成）")

    # ---------- 结论 ----------
    head("结论")
    if not problems:
        print("   ✓ 环境齐了，可以开始：")
        print("       python ingest.py")
        print("       python answer.py \"动火作业分几级\"")
        print("       streamlit run app.py")
    else:
        print(f"   还有 {len(problems)} 项没就绪：")
        for p in problems:
            print(f"     · {p}")
        print("\n   下一步：")
        for h in dict.fromkeys(hints):
            print(f"     → {h}")
    print()
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
