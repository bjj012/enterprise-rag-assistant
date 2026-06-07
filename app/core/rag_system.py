from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.config import Settings
from app.core.compression import ContextCompressor
from app.core.llm import QwenClient
from app.database.repository import DocumentRepository
from app.vector_store.chroma_store import ChromaVectorStore, RetrievedChunk


@dataclass(frozen=True)
class RagAnswer:
    answer: str
    sources: list[RetrievedChunk]
    mode: str


class RagSystem:
    def __init__(
        self,
        settings: Settings,
        repository: DocumentRepository,
        vector_store: ChromaVectorStore,
        llm: QwenClient,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.vector_store = vector_store
        self.llm = llm
        self.compressor = ContextCompressor()

    def answer(
        self,
        question: str,
        document_ids: list[int],
        session_id: str | None = None,
        stream: bool = False,
    ):
        session_id = session_id or uuid.uuid4().hex
        if document_ids:
            result = self._answer_with_knowledge(question, document_ids, session_id)
        else:
            result = self._answer_general(question, session_id)

        self.repository.save_turn(
            session_id=session_id,
            mode=result.mode,
            question=question,
            answer=result.answer,
            document_ids=document_ids,
            source_chunk_ids=[source.vector_id for source in result.sources],
        )
        return result

    def stream_answer(self, question: str, document_ids: list[int], session_id: str):
        result = self.answer(question, document_ids, session_id=session_id, stream=False)
        for char in result.answer:
            yield char
        return result

    def _answer_with_knowledge(self, question: str, document_ids: list[int], session_id: str) -> RagAnswer:
        child_hits = self.vector_store.search_children(question, document_ids, self.settings.retrieval_top_k)
        parent_map = self.vector_store.get_parents([hit.parent_vector_id for hit in child_hits])
        parents = list(parent_map.values())
        compressed = self.compressor.compress(question, parents, child_hits)[: self.settings.compression_top_k]
        history = self._format_history(session_id)
        context = "\n\n".join(
            f"[来源：{item.filename} / parent={item.vector_id}]\n{item.content}" for item in compressed
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "你是企业私有知识库问答助手。回答必须基于检索上下文；"
                    "如果上下文不足，明确说明无法从已选文档确认。回答使用中文，结构清晰。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"【历史对话】\n{history or '无'}\n\n"
                    f"【检索上下文】\n{context or '无可用上下文'}\n\n"
                    f"【用户问题】\n{question}\n\n"
                    "请给出准确回答，并在必要时说明依据来自哪些文档。"
                ),
            },
        ]
        answer = self.llm.chat(messages, stream=False)
        return RagAnswer(answer=str(answer), sources=compressed, mode="knowledge_base")

    def _answer_general(self, question: str, session_id: str) -> RagAnswer:
        history = self._format_history(session_id)
        messages = [
            {"role": "system", "content": "你是专业、简洁的中文 AI 助手。"},
            {"role": "user", "content": f"【历史对话】\n{history or '无'}\n\n【用户问题】\n{question}"},
        ]
        answer = self.llm.chat(messages, stream=False)
        return RagAnswer(answer=str(answer), sources=[], mode="chat")

    def _format_history(self, session_id: str) -> str:
        turns = self.repository.get_recent_turns(session_id, limit=self.settings.history_turns)
        lines = []
        for turn in turns:
            lines.append(f"用户：{turn.question}")
            lines.append(f"助手：{turn.answer[:500]}")
        return "\n".join(lines)
