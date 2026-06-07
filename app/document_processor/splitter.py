from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    chunk_index: int
    content: str


@dataclass(frozen=True)
class ParentChildChunks:
    parent_chunks: list[Chunk]
    child_chunks: list[tuple[Chunk, int]]


class ParentChildSplitter:
    def __init__(
        self,
        parent_size: int = 1800,
        parent_overlap: int = 180,
        child_size: int = 420,
        child_overlap: int = 80,
    ) -> None:
        self.parent_size = parent_size
        self.parent_overlap = parent_overlap
        self.child_size = child_size
        self.child_overlap = child_overlap

    def split(self, text: str) -> ParentChildChunks:
        normalized = normalize_text(text)
        parents = self._split_text(normalized, self.parent_size, self.parent_overlap)
        child_items: list[tuple[Chunk, int]] = []
        child_index = 0
        for parent in parents:
            children = self._split_text(parent.content, self.child_size, self.child_overlap)
            for child in children:
                child_items.append((Chunk(child_index, child.content), parent.chunk_index))
                child_index += 1
        return ParentChildChunks(parents, child_items)

    def _split_text(self, text: str, chunk_size: int, overlap: int) -> list[Chunk]:
        units = split_into_units(text)
        chunks: list[Chunk] = []
        current = ""
        for unit in units:
            candidate = f"{current}\n{unit}".strip() if current else unit
            if len(candidate) <= chunk_size:
                current = candidate
                continue

            if current:
                chunks.append(Chunk(len(chunks), current.strip()))
                current = tail_text(current, overlap)

            if len(unit) > chunk_size:
                for piece in sliding_window(unit, chunk_size, overlap):
                    chunks.append(Chunk(len(chunks), piece.strip()))
                current = ""
            else:
                current = f"{current}\n{unit}".strip() if current else unit

        if current.strip():
            chunks.append(Chunk(len(chunks), current.strip()))
        return chunks


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_into_units(text: str) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    units: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= 700:
            units.append(paragraph)
            continue
        sentences = re.split(r"(?<=[。！？!?；;])", paragraph)
        units.extend(s.strip() for s in sentences if s.strip())
    return units


def sliding_window(text: str, size: int, overlap: int) -> list[str]:
    step = max(1, size - overlap)
    return [text[start : start + size] for start in range(0, len(text), step) if text[start : start + size].strip()]


def tail_text(text: str, length: int) -> str:
    if length <= 0:
        return ""
    return text[-length:].strip()
