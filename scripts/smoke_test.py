from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.core.embeddings import build_embedding_service
from app.core.ingestion import IngestionService
from app.core.llm import QwenClient
from app.core.rag_system import RagSystem
from app.database.models import init_database
from app.database.repository import DocumentRepository
from app.document_processor.processor import DocumentProcessor
from app.vector_store.chroma_store import ChromaVectorStore


def reset_local_data() -> None:
    data_dir = ROOT / "data"
    for path in [data_dir / "rag_assistant.sqlite3", data_dir / "chroma"]:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
    (data_dir / "chroma").mkdir(parents=True, exist_ok=True)
    (data_dir / "uploads").mkdir(parents=True, exist_ok=True)


def main() -> None:
    reset_local_data()
    settings = get_settings()
    init_database()
    repository = DocumentRepository()
    embeddings = build_embedding_service(settings)
    vector_store = ChromaVectorStore(settings, embeddings)
    processor = DocumentProcessor(settings)
    ingestion = IngestionService(settings, repository, processor, vector_store)
    rag = RagSystem(settings, repository, vector_store, QwenClient(settings))

    sample_path = ROOT / "sample_docs" / "enterprise_handbook.txt"
    document_id = ingestion.ingest_path(sample_path)
    documents = repository.list_documents()
    assert len(documents) == 1
    assert documents[0].parent_chunk_count >= 1
    assert documents[0].child_chunk_count >= 1

    answer = rag.answer(
        question="合同金额超过 50 万元时需要谁复核？",
        document_ids=[document_id],
        session_id="smoke-test",
    )
    assert answer.answer
    assert answer.sources
    assert "财务" in answer.answer or any("财务" in source.content for source in answer.sources)

    chat = rag.answer(
        question="请用一句话介绍你能做什么。",
        document_ids=[],
        session_id="smoke-test",
    )
    assert chat.answer
    assert chat.mode == "chat"

    stats = vector_store.stats()
    print("智能文档检索助手健康检查通过。")
    print(f"document_id={document_id}, parent_count={stats['parent_count']}, child_count={stats['child_count']}")


if __name__ == "__main__":
    main()
