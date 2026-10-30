# -*- coding: utf-8 -*-
"""全局配置。所有密钥走环境变量，不要写进代码、不要提交到 GitHub。"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"          # 放你的 PDF
INDEX_DIR = BASE_DIR / "index"        # 生成的索引
EVAL_DIR = BASE_DIR / "eval"

# ---------- 生成模型：DeepSeek ----------
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
CHAT_BASE_URL = "https://api.deepseek.com"
CHAT_MODEL = "deepseek-chat"

# ---------- 向量模型：智谱 embedding-3 ----------
# 也可换通义 text-embedding-v3（base_url 改成 dashscope 兼容地址、model 改名即可）
EMBED_API_KEY = os.getenv("EMBED_API_KEY", "")
EMBED_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
EMBED_MODEL = "embedding-3"

# ---------- 检索参数 ----------
TOP_K = 5            # 最终给模型的条数
RECALL_N = 20        # 每路检索先取多少条，再融合
CHUNK_MAX_CHARS = 800

# 拒答阈值：最高向量相似度低于它，直接说“查不到”，不调用大模型
# 这个值要用你的评测集扫一遍再定，0.35 只是起点
REFUSE_SIM = 0.35

COLLECTION = "anguitong"


def check_keys() -> None:
    missing = [n for n, v in
               (("DEEPSEEK_API_KEY", DEEPSEEK_API_KEY), ("EMBED_API_KEY", EMBED_API_KEY))
               if not v]
    if missing:
        raise SystemExit(
            f"缺少环境变量：{', '.join(missing)}\n"
            "在项目根目录建一个 .env 文件，写入：\n"
            "  DEEPSEEK_API_KEY=sk-xxx\n"
            "  EMBED_API_KEY=xxx\n"
            "（.env 必须写进 .gitignore）"
        )
