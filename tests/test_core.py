import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import numpy as np  # noqa: E402

from llm_platform.llm.pricing import cost_usd  # noqa: E402
from llm_platform.rag.chunking import chunk_text  # noqa: E402
from llm_platform.rag.store import VectorIndex  # noqa: E402


def test_chunking_overlaps_and_covers_text():
    text = " ".join(f"Sentence number {i}." for i in range(200))
    chunks = chunk_text(text, size=300, overlap=60)
    assert len(chunks) > 5
    assert all(len(c) <= 300 for c in chunks)
    assert chunks[0].startswith("Sentence number 0.")
    assert chunks[-1].endswith("Sentence number 199.")


def test_chunking_empty():
    assert chunk_text("   ") == []


def test_cost_haiku():
    assert round(cost_usd("anthropic.claude-3-haiku-20240307-v1:0", 1000, 1000), 5) == 0.0015


def test_vector_search_ranks_best_match_first():
    vecs = np.array([[1, 0], [0, 1], [0.7, 0.7]], dtype=np.float32)
    meta = [{"source": f"d{i}", "chunk_index": 0, "text": str(i)} for i in range(3)]
    hits = VectorIndex(vecs, meta).search(np.array([0, 1], dtype=np.float32), top_k=2)
    assert [h.source for h in hits] == ["d1", "d2"]
