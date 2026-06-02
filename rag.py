"""Lightweight RAG retrieval core for business knowledge files.

The module is deliberately dependency-tolerant:
1. Use local embeddings from sentence-transformers when installed.
2. Use OpenAI embeddings when an API key is available.
3. Always fall back to keyword retrieval.
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency guard
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parent
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
DATA_DIR = PROJECT_ROOT / "data"
INDEX_FILE = DATA_DIR / "knowledge_index.json"

SUPPORTED_EXTENSIONS = {".md", ".txt"}
DEFAULT_CHUNK_SIZE = 900
DEFAULT_CHUNK_OVERLAP = 120
DEFAULT_LOCAL_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

_LOCAL_MODEL: Any | None = None


@dataclass(frozen=True)
class KnowledgeChunk:
    source: str
    title: str
    content: str
    chunk_id: str

    def as_dict(self) -> dict[str, str]:
        return {
            "source": self.source,
            "title": self.title,
            "content": self.content,
            "chunk_id": self.chunk_id,
        }


def retrieve_knowledge(query: str, top_k: int = 4) -> list[dict[str, Any]]:
    """Retrieve relevant knowledge chunks for a query.

    Returns:
        [
          {
            "source": "knowledge/pricing.md",
            "title": "水管维修价格",
            "content": "...",
            "score": 0.83
          }
        ]
    """

    clean_query = query.strip()
    if not clean_query:
        return []

    top_k = max(1, top_k)
    index = _load_or_build_index()
    chunks = index.get("chunks", [])
    if not chunks:
        return []

    provider = index.get("embedding_provider", "keyword")
    results: list[dict[str, Any]]

    if provider == "local":
        query_embedding = _embed_query_local(clean_query)
        results = _vector_results(chunks, query_embedding) if query_embedding else []
    elif provider == "openai":
        query_embedding = _embed_query_openai(clean_query)
        results = _vector_results(chunks, query_embedding) if query_embedding else []
    else:
        results = []

    if not results:
        results = _keyword_results(chunks, clean_query)

    return [_result_payload(item) for item in results[:top_k]]


def rebuild_knowledge_index() -> dict[str, Any]:
    """Rebuild and persist the knowledge index."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    chunks = [chunk.as_dict() for chunk in _load_knowledge_chunks()]
    provider = "keyword"
    embeddings: list[list[float]] | None = None

    local_embeddings = _embed_texts_local([chunk["content"] for chunk in chunks])
    if local_embeddings:
        provider = "local"
        embeddings = local_embeddings
    else:
        openai_embeddings = _embed_texts_openai([chunk["content"] for chunk in chunks])
        if openai_embeddings:
            provider = "openai"
            embeddings = openai_embeddings

    if embeddings:
        for chunk, embedding in zip(chunks, embeddings, strict=False):
            chunk["embedding"] = embedding

    index = {
        "embedding_provider": provider,
        "chunk_count": len(chunks),
        "sources": sorted({chunk["source"] for chunk in chunks}),
        "chunks": chunks,
    }
    _write_json(INDEX_FILE, index)
    return {
        "status": "ok",
        "embedding_provider": provider,
        "chunk_count": len(chunks),
        "sources": index["sources"],
        "index_file": str(INDEX_FILE),
    }


def get_knowledge_status() -> dict[str, Any]:
    """Return a small status summary for the knowledge index."""

    index_exists = INDEX_FILE.exists()
    index = _read_json(INDEX_FILE, {}) if index_exists else {}
    files = _knowledge_files()
    return {
        "knowledge_dir": str(KNOWLEDGE_DIR),
        "knowledge_dir_exists": KNOWLEDGE_DIR.exists(),
        "index_file": str(INDEX_FILE),
        "index_exists": index_exists,
        "embedding_provider": index.get("embedding_provider", "not_built"),
        "chunk_count": index.get("chunk_count", 0),
        "source_count": len(files),
        "sources": [str(path.relative_to(PROJECT_ROOT)).replace("\\", "/") for path in files],
        "fallback_available": True,
        "local_embedding_available": _local_embedding_available(),
        "openai_embedding_available": bool(_openai_api_key()),
    }


def _load_or_build_index() -> dict[str, Any]:
    index = _read_json(INDEX_FILE, {})
    if _index_is_current(index):
        return index
    rebuild_knowledge_index()
    return _read_json(INDEX_FILE, {})


def _index_is_current(index: dict[str, Any]) -> bool:
    if not index or not isinstance(index.get("chunks"), list):
        return False
    current_files = [str(path.relative_to(PROJECT_ROOT)).replace("\\", "/") for path in _knowledge_files()]
    return sorted(current_files) == sorted(index.get("sources", []))


def _load_knowledge_chunks() -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    for path in _knowledge_files():
        text = _read_text(path)
        if not text.strip():
            continue
        title = _extract_title(text, path)
        source = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        for index, content in enumerate(_split_chunks(text), start=1):
            chunk_id = sha1(f"{source}:{index}:{content}".encode("utf-8")).hexdigest()
            chunks.append(KnowledgeChunk(source=source, title=title, content=content, chunk_id=chunk_id))
    return chunks


