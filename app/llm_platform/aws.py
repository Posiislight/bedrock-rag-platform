"""Shared boto3 clients. Credentials come from the EC2 instance role; none are configured here."""
from functools import lru_cache

import boto3
from botocore.config import Config

from .config import get_settings

_CFG = Config(retries={"max_attempts": 5, "mode": "adaptive"}, read_timeout=120)


@lru_cache
def client(service: str):
    return boto3.client(service, region_name=get_settings().region, config=_CFG)


@lru_cache
def dynamodb_table():
    return boto3.resource("dynamodb", region_name=get_settings().region).Table(get_settings().jobs_table)
