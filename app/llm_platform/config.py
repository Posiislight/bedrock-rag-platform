import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    region: str
    model_id: str
    embedding_model_id: str
    embedding_dimensions: int
    data_bucket: str
    jobs_table: str
    queue_url: str
    queue_max_receives: int
    api_key_secret_id: str
    api_key_env: str
    docs_prefix: str = "docs/"
    index_prefix: str = "index/"
    chunk_chars: int = 1000
    chunk_overlap: int = 200


@lru_cache
def get_settings() -> Settings:
    e = os.environ.get
    return Settings(
        region=e("AWS_REGION", "us-east-1"),
        model_id=e("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0"),
        embedding_model_id=e("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0"),
        embedding_dimensions=int(e("EMBEDDING_DIMENSIONS", "512")),
        data_bucket=e("DATA_BUCKET", ""),
        jobs_table=e("JOBS_TABLE", ""),
        queue_url=e("QUEUE_URL", ""),
        queue_max_receives=int(e("QUEUE_MAX_RECEIVES", "3")),
        api_key_secret_id=e("API_KEY_SECRET_ID", ""),
        api_key_env=e("API_KEY", ""),
    )
