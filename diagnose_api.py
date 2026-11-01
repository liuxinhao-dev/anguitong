# -*- coding: utf-8 -*-
r"""分别测试 DeepSeek 和智谱的连通性，精确定位 401 来自哪一边。

用法（放在项目根目录，和 config.py 同级）：
    .\.venv\Scripts\python.exe diagnose_api.py
"""
import sys

import config as C

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from openai import OpenAI


def mask(key: str) -> str:
    if not key:
        return "(空)"
    if len(key) <= 12:
        return key[:2] + "…"
    return f"{key[:8]}…{key[-4:]}（{len(key)} 位）"


def test_embed() -> bool:
    print("\n" + "=" * 56)
    print("智谱 Embedding")
    print("=" * 56)
    print(f"  BASE_URL : {C.EMBED_BASE_URL}")
    print(f"  MODEL    : {C.EMBED_MODEL}")
    print(f"  API_KEY  : {mask(C.EMBED_API_KEY)}")

    if not C.EMBED_API_KEY:
        print("  ✗ key 是空的，检查 .env")
        return False

    if "." not in C.EMBED_API_KEY:
        print("  ⚠ 智谱的 key 形如 xxxxxxxx.yyyyyyyy，你这串里没有「.」")
        print("    很可能只复制了前半段")
        return False

    try:
        client = OpenAI(api_key=C.EMBED_API_KEY, base_url=C.EMBED_BASE_URL)
        r = client.embeddings.create(model=C.EMBED_MODEL, input=["安全帽"])
        print(f"  ✓ 调用成功，向量维度 = {len(r.data[0].embedding)}")
        return True
    except Exception as e:
        print(f"  ✗ {type(e).__name__}")
        msg = str(e)
        print(f"    {msg[:300]}")

        low = msg.lower()
        if "401" in msg or "身份验证" in msg or "unauthorized" in low:
            print("\n  → 这是「key 本身不被认可」。最常见三个原因：")
            print("    1. 智谱账号还没做实名认证（国内平台硬门槛，没认证 key 一律 401）")
            print("    2. key 已经被删掉/重新生成过，.env 里还是旧的")
            print("    3. key 复制不全（前后有空格，或漏了 . 后面那段）")
        elif "403" in msg:
            print("\n  → 权限问题：key 有效，但没有 embedding-3 的调用权限")
        elif "1113" in msg or "余额" in msg or "资源包" in msg:
            print("\n  → 余额/资源包问题，去「财务」页看看要不要领免费额度")
        elif "model" in low:
            print("\n  → 模型名不对，去文档确认当前的 embedding 模型名")
        return False


def test_chat() -> bool:
    print("\n" + "=" * 56)
    print("DeepSeek Chat")
    print("=" * 56)
    print(f"  BASE_URL : {C.CHAT_BASE_URL}")
    print(f"  MODEL    : {C.CHAT_MODEL}")
    print(f"  API_KEY  : {mask(C.DEEPSEEK_API_KEY)}")

    if not C.DEEPSEEK_API_KEY:
        print("  ✗ key 是空的")
        return False

    try:
        client = OpenAI(api_key=C.DEEPSEEK_API_KEY, base_url=C.CHAT_BASE_URL)
        r = client.chat.completions.create(
            model=C.CHAT_MODEL,
            messages=[{"role": "user", "content": "只回两个字：收到"}],
            extra_body={"thinking": {"type": "disabled"}},
        )
        print(f"  ✓ 调用成功，返回：{r.choices[0].message.content!r}")
        return True
    except Exception as e:
        print(f"  ✗ {type(e).__name__}")
        msg = str(e)
        print(f"    {msg[:300]}")
        if "model" in msg.lower():
            print("\n  → 模型名不对。当前官方名是 deepseek-flash，改 config.py 第 18 行")
        elif "402" in msg or "insufficient" in msg.lower():
            print("\n  → 余额不足，去 platform.deepseek.com 充值")
        elif "401" in msg:
            print("\n  → DeepSeek 的 key 无效，重新生成一个")
        return False


if __name__ == "__main__":
    print("正在分别测试两个 API…")
    ok_embed = test_embed()
    ok_chat = test_chat()

    print("\n" + "=" * 56)
    print("结论")
    print("=" * 56)
    print(f"  智谱 embedding : {'✓ 通' if ok_embed else '✗ 不通'}")
    print(f"  DeepSeek chat  : {'✓ 通' if ok_chat else '✗ 不通'}")
    print()
    if not ok_embed and ok_chat:
        print("  只有智谱有问题。先查实名认证，再确认 key 是最新的那个。")
    elif ok_embed and not ok_chat:
        print("  只有 DeepSeek 有问题。")
    elif not ok_embed and not ok_chat:
        print("  两边都不通，先检查网络（能不能打开 open.bigmodel.cn）。")

    sys.exit(0 if (ok_embed and ok_chat) else 1)
