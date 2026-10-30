# -*- coding: utf-8 -*-
"""Streamlit 界面。运行：streamlit run app.py"""
import streamlit as st

from answer import ask

st.set_page_config(page_title="安规通", page_icon="🦺", layout="centered")

st.title("🦺 安规通")
st.caption("化工安全规程问答 · 每个回答都给出条款出处 · 查不到会明说")

with st.sidebar:
    st.subheader("说明")
    st.markdown(
        "- 回答**只依据**已入库的规程\n"
        "- 每条回答都带条款号，可回查原文\n"
        "- 置信度不足时**拒答**，不猜\n"
    )
    st.divider()
    st.caption("个人项目 · 仅供学习演示，不能替代正式安全审查")

if "history" not in st.session_state:
    st.session_state.history = []

for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("hits"):
            with st.expander("查看召回的条款"):
                for n, h in enumerate(msg["hits"], 1):
                    st.markdown(f"**[{n}] {h['clause'] or '无编号'}**  · 相似度 {h['sim']:.3f}")
                    st.text(h["text"][:600])

q = st.chat_input("例如：动火作业分几级，分别由谁审批？")
if q:
    st.session_state.history.append({"role": "user", "content": q})
    with st.chat_message("user"):
        st.markdown(q)

    with st.chat_message("assistant"):
        with st.spinner("检索条款中…"):
            res = ask(q)
        text = res["answer"]
        if res["cited_clause"]:
            text += f"\n\n> 依据：{res['cited_clause']}"
        else:
            text += "\n\n> 未给出条款依据"
        st.markdown(text)
        if res["refused"]:
            st.caption(f"拒答原因：{res['reason']}")
        with st.expander("查看召回的条款"):
            for n, h in enumerate(res["hits"], 1):
                st.markdown(f"**[{n}] {h['clause'] or '无编号'}**  · 相似度 {h['sim']:.3f}")
                st.text(h["text"][:600])

    st.session_state.history.append(
        {"role": "assistant", "content": text, "hits": res["hits"]}
    )
