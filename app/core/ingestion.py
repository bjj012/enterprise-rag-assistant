from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.database.repository import DocumentRepository
from app.document_processor.processor import DocumentProcessor, ProcessedDocument
from app.vector_store.chroma_store import ChromaVectorStore


class IngestionService:
    def __init__(
        self,
        settings: Settings,
        repository: DocumentRepository,
        processor: DocumentProcessor,
        vector_store: ChromaVectorStore,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.processor = processor
        self.vector_store = vector_store

    def ingest_path(self, path: str | Path, original_name: str | None = None) -> int:
        processed = self.processor.process_file(path, original_name=original_name)
        return self._persist(processed)

    def ingest_upload(self, file_obj, filename: str) -> int:
        path = self.processor.save_upload(file_obj, filename)
        processed = self.processor.process_file(path, original_name=filename)
        return self._persist(processed)

    def _persist(self, processed: ProcessedDocument) -> int:
        document_id = self.repository.create_document(
            filename=processed.filename,
            file_type=processed.file_type,
            file_path=processed.file_path,
            file_hash=processed.file_hash,
            status="processing",
        )
        try:
            parent_chunks, child_chunks = namespace_vector_ids(
                document_id=document_id,
                parent_chunks=processed.parent_chunks,
                child_chunks=processed.child_chunks,
            )
            self.vector_store.add_document_chunks(
                document_id=document_id,
                filename=processed.filename,
                parent_chunks=parent_chunks,
                child_chunks=child_chunks,
            )
            self.repository.add_chunks(
                document_id=document_id,
                parent_chunks=parent_chunks,
                child_chunks=child_chunks,
                summary=processed.summary,
                token_count=processed.token_count,
            )
            return document_id
        except Exception as exc:
            self.vector_store.delete_document(document_id)
            self.repository.mark_failed(document_id, str(exc))
            raise


def namespace_vector_ids(document_id: int, parent_chunks: list[dict], child_chunks: list[dict]) -> tuple[list[dict], list[dict]]:
    parent_index_to_vector_id = {
        item["chunk_index"]: f"parent-doc{document_id}-{item['chunk_index']}" for item in parent_chunks
    }
    namespaced_parents = [
        {
            **item,
            "vector_id": parent_index_to_vector_id[item["chunk_index"]],
        }
        for item in parent_chunks
    ]
    namespaced_children = []
    for item in child_chunks:
        parent_index = int(item["parent_vector_id"].rsplit("-", 1)[-1])
        namespaced_children.append(
            {
                **item,
                "vector_id": f"child-doc{document_id}-{item['chunk_index']}",
                "parent_vector_id": parent_index_to_vector_id[parent_index],
            }
        )
    return namespaced_parents, namespaced_children
