# -*- coding: utf-8 -*-
"""splitter 的自测。运行：python test_splitter.py"""
from splitter import chunk_text, clean_lines, split_by_clause

SAMPLE_PAGES = [
    """化工企业特殊作业安全规范
第一章 总则
第一条 为规范特殊作业安全管理，防止事故发生，制定本规范。
第二条 本规范适用于本企业区域内的一切特殊作业。
第二章 动火作业
第一节 分级
第三条 动火作业分为一级动火、二级动火和三级动火。
一级动火由企业主要负责人审批；二级动火由安全管理部门审批；
三级动火由作业所在车间负责人审批。
第四条 动火作业前应办理动火作业许可证，许可证有效期不超过8小时。
""",
    """化工企业特殊作业安全规范
第三章 受限空间作业
第五条 进入受限空间作业前，应进行氧含量、可燃气体、有毒气体检测。
氧含量应为19.5%~21%，检测合格后方可进入。
""",
]

text = clean_lines(SAMPLE_PAGES)
assert "化工企业特殊作业安全规范" not in text, "页眉未被清除"
print("页眉清除：OK")

clauses = split_by_clause(text)
print(f"切出 {len(clauses)} 条：")
for no, body in clauses:
    first = body.replace("\n", " ")[:52]
    print(f"  {no or '(无编号)'}  {first}")

assert len(clauses) == 5, f"应为 5 条，实际 {len(clauses)}"
nos = [no for no, _ in clauses]
assert nos == ["第一条", "第二条", "第三条", "第四条", "第五条"], nos

# 章节路径应被注入
c3 = dict(clauses)["第三条"]
assert "第二章 动火作业" in c3 and "第一节 分级" in c3, "第三条缺少章节路径"
print("章节路径注入：OK")

c5 = dict(clauses)["第五条"]
assert "第三章 受限空间作业" in c5
print("跨章路径：OK")

# 二次切分
long_body = c3 + "。" + "作业前应清除周围可燃物并配备灭火器材。" * 40
parts = chunk_text("第三条", long_body, max_chars=200)
print(f"\n长条款切成 {len(parts)} 段，首段长度 {len(parts[0])}，尾段长度 {len(parts[-1])}")
assert all(len(p) <= 260 for p in parts), "二次切分后仍过长"
assert "续" in parts[1], "续段缺少标记"
print("二次切分：OK")

print("\n全部通过")
