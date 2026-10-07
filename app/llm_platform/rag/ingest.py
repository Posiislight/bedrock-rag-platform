import io
import logging

import numpy as np
from pypdf import PdfReader

from ..aws import client
from ..config import get_settings
from .chunking import chunk_text
from .embeddings import embed
from .store import save_index

log = logging.getLogger(__name__)
TEXT_EXT = (".txt", ".md", ".markdown", ".csv", ".json")


def _read(key: str, body: bytes) -> str:
    k = key.lower()
    if k.endswith(".pdf"):
        return "\n\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(body)).pages)
    if k.endswith(TEXT_EXT):
        return body.decode("utf-8", errors="replace")
    return ""


def ingest_all() -> dict:
    """Read every document under s3://<bucket>/docs/, chunk, embed, and rebuild the index."""
    s, s3 = get_settings(), client("s3")
    vectors, meta, docs = [], [], 0
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=s.data_bucket, Prefix=s.docs_prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):
                continue
            text = _read(key, s3.get_object(Bucket=s.data_bucket, Key=key)["Body"].read())
            chunks = chunk_text(text, s.chunk_chars, s.chunk_overlap)
            if not chunks:
                log.info("skipping %s (no text)", key)
                continue
            docs += 1
            for i, c in enumerate(chunks):
                vectors.append(embed(c))
                meta.append({"source": key, "chunk_index": i, "text": c})
    matrix = np.vstack(vectors) if vectors else np.zeros((0, s.embedding_dimensions), dtype=np.float32)
    save_index(matrix, meta)
    return {"documents": docs, "chunks": len(meta)}