def _knowledge_files() -> list[Path]:
    if not KNOWLEDGE_DIR.exists():
        return []
    return sorted(
        path
        for path in KNOWLEDGE_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def _split_chunks(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[str]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    chunks: list[str] = []
    current = ""

    for block in blocks:
        candidate = f"{current}\n\n{block}".strip() if current else block
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.extend(_hard_split(current, chunk_size, overlap))
        current = block

    if current:
        chunks.extend(_hard_split(current, chunk_size, overlap))

    return chunks


def _hard_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    result = []
    start = 0
    step = max(1, chunk_size - overlap)
    while start < len(text):
        result.append(text[start : start + chunk_size].strip())
        start += step
    return [chunk for chunk in result if chunk]


def _extract_title(text: str, path: Path) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or path.stem
    return path.stem


def _embed_texts_local(texts: list[str]) -> list[list[float]] | None:
    if not texts:
        return []
    model = _load_local_model()
    if model is None:
        return None
    try:
        vectors = model.encode(texts, normalize_embeddings=True)
        return [list(map(float, vector)) for vector in vectors]
    except Exception:
        return None


def _embed_query_local(query: str) -> list[float] | None:
    embeddings = _embed_texts_local([query])
    return embeddings[0] if embeddings else None


def _load_local_model() -> Any | None:
    global _LOCAL_MODEL
    if _LOCAL_MODEL is not None:
        return _LOCAL_MODEL
    try:
        from sentence_transformers import SentenceTransformer

        model_name = os.getenv("LOCAL_EMBEDDING_MODEL", DEFAULT_LOCAL_MODEL)
        _LOCAL_MODEL = SentenceTransformer(model_name)
        return _LOCAL_MODEL
    except Exception:
        return None


def _local_embedding_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401

        return True
    except Exception:
        return False


def _embed_texts_openai(texts: list[str]) -> list[list[float]] | None:
    api_key = _openai_api_key()
    if not texts or not api_key:
        return [] if not texts else None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_OPENAI_EMBEDDING_MODEL)
        response = client.embeddings.create(model=model, input=texts)
        return [list(map(float, item.embedding)) for item in response.data]
    except Exception:
        return None


def _embed_query_openai(query: str) -> list[float] | None:
    embeddings = _embed_texts_openai([query])
    return embeddings[0] if embeddings else None


def _openai_api_key() -> str:
    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env")
    value = os.getenv("OPENAI_API_KEY", "").strip()
    if not value or value == "your_api_key_here":
        return ""
    return value


def _vector_results(chunks: list[dict[str, Any]], query_embedding: list[float]) -> list[dict[str, Any]]:
    scored = []
    for chunk in chunks:
        embedding = chunk.get("embedding")
        if not isinstance(embedding, list):
            continue
        score = _cosine_similarity(query_embedding, embedding)
        scored.append({**chunk, "score": score})
    return sorted(scored, key=lambda item: item["score"], reverse=True)


def _keyword_results(chunks: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    query_terms = _tokenize(query)
    scored = []
    for chunk in chunks:
        text = f"{chunk.get('title', '')}\n{chunk.get('content', '')}"
        content_terms = _tokenize(text)
        score = _keyword_score(query_terms, content_terms, query, text)
        if score > 0:
            scored.append({**chunk, "score": score})

    if not scored:
        scored = [{**chunk, "score": 0.0} for chunk in chunks]

    return sorted(scored, key=lambda item: item["score"], reverse=True)


def _tokenize(text: str) -> list[str]:
    lowered = text.lower()
    ascii_terms = re.findall(r"[a-z0-9]+", lowered)
    cjk_text = "".join(re.findall(r"[\u4e00-\u9fff]+", lowered))
    cjk_terms = _cjk_ngrams(cjk_text)
    return ascii_terms + cjk_terms


def _cjk_ngrams(text: str) -> list[str]:
    terms: list[str] = []
    for size in (1, 2, 3, 4):
        if len(text) < size:
            continue
        terms.extend(text[index : index + size] for index in range(0, len(text) - size + 1))
    return terms


def _keyword_score(query_terms: list[str], content_terms: list[str], query: str, content: str) -> float:
    if not query_terms or not content_terms:
        return 0.0
    content_counts: dict[str, int] = {}
    for term in content_terms:
        content_counts[term] = content_counts.get(term, 0) + 1

    matched = sum(content_counts.get(term, 0) for term in query_terms)
    coverage = len({term for term in query_terms if term in content_counts}) / max(1, len(set(query_terms)))
    phrase_bonus = 2.0 if query.strip() and query.strip() in content else 0.0
    score = matched / math.sqrt(len(content_terms)) + coverage + phrase_bonus
    return round(float(score), 6)


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return round(float(dot / (left_norm * right_norm)), 6)


def _result_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": item.get("source", ""),
        "title": item.get("title", ""),
        "content": item.get("content", ""),
        "score": float(item.get("score", 0.0)),
    }


def _read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists() or path.stat().st_size == 0:
            return default
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")
