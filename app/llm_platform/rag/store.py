"""Vector store: embeddings matrix + chunk metadata persisted in S3, searched with numpy cosine similarity.

Fine for thousands of chunks; swap for OpenSearch/pgvector when a single in-memory matrix is outgrown.
"""
import io
import json
import threading
import time
from dataclasses import dataclass

import numpy as np
from botocore.exceptions import ClientError

from ..aws import client
from ..config import get_settings


@dataclass
class Hit:
    source: str
    chunk_index: int
    text: str
    score: float


class VectorIndex:
    def __init__(self, vectors: np.ndarray, meta: list[dict]):
        self.vectors, self.meta = vectors, meta

    def search(self, query: np.ndarray, top_k: int = 4) -> list[Hit]:
        if len(self.meta) == 0:
            return []
        scores = self.vectors @ query
        top = np.argsort(-scores)[:top_k]
        return [Hit(self.meta[i]["source"], self.meta[i]["chunk_index"], self.meta[i]["text"], float(scores[i]))
                for i in top]


_cache: tuple[float, VectorIndex] | None = None
_lock = threading.Lock()
_TTL = 60.0


def invalidate_cache() -> None:
    global _cache
    with _lock:
        _cache = None


def save_index(vectors: np.ndarray, meta: list[dict]) -> None:
    s, s3 = get_settings(), client("s3")
    buf = io.BytesIO()
    np.save(buf, vectors)
    s3.put_object(Bucket=s.data_bucket, Key=f"{s.index_prefix}vectors.npy", Body=buf.getvalue())
    s3.put_object(Bucket=s.data_bucket, Key=f"{s.index_prefix}chunks.json", Body=json.dumps(meta).encode())
    invalidate_cache()


def load_index() -> VectorIndex:
    global _cache
    with _lock:
        if _cache and time.time() - _cache[0] < _TTL:
            return _cache[1]
    s, s3 = get_settings(), client("s3")
    try:
        vec = s3.get_object(Bucket=s.data_bucket, Key=f"{s.index_prefix}vectors.npy")["Body"].read()
        meta = s3.get_object(Bucket=s.data_bucket, Key=f"{s.index_prefix}chunks.json")["Body"].read()
        idx = VectorIndex(np.load(io.BytesIO(vec)), json.loads(meta))
    except ClientError as e:
        if e.response["Error"]["Code"] != "NoSuchKey":
            raise
        idx = VectorIndex(np.zeros((0, s.embedding_dimensions), dtype=np.float32), [])
    with _lock:
        _cache = (time.time(), idx)
    return idx
