import json
import time
import uuid

from ..aws import client, dynamodb_table
from ..config import get_settings

TTL_SECONDS = 7 * 24 * 3600


def create_job(job_type: str, payload: dict) -> str:
    job_id = str(uuid.uuid4())
    now = int(time.time())
    dynamodb_table().put_item(Item={
        "job_id": job_id, "type": job_type, "status": "queued",
        "created_at": now, "expires_at": now + TTL_SECONDS,
    })
    client("sqs").send_message(
        QueueUrl=get_settings().queue_url,
        MessageBody=json.dumps({"job_id": job_id, "type": job_type, "payload": payload}))
    return job_id


def get_job(job_id: str) -> dict | None:
    item = dynamodb_table().get_item(Key={"job_id": job_id}).get("Item")
    if not item:
        return None
    if "result" in item:
        item["result"] = json.loads(item["result"])
    return {k: (int(v) if hasattr(v, "as_tuple") else v) for k, v in item.items()}


def set_status(job_id: str, status: str, result: dict | None = None, error: str | None = None,
               attempts: int | None = None) -> None:
    expr = ["#s = :s", "updated_at = :u"]
    names = {"#s": "status"}
    values: dict = {":s": status, ":u": int(time.time())}
    if result is not None:
        expr.append("#r = :r")
        names["#r"] = "result"
        values[":r"] = json.dumps(result)
    if error is not None:
        expr.append("#e = :e")
        names["#e"] = "error"
        values[":e"] = error[:1000]
    if attempts is not None:
        expr.append("attempts = :a")
        values[":a"] = attempts
    dynamodb_table().update_item(
        Key={"job_id": job_id}, UpdateExpression="SET " + ", ".join(expr),
        ExpressionAttributeNames=names, ExpressionAttributeValues=values)
