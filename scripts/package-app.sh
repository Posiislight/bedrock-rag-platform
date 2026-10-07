#!/usr/bin/env bash
# Packages ./app and uploads it to s3://<bucket>/artifacts/app.tar.gz
set -euo pipefail
BUCKET="${1:?usage: package-app.sh <bucket> [region]}"
REGION="${2:-${AWS_REGION:-us-east-1}}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/build"
tar -czf "$ROOT/build/app.tar.gz" -C "$ROOT/app" --exclude='__pycache__' .
aws s3 cp "$ROOT/build/app.tar.gz" "s3://$BUCKET/artifacts/app.tar.gz" --region "$REGION"
