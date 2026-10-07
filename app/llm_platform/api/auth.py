import hmac
from functools import lru_cache

from fastapi import Header, HTTPException

from ..aws import client
from ..config import get_settings


@lru_cache
def _expected_key() -> str:
    s = get_settings()
    if s.api_key_secret_id:
        return client("secretsmanager").get_secret_value(SecretId=s.api_key_secret_id)["SecretString"].strip()
    return s.api_key_env  # local development only


def require_api_key(x_api_key: str = Header(default="")) -> None:
    expected = _expected_key()
    if not expected or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="invalid or missing X-API-Key")
