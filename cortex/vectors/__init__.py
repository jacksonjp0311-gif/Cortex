"""Local deterministic vector index (HNSW) — evidence infrastructure only."""

from .hnsw import HNSWIndex, cosine_similarity
from .index import build_hnsw_index, hnsw_status, query_hnsw

__all__ = [
    "HNSWIndex",
    "cosine_similarity",
    "build_hnsw_index",
    "hnsw_status",
    "query_hnsw",
]
