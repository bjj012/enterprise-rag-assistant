from __future__ import annotations


def build_contextual_compression_retriever(base_retriever, llm):
    """Create a LangChain ContextualCompressionRetriever when LangChain is installed.

    The main application uses a deterministic compressor so local tests do not require
    a paid model key. This adapter keeps the enterprise extension point explicit:
    production teams can pass a Chroma retriever and Qwen/OpenAI-compatible LLM here
    to enable LangChain's ContextualCompressionRetriever + LLMChainExtractor flow.
    """

    try:
        from langchain.retrievers import ContextualCompressionRetriever
        from langchain.retrievers.document_compressors import LLMChainExtractor
    except Exception as exc:  # pragma: no cover - optional integration
        raise RuntimeError("请先安装 langchain 相关依赖后再启用上下文压缩检索器。") from exc

    compressor = LLMChainExtractor.from_llm(llm)
    return ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=base_retriever,
    )
