from dataclasses import asdict

from ..llm.bedrock import chat
from ..rag.answer import answer_question


def run_job(job_type: str, payload: dict) -> dict:
    if job_type == "chat":
        r = chat(payload["prompt"], payload.get("system"), payload.get("max_tokens", 1024))
        return {"text": r.text, "input_tokens": r.input_tokens, "output_tokens": r.output_tokens,
                "latency_ms": round(r.latency_ms), "cost_usd": round(r.cost_usd, 6)}
    if job_type == "rag":
        return asdict(answer_question(payload["question"], payload.get("top_k", 4)))
    raise ValueError(f"unknown job type: {job_type}")
