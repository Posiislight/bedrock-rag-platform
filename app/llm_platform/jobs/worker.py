"""SQS worker.

Success -> delete the message. Failure -> leave it: SQS redelivers after the visibility timeout and,
after maxReceiveCount attempts, moves it to the dead-letter queue.
"""
import json
import logging
import signal

from ..aws import client
from ..config import get_settings
from . import store
from .handlers import run_job

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("worker")
_running = True


def _stop(*_):
    global _running
    _running = False


def handle(msg: dict) -> None:
    s, sqs = get_settings(), client("sqs")
    body = json.loads(msg["Body"])
    job_id = body["job_id"]
    attempt = int(msg["Attributes"].get("ApproximateReceiveCount", "1"))
    store.set_status(job_id, "running", attempts=attempt)
    try:
        result = run_job(body["type"], body["payload"])
    except Exception as e:
        final = attempt >= s.queue_max_receives
        log.exception("job %s failed (attempt %d/%d)", job_id, attempt, s.queue_max_receives)
        store.set_status(job_id, "failed" if final else "retrying",
                         error=f"{type(e).__name__}: {e}", attempts=attempt)
        return  # not deleted: retried, then dead-lettered
    store.set_status(job_id, "succeeded", result=result, attempts=attempt)
    sqs.delete_message(QueueUrl=s.queue_url, ReceiptHandle=msg["ReceiptHandle"])


def main() -> None:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    s, sqs = get_settings(), client("sqs")
    log.info("worker polling %s", s.queue_url)
    while _running:
        resp = sqs.receive_message(QueueUrl=s.queue_url, MaxNumberOfMessages=5, WaitTimeSeconds=20,
                                   AttributeNames=["ApproximateReceiveCount"])
        for msg in resp.get("Messages", []):
            handle(msg)


if __name__ == "__main__":
    main()
