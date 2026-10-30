# -*- coding: utf-8 -*-
"""纯逻辑：文本清洗与结构化切片。不依赖任何第三方库，方便单独测试。

设计取舍：
  通用 splitter 按固定字数切，会把「第 4.2 条」切成两半，模型拿到半句话就会答偏；
  安全规程本身是「章-节-条」的天然结构，按条款边界切，召回的就是完整语义单元。
  代价是块长度不均，靠 chunk_text 做二次切分兜底。
"""
import re

# 第X章 / 第X节 / 第X条
RE_CHAPTER = re.compile(r"^第([一二三四五六七八九十百零〇]+)章[\s　]*(.*)$")
RE_SECTION = re.compile(r"^第([一二三四五六七八九十百零〇]+)节[\s　]*(.*)$")
RE_CLAUSE = re.compile(r"^(第([一二三四五六七八九十百零〇]+)条)[\s　]*(.*)$")
# 数字编号：4.1 / 4.1.2
RE_NUMBERED = re.compile(r"^(\d+(?:\.\d+){1,3})[\s　]+(.+)$")
# 纯页码
RE_PAGE_NO = re.compile(r"^[-—\s]*\d+[-—\s]*$")


def clean_lines(pages: list[str], min_repeat_ratio: float = 0.5) -> str:
    """去掉跨页重复的页眉页脚和纯页码。

    阈值：文档至少 3 页时按比例；只有 2 页时放宽到 2 次，否则短文档去不掉页眉。
    """
    counter: dict[str, int] = {}
    for page in pages:
        for line in set(l.strip() for l in page.splitlines() if l.strip()):
            if len(line) <= 40:
                counter[line] = counter.get(line, 0) + 1

    if len(pages) < 2:
        threshold = 10 ** 9  # 单页文档不做去重，避免误删正文
    else:
        threshold = max(2, int(len(pages) * min_repeat_ratio))
    junk = {line for line, n in counter.items() if n >= threshold}

    out = []
    for page in pages:
        for line in page.splitlines():
            s = line.strip()
            if not s or s in junk or RE_PAGE_NO.fullmatch(s):
                continue
            out.append(s)
    return "\n".join(out)


def split_by_clause(text: str) -> list[tuple[str, str]]:
    """按「第X条」切分，块首注入「第X章 > 第X节」路径。

    返回 [(条款号, 块文本)]。条款号可能为空（退化为按段切分的情况）。
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    clauses: list[tuple[str, str]] = []
    chapter = section = ""
    buf: list[str] = []
    cur_no = ""

    def flush():
        nonlocal buf, cur_no
        body = "\n".join(buf).strip()
        if body:
            clauses.append((cur_no, body))
        buf, cur_no = [], ""

    for s in lines:
        if RE_CHAPTER.match(s):
            flush()
            chapter, section = s, ""
            continue
        if RE_SECTION.match(s):
            flush()
            section = s
            continue

        m = RE_CLAUSE.match(s)
        if m:
            flush()
            cur_no = m.group(1)
            path = f"【{chapter}{(' > ' + section) if section else ''}】" if chapter else ""
            buf = [x for x in (path, m.group(3)) if x]
            continue

        if not cur_no:
            m2 = RE_NUMBERED.match(s)
            if m2:
                flush()
                cur_no = m2.group(1)
                path = f"【{chapter}】" if chapter else ""
                buf = [x for x in (path, m2.group(2)) if x]
                continue

        if cur_no:
            buf.append(s)

    flush()

    if not clauses:  # 完全没有编号，退化为按自然段
        paras = [p.strip() for p in re.split(r"\n{2,}|\n", text) if p.strip()]
        clauses = [("", p) for p in paras]
    return clauses


def chunk_text(no: str, body: str, max_chars: int = 800) -> list[str]:
    """超过 max_chars 的条款按句号/分号二次切分，保留条款号，避免超出 embedding 上限。"""
    if len(body) <= max_chars:
        return [body]

    header = ""
    if body.startswith("【") and "】" in body:
        cut = body.find("】") + 1
        header, body = body[:cut], body[cut:]

    sentences = re.split(r"(?<=[。；;])", body)
    out, buf = [], ""
    for s in sentences:
        if len(buf) + len(s) > max_chars and buf:
            out.append(f"{header}{no}（续）{buf.strip()}")
            buf = s
        else:
            buf += s
    if buf.strip():
        out.append(f"{header}{no}（续）{buf.strip()}")
    return out
