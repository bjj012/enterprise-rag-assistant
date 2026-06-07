from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.core.embeddings import EmbeddingService


@dataclass(frozen=True)
class RetrievedChunk:
    vector_id: str
    parent_vector_id: str
    document_id: int
    filename: str
    content: str
    score: float
    metadata: dict


class ChromaVectorStore:
    def __init__(self, settings: Settings, embeddings: EmbeddingService) -> None:
        self.settings = settings
        self.embeddings = embeddings
        try:
            import chromadb

            self.backend = "chroma"
            self.client = chromadb.PersistentClient(path=str(settings.chroma_dir))
            self.parent_collection = self.client.get_or_create_collection(
                name=settings.parent_collection,
                metadata={"hnsw:space": "cosine"},
            )
            self.child_collection = self.client.get_or_create_collection(
                name=settings.child_collection,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception:
            self.backend = "local"
            self.local = LocalVectorStore(settings.chroma_dir)

    def add_document_chunks(
        self,
        document_id: int,
        filename: str,
        parent_chunks: list[dict],
        child_chunks: list[dict],
    ) -> None:
        if self.backend == "local":
            self.local.add_document_chunks(document_id, filename, parent_chunks, child_chunks, self.embeddings)
            return

        if parent_chunks:
            self.parent_collection.upsert(
                ids=[item["vector_id"] for item in parent_chunks],
                documents=[item["content"] for item in parent_chunks],
                embeddings=self.embeddings.embed_documents([item["content"] for item in parent_chunks]),
                metadatas=[
                    {
                        "document_id": document_id,
                        "filename": filename,
                        "chunk_index": item["chunk_index"],
                        "vector_id": item["vector_id"],
                    }
                    for item in parent_chunks
                ],
            )

        if child_chunks:
            self.child_collection.upsert(
                ids=[item["vector_id"] for item in child_chunks],
                documents=[item["content"] for item in child_chunks],
                embeddings=self.embeddings.embed_documents([item["content"] for item in child_chunks]),
                metadatas=[
                    {
                        "document_id": document_id,
                        "filename": filename,
                        "chunk_index": item["chunk_index"],
                        "vector_id": item["vector_id"],
                        "parent_vector_id": item["parent_vector_id"],
                    }
                    for item in child_chunks
                ],
            )

    def search_children(self, query: str, document_ids: list[int], top_k: int) -> list[RetrievedChunk]:
        if self.backend == "local":
            return self.local.search_children(query, document_ids, top_k, self.embeddings)

        where = None
        if document_ids:
            where = {"document_id": {"$in": document_ids}} if len(document_ids) > 1 else {"document_id": document_ids[0]}
        result = self.child_collection.query(
            query_embeddings=[self.embeddings.embed_query(query)],
            n_results=max(1, top_k),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        chunks: list[RetrievedChunk] = []
        for vector_id, content, metadata, distance in zip(ids, docs, metadatas, distances):
            score = max(0.0, 1.0 - float(distance))
            chunks.append(
                RetrievedChunk(
                    vector_id=vector_id,
                    parent_vector_id=metadata.get("parent_vector_id", ""),
                    document_id=int(metadata.get("document_id", 0)),
                    filename=metadata.get("filename", ""),
                    content=content,
                    score=score,
                    metadata=metadata,
                )
            )
        return chunks

    def get_parents(self, parent_vector_ids: list[str]) -> dict[str, RetrievedChunk]:
        if self.backend == "local":
            return self.local.get_parents(parent_vector_ids)

        if not parent_vector_ids:
            return {}
        unique_ids = list(dict.fromkeys(parent_vector_ids))
        result = self.parent_collection.get(
            ids=unique_ids,
            include=["documents", "metadatas"],
        )
        parents: dict[str, RetrievedChunk] = {}
        for vector_id, content, metadata in zip(result.get("ids", []), result.get("documents", []), result.get("metadatas", [])):
            parents[vector_id] = RetrievedChunk(
                vector_id=vector_id,
                parent_vector_id=vector_id,
                document_id=int(metadata.get("document_id", 0)),
                filename=metadata.get("filename", ""),
                content=content,
                score=1.0,
                metadata=metadata,
            )
        return parents

    def delete_document(self, document_id: int) -> None:
        if self.backend == "local":
            self.local.delete_document(document_id)
            return

        where = {"document_id": int(document_id)}
        self.parent_collection.delete(where=where)
        self.child_collection.delete(where=where)

    def stats(self) -> dict:
        if self.backend == "local":
            return self.local.stats()

        return {
            "parent_count": self.parent_collection.count(),
            "child_count": self.child_collection.count(),
        }


class LocalVectorStore:
    """Small persistent vector store used when chromadb is unavailable locally."""

    def __init__(self, directory: Path) -> None:
        self.path = Path(directory) / "local_vectors.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._save({"parents": {}, "children": {}})

    def add_document_chunks(
        self,
        document_id: int,
        filename: str,
        parent_chunks: list[dict],
        child_chunks: list[dict],
        embeddings: EmbeddingService,
    ) -> None:
        data = self._load()
        for item in parent_chunks:
            data["parents"][item["vector_id"]] = {
                "content": item["content"],
                "embedding": embeddings.embed_query(item["content"]),
                "metadata": {
                    "document_id": document_id,
                    "filename": filename,
                    "chunk_index": item["chunk_index"],
                    "vector_id": item["vector_id"],
                },
            }
        for item in child_chunks:
            data["children"][item["vector_id"]] = {
                "content": item["content"],
                "embedding": embeddings.embed_query(item["content"]),
                "metadata": {
                    "document_id": document_id,
                    "filename": filename,
                    "chunk_index": item["chunk_index"],
                    "vector_id": item["vector_id"],
                    "parent_vector_id": item["parent_vector_id"],
                },
            }
        self._save(data)

    def search_children(
        self,
        query: str,
        document_ids: list[int],
        top_k: int,
        embeddings: EmbeddingService,
    ) -> list[RetrievedChunk]:
        data = self._load()
        query_vector = embeddings.embed_query(query)
        rows = []
        for vector_id, item in data["children"].items():
            metadata = item["metadata"]
            if document_ids and int(metadata["document_id"]) not in document_ids:
                continue
            score = cosine_similarity(query_vector, item["embedding"])
            rows.append((score, vector_id, item))
        rows.sort(key=lambda item: item[0], reverse=True)
        return [
            RetrievedChunk(
                vector_id=vector_id,
                parent_vector_id=item["metadata"]["parent_vector_id"],
                document_id=int(item["metadata"]["document_id"]),
                filename=item["metadata"]["filename"],
                content=item["content"],
                score=float(score),
                metadata=item["metadata"],
            )
            for score, vector_id, item in rows[:top_k]
        ]

    def get_parents(self, parent_vector_ids: list[str]) -> dict[str, RetrievedChunk]:
        data = self._load()
        parents = {}
        for vector_id in parent_vector_ids:
            item = data["parents"].get(vector_id)
            if not item:
                continue
            metadata = item["metadata"]
            parents[vector_id] = RetrievedChunk(
                vector_id=vector_id,
                parent_vector_id=vector_id,
                document_id=int(metadata["document_id"]),
                filename=metadata["filename"],
                content=item["content"],
                score=1.0,
                metadata=metadata,
            )
        return parents

    def delete_document(self, document_id: int) -> None:
        data = self._load()
        data["parents"] = {
            key: item for key, item in data["parents"].items() if int(item["metadata"]["document_id"]) != document_id
        }
        data["children"] = {
            key: item for key, item in data["children"].items() if int(item["metadata"]["document_id"]) != document_id
        }
        self._save(data)

    def stats(self) -> dict:
        data = self._load()
        return {"parent_count": len(data["parents"]), "child_count": len(data["children"])}

    def _load(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    return sum(a * b for a, b in zip(left, right))
