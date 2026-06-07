from __future__ import annotations

import time
import uuid

import streamlit as st

from app.config import get_settings
from app.core.embeddings import build_embedding_service
from app.core.ingestion import IngestionService
from app.core.llm import QwenClient
from app.core.rag_system import RagSystem
from app.database.models import init_database
from app.database.repository import DocumentRepository
from app.document_processor.processor import DocumentProcessor
from app.ui.components import (
    render_chat_message,
    render_document_card,
    render_hero,
    render_metrics,
    render_source,
)
from app.ui.styles import CUSTOM_CSS
from app.vector_store.chroma_store import ChromaVectorStore


st.set_page_config(
    page_title="智能文档检索助手",
    page_icon="KB",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner=False)
def bootstrap():
    settings = get_settings()
    init_database()
    repository = DocumentRepository()
    embeddings = build_embedding_service(settings)
    vector_store = ChromaVectorStore(settings, embeddings)
    processor = DocumentProcessor(settings)
    ingestion = IngestionService(settings, repository, processor, vector_store)
    rag = RagSystem(settings, repository, vector_store, QwenClient(settings))
    return settings, repository, vector_store, ingestion, rag


settings, repository, vector_store, ingestion, rag = bootstrap()

if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_sources" not in st.session_state:
    st.session_state.last_sources = []

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 文档管理")
    uploaded_files = st.file_uploader(
        "上传 PDF / Word / TXT / Markdown",
        type=["pdf", "docx", "txt", "md"],
        accept_multiple_files=True,
    )
    if uploaded_files and st.button("入库并向量化", use_container_width=True):
        progress = st.progress(0)
        for index, uploaded in enumerate(uploaded_files, start=1):
            with st.spinner(f"正在处理：{uploaded.name}"):
                ingestion.ingest_upload(uploaded, uploaded.name)
            progress.progress(index / len(uploaded_files))
        st.success("文档已完成入库。")
        time.sleep(0.4)
        st.rerun()

    documents = repository.list_documents()
    ready_documents = [doc for doc in documents if doc.status == "ready"]
    options = {f"{doc.filename} · #{doc.id}": doc.id for doc in ready_documents}
    selected_labels = st.multiselect(
        "选择知识源",
        options=list(options.keys()),
        default=list(options.keys())[:3],
    )
    selected_document_ids = [options[label] for label in selected_labels]

    st.markdown("### 文档列表")
    if documents:
        for doc in documents[:12]:
            render_document_card(doc)
    else:
        st.info("还没有上传文档。")

    st.markdown("### 运行状态")
    st.caption(f"嵌入模型：{settings.embedding_model}")
    st.caption(f"大模型：{settings.qwen_model if settings.qwen_api_key else '本地检索摘要'}")

documents = repository.list_documents()
stats = vector_store.stats()

render_hero()
render_metrics(len(documents), stats["parent_count"], stats["child_count"])

left, right = st.columns([0.68, 0.32], gap="large")

with left:
    mode_label = "知识库问答" if selected_document_ids else "普通对话"
    st.markdown(f"#### 当前模式：{mode_label}")

    for message in st.session_state.messages:
        render_chat_message(message["role"], message["content"])

    question = st.chat_input("输入问题，选择知识源后自动进入 RAG 模式")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        render_chat_message("user", question)
        with st.spinner("正在检索知识库并生成回答..."):
            result = rag.answer(
                question=question,
                document_ids=selected_document_ids,
                session_id=st.session_state.session_id,
            )

        placeholder = st.empty()
        streamed = ""
        for char in result.answer:
            streamed += char
            placeholder.markdown(
                f'<div class="chat chat-assistant"><div class="bubble bubble-assistant cursor">{streamed}</div></div>',
                unsafe_allow_html=True,
            )
            time.sleep(0.003)
        placeholder.empty()
        render_chat_message("assistant", result.answer)
        st.session_state.messages.append({"role": "assistant", "content": result.answer})
        st.session_state.last_sources = result.sources

with right:
    st.markdown("#### 参考来源")
    if st.session_state.last_sources:
        with st.expander("展开检索片段", expanded=True):
            for index, source in enumerate(st.session_state.last_sources, start=1):
                render_source(source, index)
    else:
        st.info("知识库问答后，这里会显示召回的父级上下文片段。")

    st.markdown("#### 使用建议")
    st.markdown(
        """
        - 上传合同、制度、手册、论文等文档
        - 选择一个或多个知识源后提问
        - 不选择知识源时进入普通对话
        - 参考来源用于核对回答依据
        """
    )
