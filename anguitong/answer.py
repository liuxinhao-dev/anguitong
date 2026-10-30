# -*- coding: utf-8 -*-
"""带引用与拒答的回答生成。

两道防线：
  1) 检索置信度不够 -> 不调模型，直接拒答（省钱且安全）
  2) 模型给出的引用条款号不在召回结果里 -> 判定为幻觉，拒答
"""
import json
import re

from openai import OpenAI

import config as C
from retrieve import search

SYSTEM = """你是化工安全规程问答助手，服务对象是一线作业人员。

硬性规则：
1. 只能依据【给定条款】回答，不得使用条款之外的知识；
2. 回答必须具体、可执行，直接说怎么做、分几级、谁来批；
3. 必须注明依据的条款号；
4. 若给定条款不足以回答，can_answer 必须为 false，不要猜。

只输出 JSON，不要输出其他内容：
{"can_answer": true/false, "answer": "回答正文", "cited_clause": "第X条"}
"""

REFUSAL = "规程中未找到相关条款，建议咨询安全管理员确认后再作业。"


def _build_context(hits):
    blocks, valid = [], set()
    for n, h in enumerate(hits, 1):
        clause = h["clause"] or "（无编号）"
        valid.add(clause)
        blocks.append(f"[{n}] 条款：{clause}\n{h['text']}")
    return "\n\n".join(blocks), valid


def _parse(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"can_answer": False, "answer": "", "cited_clause": ""}


def ask(question: str) -> dict:
    """返回 {answer, cited_clause, refused, reason, hits}"""
    r = search(question)
    hits, max_sim = r["hits"], r["max_sim"]

    if not hits or max_sim < C.REFUSE_SIM:
        return {
            "answer": REFUSAL,
            "cited_clause": "",
            "refused": True,
            "reason": f"检索置信度不足（{max_sim:.3f} < {C.REFUSE_SIM}）",
            "hits": hits,
        }

    ctx, valid = _build_context(hits)
    client = OpenAI(api_key=C.DEEPSEEK_API_KEY, base_url=C.CHAT_BASE_URL)
    resp = client.chat.completions.create(
        model=C.CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"【给定条款】\n{ctx}\n\n【问题】{question}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    data = _parse(resp.choices[0].message.content or "")

    cited = (data.get("cited_clause") or "").strip()
    if not data.get("can_answer") or not data.get("answer"):
        return {"answer": REFUSAL, "cited_clause": "", "refused": True,
                "reason": "模型判定条款不足", "hits": hits}

    # 引用校验：引用的条款必须是这次真正召回到的
    if cited and not any(cited in v or v in cited for v in valid):
        return {"answer": REFUSAL, "cited_clause": "", "refused": True,
                "reason": f"引用校验失败：{cited} 不在召回结果中", "hits": hits}

    return {"answer": data["answer"], "cited_clause": cited,
            "refused": False, "reason": "", "hits": hits}


if __name__ == "__main__":
    import sys

    q = sys.argv[1] if len(sys.argv) > 1 else "动火作业分几级，谁来审批"
    res = ask(q)
    print("问题：", q)
    print("回答：", res["answer"])
    print("依据：", res["cited_clause"] or "—")
    if res["refused"]:
        print("拒答原因：", res["reason"])
