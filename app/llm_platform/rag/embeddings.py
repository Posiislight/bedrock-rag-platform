import json
import time

import numpy as np

from ..aws import client
from ..config import get_settings
from ..llm.pricing import cost_usd
from ..observability.metrics import record_call


def embed(text: str) -> np.ndarray:
    """Embed text with Titan Text Embeddings v2 (normalized, so dot product == cosine)."""
    s = get_settings()
    body = json.dumps({"inputText": text[:8000], "dimensions": s.embedding_dimensions, "normalize": True})
    start = time.perf_counter()
    try:
        resp = client("bedrock-runtime").invoke_model(
            modelId=s.embedding_model_id, body=body, accept="application/json", contentType="application/json")
        payload = json.loads(resp["body"].read())
    except Exception:
        record_call("embed", s.embedding_model_id, (time.perf_counter() - start) * 1000, 0, 0, 0.0, error=True)
        raise
    tokens = payload.get("inputTextTokenCount", 0)
    record_call("embed", s.embedding_model_id, (time.perf_counter() - start) * 1000, tokens, 0,
                cost_usd(s.embedding_model_id, tokens, 0), error=False)
    return np.asarray(payload["embedding"], dtype=np.float32)
