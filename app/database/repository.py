from __future__ import annotations

import json
from collections.abc import Iterable
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import ChildChunk, ConversationTurn, DocumentRecord, ParentChunk, SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class DocumentRepository:
    def create_document(
        self,
        filename: str,
        file_type: str,
        file_path: str,
        file_hash: str,
        status: str = "processing",
    ) -> int:
        with session_scope() as session:
            record = DocumentRecord(
                filename=filename,
                file_type=file_type,
                file_path=file_path,
                file_hash=file_hash,
                status=status,
            )
            session.add(record)
            session.flush()
            return int(record.id)

    def get_ready_document_by_hash(self, file_hash: str) -> DocumentRecord | None:
        with session_scope() as session:
            row = session.scalars(
                select(DocumentRecord).where(
                    DocumentRecord.file_hash == file_hash,
                    DocumentRecord.status == "ready",
                )
            ).first()
            return self._detach(row, session) if row else None

    def add_chunks(
        self,
        document_id: int,
        parent_chunks: list[dict],
        child_chunks: list[dict],
        summary: str,
        token_count: int,
    ) -> None:
        with session_scope() as session:
            document = session.get(DocumentRecord, document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")

            parent_id_map: dict[str, int] = {}
            for item in parent_chunks:
                row = ParentChunk(
                    document_id=document_id,
                    chunk_index=item["chunk_index"],
                    content=item["content"],
                    vector_id=item["vector_id"],
                )
                session.add(row)
                session.flush()
                parent_id_map[item["vector_id"]] = row.id

            for item in child_chunks:
                parent_db_id = parent_id_map[item["parent_vector_id"]]
                session.add(
                    ChildChunk(
                        document_id=document_id,
                        parent_chunk_id=parent_db_id,
                        chunk_index=item["chunk_index"],
                        content=item["content"],
                        vector_id=item["vector_id"],
                        parent_vector_id=item["parent_vector_id"],
                    )
                )

            document.summary = summary
            document.status = "ready"
            document.token_count = token_count
            document.parent_chunk_count = len(parent_chunks)
            document.child_chunk_count = len(child_chunks)

    def mark_failed(self, document_id: int, message: str) -> None:
        with session_scope() as session:
            document = session.get(DocumentRecord, document_id)
            if document:
                document.status = "failed"
                document.summary = message[:1000]

    def list_documents(self) -> list[DocumentRecord]:
        with session_scope() as session:
            rows = session.scalars(select(DocumentRecord).order_by(DocumentRecord.created_at.desc())).all()
            return [self._detach(row, session) for row in rows]

    def get_document(self, document_id: int) -> DocumentRecord | None:
        with session_scope() as session:
            row = session.get(DocumentRecord, document_id)
            return self._detach(row, session) if row else None

    def get_documents(self, document_ids: Iterable[int]) -> list[DocumentRecord]:
        ids = list(document_ids)
        if not ids:
            return []
        with session_scope() as session:
            rows = session.scalars(select(DocumentRecord).where(DocumentRecord.id.in_(ids))).all()
            return [self._detach(row, session) for row in rows]

    def delete_document(self, document_id: int) -> None:
        with session_scope() as session:
            row = session.get(DocumentRecord, document_id)
            if row:
                session.delete(row)

    def get_recent_turns(self, session_id: str, limit: int = 8) -> list[ConversationTurn]:
        with session_scope() as session:
            rows = session.scalars(
                select(ConversationTurn)
                .where(ConversationTurn.session_id == session_id)
                .order_by(ConversationTurn.created_at.desc())
                .limit(limit)
            ).all()
            return [self._detach(row, session) for row in reversed(rows)]

    def save_turn(
        self,
        session_id: str,
        mode: str,
        question: str,
        answer: str,
        document_ids: list[int],
        source_chunk_ids: list[str],
    ) -> None:
        with session_scope() as session:
            session.add(
                ConversationTurn(
                    session_id=session_id,
                    mode=mode,
                    question=question,
                    answer=answer,
                    document_ids=json.dumps(document_ids, ensure_ascii=False),
                    source_chunk_ids=json.dumps(source_chunk_ids, ensure_ascii=False),
                )
            )

    @staticmethod
    def _detach(row, session: Session):
        session.expunge(row)
        return row
