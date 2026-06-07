from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
CHROMA_DIR = DATA_DIR / "chroma"

load_dotenv(PROJECT_ROOT / ".env")


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    app_name: str = "智能文档检索助手"
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'rag_assistant.sqlite3'}")
    upload_dir: Path = UPLOAD_DIR
    chroma_dir: Path = CHROMA_DIR
    parent_collection: str = os.getenv("PARENT_COLLECTION", "parent_documents")
    child_collection: str = os.getenv("CHILD_COLLECTION", "child_documents")
    embedding_backend: str = os.getenv("EMBEDDING_BACKEND", "hash")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5")
    embedding_dimension: int = _int_env("EMBEDDING_DIMENSION", 768)
    parent_chunk_size: int = _int_env("PARENT_CHUNK_SIZE", 1800)
    parent_chunk_overlap: int = _int_env("PARENT_CHUNK_OVERLAP", 180)
    child_chunk_size: int = _int_env("CHILD_CHUNK_SIZE", 420)
    child_chunk_overlap: int = _int_env("CHILD_CHUNK_OVERLAP", 80)
    retrieval_top_k: int = _int_env("RETRIEVAL_TOP_K", 8)
    compression_top_k: int = _int_env("COMPRESSION_TOP_K", 5)
    history_turns: int = _int_env("HISTORY_TURNS", 6)
    qwen_api_key: str = os.getenv("DASHSCOPE_API_KEY", "")
    qwen_base_url: str = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    qwen_model: str = os.getenv("QWEN_MODEL", "qwen-plus")
    request_timeout: int = _int_env("REQUEST_TIMEOUT", 60)


def get_settings() -> Settings:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return Settings()
