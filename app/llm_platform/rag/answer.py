import re
from dataclasses import dataclass, field

from ..llm.bedrock import chat
from .embeddings import embed
from .store import Hit, load_index

SYSTEM = (
    "You answer questions using ONLY the numbered context passages. Cite every claim with its passage "
    "number in square brackets, like [1] or [2][3]. If the context does not contain the answer, say you "
    "do not know. Never invent citations."
)


@dataclass
class RagAnswer:
    answer: str
    citations: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)


def _prompt(question: str, hits: list[Hit]) -> str:
    ctx = "\n\n".join(f"[{i}] (source: {h.source})\n{h.text}" for i, h in enumerate(hits, 1))
    return f"Context:\n{ctx}\n\nQuestion: {question}"


def answer_question(question: str, top_k: int = 4, max_tokens: int = 768) -> RagAnswer:
    hits = load_index().search(embed(question), top_k)
    if not hits:
        return RagAnswer("No documents have been ingested yet.")
    result = chat(_prompt(question, hits), system=SYSTEM, max_tokens=max_tokens)
    cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", result.text) if 1 <= int(n) <= len(hits)})
    citations = [{
        "ref": n, "source": hits[n - 1].source, "chunk_index": hits[n - 1].chunk_index,
        "score": round(hits[n - 1].score, 4), "snippet": hits[n - 1].text[:300],
    } for n in cited]
    usage = {"input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
             "latency_ms": round(result.latency_ms), "cost_usd": round(result.cost_usd, 6)}
    return RagAnswer(result.text, citations, usage)
