"""Per-call LLM metrics (latency, tokens, errors, cost) published to CloudWatch in batches."""
import atexit
import logging
import queue
import threading
import time

from ..aws import client

log = logging.getLogger(__name__)
NAMESPACE = "LLMPlatform"


class MetricsPublisher:
    def __init__(self, flush_seconds: float = 5.0, batch_size: int = 20):
        self._q: "queue.Queue[dict]" = queue.Queue(maxsize=10_000)
        self._flush_seconds = flush_seconds
        self._batch_size = batch_size
        self._thread = threading.Thread(target=self._run, daemon=True, name="metrics")
        self._thread.start()
        atexit.register(self.flush)

    def put(self, name: str, value: float, unit: str, operation: str) -> None:
        try:
            self._q.put_nowait({
                "MetricName": name,
                "Dimensions": [{"Name": "Operation", "Value": operation}],
                "Value": value,
                "Unit": unit,
            })
        except queue.Full:
            log.warning("metrics queue full, dropping %s", name)

    def flush(self) -> None:
        batch = []
        while len(batch) < 1000:
            try:
                batch.append(self._q.get_nowait())
            except queue.Empty:
                break
        for i in range(0, len(batch), 1000):
            self._send(batch[i:i + 1000])

    def _send(self, data: list) -> None:
        if not data:
            return
        try:
            client("cloudwatch").put_metric_data(Namespace=NAMESPACE, MetricData=data)
        except Exception:  # metrics must never break a request
            log.exception("put_metric_data failed")

    def _run(self) -> None:
        while True:
            time.sleep(self._flush_seconds)
            self.flush()


_publisher: MetricsPublisher | None = None
_lock = threading.Lock()


def publisher() -> MetricsPublisher:
    global _publisher
    with _lock:
        if _publisher is None:
            _publisher = MetricsPublisher()
        return _publisher


def record_call(operation: str, model_id: str, latency_ms: float, input_tokens: int,
                output_tokens: int, cost_usd: float, error: bool) -> None:
    """Emit one set of metrics and one structured log line for an LLM call."""
    p = publisher()
    p.put("Requests", 1, "Count", operation)
    p.put("LatencyMs", latency_ms, "Milliseconds", operation)
    p.put("InputTokens", input_tokens, "Count", operation)
    p.put("OutputTokens", output_tokens, "Count", operation)
    p.put("CostUSD", cost_usd, "None", operation)
    p.put("Errors", 1 if error else 0, "Count", operation)
    log.info(
        "llm_call operation=%s model=%s latency_ms=%.0f input_tokens=%d output_tokens=%d cost_usd=%.6f error=%s",
        operation, model_id, latency_ms, input_tokens, output_tokens, cost_usd, error,
    )
