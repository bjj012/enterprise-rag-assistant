from __future__ import annotations

import hashlib
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.document_processor.loader import load_document_text
from app.document_processor.splitter import ParentChildSplitter


@dataclass(frozen=True)
class ProcessedDocument:
    filename: str
    file_type: str
    file_path: str
    file_hash: str
    text: str
    summary: str
    token_count: int
    parent_chunks: list[dict]
    child_chunks: list[dict]


class DocumentProcessor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.splitter = ParentChildSplitter(
            parent_size=settings.parent_chunk_size,
            parent_overlap=settings.parent_chunk_overlap,
            child_size=settings.child_chunk_size,
            child_overlap=settings.child_chunk_overlap,
        )

    def save_upload(self, file_obj, filename: str) -> Path:
        suffix = Path(filename).suffix.lower()
        safe_name = f"{uuid.uuid4().hex}{suffix}"
        target = self.settings.upload_dir / safe_name
        if hasattr(file_obj, "getbuffer"):
            target.write_bytes(file_obj.getbuffer())
        else:
            with open(target, "wb") as output:
                shutil.copyfileobj(file_obj, output)
        return target

    def process_file(self, path: str | Path, original_name: str | None = None) -> ProcessedDocument:
        file_path = Path(path)
        text = load_document_text(file_path)
        if not text.strip():
            raise ValueError("文档没有提取到有效文本。")

        file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        chunks = self.splitter.split(text)
        document_key = file_hash[:16]
        parent_rows: list[dict] = []
        child_rows: list[dict] = []

        for parent in chunks.parent_chunks:
            parent_vector_id = f"parent-{document_key}-{parent.chunk_index}"
            parent_rows.append(
                {
                    "chunk_index": parent.chunk_index,
                    "content": parent.content,
                    "vector_id": parent_vector_id,
                }
            )

        for child, parent_index in chunks.child_chunks:
            parent_vector_id = f"parent-{document_key}-{parent_index}"
            child_rows.append(
                {
                    "chunk_index": child.chunk_index,
                    "content": child.content,
                    "vector_id": f"child-{document_key}-{child.chunk_index}",
                    "parent_vector_id": parent_vector_id,
                }
            )

        return ProcessedDocument(
            filename=original_name or file_path.name,
            file_type=file_path.suffix.lower().lstrip("."),
            file_path=str(file_path),
            file_hash=file_hash,
            text=text,
            summary=build_summary(text),
            token_count=estimate_token_count(text),
            parent_chunks=parent_rows,
            child_chunks=child_rows,
        )


def estimate_token_count(text: str) -> int:
    chinese_chars = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    latin_words = len([part for part in text.split() if part])
    return chinese_chars + latin_words


def build_summary(text: str, max_length: int = 220) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[:max_length].rstrip()}..."
