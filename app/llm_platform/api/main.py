import logging
from dataclasses import asdict

from botocore.exceptions import ClientError
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from ..jobs import store as jobs
from ..llm.bedrock import chat
from ..rag.answer import answer_question
from ..rag.ingest import ingest_all
from .auth import require_api_key

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
app = FastAPI(title="Bedrock LLM + RAG service", version="1.0.0")
auth = [Depends(require_api_key)]


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=20_000)
    system: str | None = Field(default=None, max_length=5_000)
    max_tokens: int = Field(default=1024, ge=1, le=4096)


class RagRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)
    top_k: int = Field(default=4, ge=1, le=10)


class JobRequest(BaseModel):
    type: str = Field(pattern="^(chat|rag)$")
    chat: ChatRequest | None = None
    rag: RagRequest | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/chat", dependencies=auth)
def chat_endpoint(req: ChatRequest):
    try:
        r = chat(req.prompt, req.system, req.max_tokens)
    except ClientError as e:
        raise HTTPException(status_code=502, detail=e.response["Error"]["Code"])
    return {"text": r.text, "model": r.model_id, "usage": {
        "input_tokens": r.input_tokens, "output_tokens": r.output_tokens,
        "latency_ms": round(r.latency_ms), "cost_usd": round(r.cost_usd, 6)}}


@app.post("/v1/rag/ingest", dependencies=auth)
def ingest_endpoint():
    return ingest_all()


@app.post("/v1/rag/query", dependencies=auth)
def rag_endpoint(req: RagRequest):
    try:
        return asdict(answer_question(req.question, req.top_k))
    except ClientError as e:
        raise HTTPException(status_code=502, detail=e.response["Error"]["Code"])


@app.post("/v1/jobs", status_code=202, dependencies=auth)
def submit_job(req: JobRequest):
    body = req.chat if req.type == "chat" else req.rag
    if body is None:
        raise HTTPException(status_code=422, detail=f"'{req.type}' body is required")
    job_id = jobs.create_job(req.type, body.model_dump())
    return {"job_id": job_id, "status": "queued"}


@app.get("/v1/jobs/{job_id}", dependencies=auth)
def job_status(job_id: str):
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job
