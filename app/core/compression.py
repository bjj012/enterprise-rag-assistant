from __future__ import annotations

from app.vector_store.chroma_store import RetrievedChunk


class ContextCompressor:
    """LLMChainExtractor-style contextual compression with a deterministic fallback."""

    def __init__(self, max_chars: int = 4200) -> None:
        self.max_chars = max_chars

    def compress(self, question: str, parent_chunks: list[RetrievedChunk], child_hits: list[RetrievedChunk]) -> list[RetrievedChunk]:
        keywords = set(extract_keywords(question))
        hit_parent_ids = {hit.parent_vector_id for hit in child_hits}
        ordered = [chunk for chunk in parent_chunks if chunk.vector_id in hit_parent_ids]
        compressed: list[RetrievedChunk] = []
        used = 0
        for parent in ordered:
            text = pick_relevant_sentences(parent.content, keywords)
            if not text:
                text = parent.content[:900]
            remaining = self.max_chars - used
            if remaining <= 0:
                break
            clipped = text[:remaining]
            used += len(clipped)
            compressed.append(
                RetrievedChunk(
                    vector_id=parent.vector_id,
                    parent_vector_id=parent.parent_vector_id,
                    document_id=parent.document_id,
                    filename=parent.filename,
                    content=clipped,
                    score=parent.score,
                    metadata=parent.metadata,
                )
            )
        return compressed


def extract_keywords(text: str) -> list[str]:
    tokens = []
    buffer = ""
    for char in text.lower():
        if "\u4e00" <= char <= "\u9fff":
            if buffer:
                tokens.append(buffer)
                buffer = ""
            tokens.append(char)
        elif char.isalnum():
            buffer += char
        else:
            if buffer:
                tokens.append(buffer)
                buffer = ""
    if buffer:
        tokens.append(buffer)
    return [token for token in tokens if len(token) > 1 or "\u4e00" <= token <= "\u9fff"]


def pick_relevant_sentences(text: str, keywords: set[str]) -> str:
    separators = "。！？!?；;\n"
    sentences = []
    start = 0
    for index, char in enumerate(text):
        if char in separators:
            sentence = text[start : index + 1].strip()
            if sentence:
                sentences.append(sentence)
            start = index + 1
    tail = text[start:].strip()
    if tail:
        sentences.append(tail)

    scored = []
    for sentence in sentences:
        score = sum(1 for keyword in keywords if keyword in sentence.lower())
        if score:
            scored.append((score, sentence))
    scored.sort(key=lambda item: item[0], reverse=True)
    return "\n".join(sentence for _, sentence in scored[:8])
