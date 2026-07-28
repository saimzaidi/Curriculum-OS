from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
from turbovec import IdMapIndex

from .db import ROOT, connect
from .errors import DomainError
from .services import dump, now, row, rows
from . import rag_anything_adapter


DIMENSION = 96
INDEX_DIR = ROOT / "data" / "retrieval"


def _tokens(text: str) -> list[str]:
    return [token for token in "".join(char.lower() if char.isalnum() else " " for char in text).split() if len(token) > 1]


def _embed(text: str) -> np.ndarray:
    """Deterministic dev embedder; replace with the configured RAG-Anything embedding provider in production."""
    vector = np.zeros(DIMENSION, dtype=np.float32)
    for token, count in Counter(_tokens(text)).items():
        digest = hashlib.blake2b(token.encode(), digest_size=16).digest()
        for offset in range(0, len(digest), 2):
            index = int.from_bytes(digest[offset:offset + 2], "big") % DIMENSION
            vector[index] += 1.0 if digest[offset] & 1 else -1.0
        vector *= float(count)
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm else vector


def _external_id(block_id: str) -> int:
    return int.from_bytes(hashlib.blake2b(block_id.encode(), digest_size=8).digest(), "big")


def _blocks(course_id: str) -> list[dict]:
    with connect() as conn:
        return rows(conn.execute("SELECT id,document_id,page_number,block_index,block_type,normalized_text,content_hash FROM source_blocks WHERE course_id=? ORDER BY document_id,page_number,block_index", (course_id,)).fetchall())


def rebuild(course_id: str) -> dict:
    blocks = _blocks(course_id)
    if not blocks:
        raise DomainError("NO_SOURCE_BLOCKS", "Add source blocks before building retrieval.", status_code=422)
    ids = np.ascontiguousarray(np.array([_external_id(block["id"]) for block in blocks], dtype=np.uint64))
    if len(set(ids.tolist())) != len(blocks):
        raise DomainError("RETRIEVAL_ID_COLLISION", "Unable to build a stable vector index; retry after changing source blocks.", status_code=500)
    vectors = np.ascontiguousarray(np.vstack([_embed(block["normalized_text"]) for block in blocks]).astype(np.float32))
    index = IdMapIndex(dim=DIMENSION, bit_width=4)
    index.add_with_ids(vectors, ids)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    index_path = INDEX_DIR / f"{course_id}.tvim"
    index.write(str(index_path))
    mapping_path = INDEX_DIR / f"{course_id}.json"
    mapping_path.write_text(json.dumps({str(_external_id(block["id"])): block["id"] for block in blocks}), encoding="utf-8")
    snapshot = hashlib.sha256("".join(block["content_hash"] for block in blocks).encode()).hexdigest()
    details = {"index_path": str(index_path), "mapping_path": str(mapping_path), "dimension": DIMENSION, "vectors": len(blocks), "rag_anything": rag_anything_adapter.sync(course_id, blocks)}
    with connect() as conn:
        conn.execute("INSERT OR REPLACE INTO retrieval_indexes VALUES(?,?,?,?,?,?)", (course_id, "turbovec+raganything", snapshot, "ready", dump(details), now()))
    return {"status": "ready", **details}


def search(course_id: str, query: str, limit: int = 8) -> dict:
    if not query.strip():
        raise DomainError("INVALID_QUERY", "Enter a retrieval query.", status_code=422)
    index_path, mapping_path = INDEX_DIR / f"{course_id}.tvim", INDEX_DIR / f"{course_id}.json"
    if not index_path.is_file() or not mapping_path.is_file():
        rebuild(course_id)
    index = IdMapIndex.load(str(index_path))
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    query_vector = np.ascontiguousarray(_embed(query).reshape(1, -1).astype(np.float32))
    scores, result_ids = index.search(query_vector, k=min(limit * 3, len(mapping)))
    vector_rank = {mapping.get(str(int(identifier))): float(score) for score, identifier in zip(scores[0], result_ids[0]) if mapping.get(str(int(identifier)))}
    terms = set(_tokens(query))
    candidates = _blocks(course_id)
    ranked = []
    for block in candidates:
        lexical = len(terms & set(_tokens(block["normalized_text"]))) / max(1, len(terms))
        vector = vector_rank.get(block["id"], 0.0)
        score = lexical * 0.65 + max(vector, 0.0) * 0.35
        if score > 0:
            ranked.append({"block_id": block["id"], "document_id": block["document_id"], "page_number": block["page_number"], "block_type": block["block_type"], "text": block["normalized_text"], "score": round(score, 5), "lexical_score": round(lexical, 5), "vector_score": round(vector, 5)})
    ranked.sort(key=lambda item: (-item["score"], item["page_number"], item["block_id"]))
    return {"query": query, "engine": "hybrid lexical + TurboVec; RAG-Anything multimodal adapter configured separately", "results": ranked[:limit]}
