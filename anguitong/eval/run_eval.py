# -*- coding: utf-8 -*-
"""跑评测集，输出三个指标。

用法：python eval/run_eval.py
输出：
  - 检索命中率 Recall@5（in / multi 两类）
  - 拒答正确率（out 类）
  - 逐条明细写到 eval/result.csv，人工给「回答可用率」打标
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config as C  # noqa: E402
from answer import ask  # noqa: E402
from retrieve import search  # noqa: E402


def norm(s: str) -> str:
    return (s or "").replace(" ", "").replace("　", "").strip()


def main():
    src = C.EVAL_DIR / "eval_set.csv"
    rows = list(csv.DictReader(src.open(encoding="utf-8-sig")))
    if not rows:
        raise SystemExit("评测集是空的")

    recall_total = recall_hit = 0
    refuse_total = refuse_ok = 0
    details = []

    for r in rows:
        q, typ = r["question"], r["type"]
        gold = norm(r.get("gold_clause", ""))

        if typ in ("in", "multi"):
            hits = search(q)["hits"]
            got = [norm(h["clause"]) for h in hits]
            hit = any(gold and (gold in g or g in gold) for g in got)
            recall_total += 1
            recall_hit += int(hit)
            res = ask(q)
            usable = "待人工判定"
            details.append({
                "id": r["id"], "type": typ, "question": q, "gold": gold,
                "recall_hit": "是" if hit else "否",
                "refused": "是" if res["refused"] else "否",
                "cited": res["cited_clause"], "usable": usable,
                "answer": res["answer"][:120],
            })
            print(f"[{r['id']}] {'✓' if hit else '✗'} 检索  {q[:28]}")
        else:  # out：文档外问题，应该拒答
            res = ask(q)
            ok = bool(res["refused"])
            refuse_total += 1
            refuse_ok += int(ok)
            details.append({
                "id": r["id"], "type": typ, "question": q, "gold": "",
                "recall_hit": "—", "refused": "是" if res["refused"] else "否",
                "cited": res["cited_clause"], "usable": "待人工判定",
                "answer": res["answer"][:120],
            })
            print(f"[{r['id']}] {'✓' if ok else '✗'} 拒答  {q[:28]}")

    print("\n" + "=" * 40)
    if recall_total:
        print(f"检索命中率 Recall@5: {recall_hit}/{recall_total} = {recall_hit / recall_total:.1%}")
    if refuse_total:
        print(f"拒答正确率:          {refuse_ok}/{refuse_total} = {refuse_ok / refuse_total:.1%}")
    print("回答可用率请打开 eval/result.csv，人工把 usable 改成 正确/部分/错误 后统计")

    out = C.EVAL_DIR / "result.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(details[0].keys()))
        w.writeheader()
        w.writerows(details)
    print(f"明细已写入 {out}")


if __name__ == "__main__":
    main()
