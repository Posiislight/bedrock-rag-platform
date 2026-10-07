import time
from dataclasses import dataclass

from ..aws import client
from ..config import get_settings
from ..observability.metrics import record_call
from .pricing import cost_usd


@dataclass
class ChatResult:
    text: str
    model_id: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float


def chat(prompt: str, system: str | None = None, max_tokens: int = 1024, temperature: float = 0.2) -> ChatResult:
    """Single-turn chat via the Bedrock Converse API. Records latency/tokens/cost/errors on every call."""
    model_id = get_settings().model_id
    kwargs = {
        "modelId": model_id,
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
    }
    if system:
        kwargs["system"] = [{"text": system}]

    start = time.perf_counter()
    try:
        resp = client("bedrock-runtime").converse(**kwargs)
    except Exception:
        record_call("chat", model_id, (time.perf_counter() - start) * 1000, 0, 0, 0.0, error=True)
        raise

    latency_ms = (time.perf_counter() - start) * 1000
    usage = resp.get("usage", {})
    tin, tout = usage.get("inputTokens", 0), usage.get("outputTokens", 0)
    cost = cost_usd(model_id, tin, tout)
    record_call("chat", model_id, latency_ms, tin, tout, cost, error=False)
    text = "".join(b.get("text", "") for b in resp["output"]["message"]["content"])
    return ChatResult(text, model_id, tin, tout, latency_ms, cost)
