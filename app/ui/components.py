from __future__ import annotations

import html

import streamlit as st


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero">
          <h1>智能文档检索助手</h1>
          <p>企业级私有知识库问答系统，支持文档入库、父子切分、向量召回、上下文压缩和来源追溯。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metrics(document_count: int, parent_count: int, child_count: int) -> None:
    st.markdown(
        f"""
        <div class="metric-row">
          <div class="metric-card"><strong>{document_count}</strong><span>知识库文档</span></div>
          <div class="metric-card"><strong>{parent_count}</strong><span>父级上下文块</span></div>
          <div class="metric-card"><strong>{child_count}</strong><span>精准召回子块</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_document_card(document) -> None:
    status_class = {
        "ready": "status-ready",
        "processing": "status-processing",
        "failed": "status-failed",
    }.get(document.status, "status-processing")
    st.markdown(
        f"""
        <div class="doc-card">
          <div class="doc-title">{html.escape(document.filename)}</div>
          <div class="doc-meta">{document.file_type.upper()} · {document.token_count} tokens ·
            {document.parent_chunk_count} 父块 / {document.child_chunk_count} 子块</div>
          <span class="status {status_class}">{document.status}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_chat_message(role: str, content: str) -> None:
    role_class = "chat-user" if role == "user" else "chat-assistant"
    bubble_class = "bubble-user" if role == "user" else "bubble-assistant"
    st.markdown(
        f"""
        <div class="chat {role_class}">
          <div class="bubble {bubble_class}">{html.escape(content).replace(chr(10), "<br>")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_source(source, index: int) -> None:
    content = source.content.strip()
    if len(content) > 520:
        content = f"{content[:520]}..."
    st.markdown(
        f"""
        <div class="source-card">
          <h4>来源 {index} · {html.escape(source.filename)} · 相关度 {source.score:.2f}</h4>
          <p>{html.escape(content).replace(chr(10), "<br>")}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
