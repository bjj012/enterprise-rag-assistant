from __future__ import annotations

import hashlib
import math
import re
from functools import cached_property

from app.config import Settings


class EmbeddingService:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class HashEmbeddingService(EmbeddingService):
    """Deterministic local embeddings for development and automated tests."""

    def __init__(self, dimension: int = 768) -> None:
        self.dimension = dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = tokenize(text)
        if not tokens:
            tokens = [text[:64] or "empty"]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        return l2_normalize(vector)


class SentenceTransformerEmbeddingService(EmbeddingService):
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    @cached_property
    def model(self):
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(self.model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [embedding.tolist() for embedding in embeddings]


def build_embedding_service(settings: Settings) -> EmbeddingService:
    if settings.embedding_backend.lower() in {"sentence-transformers", "sentence_transformers", "bge"}:
        return SentenceTransformerEmbeddingService(settings.embedding_model)
    return HashEmbeddingService(settings.embedding_dimension)


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{1,2}", text.lower())
    return words[:2000]


def l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]
