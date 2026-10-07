#!/usr/bin/env bash
# Uploads a folder of documents to S3 and asks the API to (re)build the vector index.
# Usage: API_URL=http://<ip>:8000 scripts/ingest-docs.sh ./sample-docs
set -euo pipefail
PROJECT="${PROJECT:-llm-platform}"; REGION="${AWS_REGION:-us-east-1}"
DIR="${1:?usage: ingest-docs.sh <dir>}"; : "${API_URL:?set API_URL}"
BUCKET=$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$PROJECT-storage" \
  --query "Stacks[0].Outputs[?OutputKey=='DataBucketName'].OutputValue" --output text)
KEY=$(aws secretsmanager get-secret-value --region "$REGION" --secret-id "$PROJECT/api-key" --query SecretString --output text)
aws s3 sync "$DIR" "s3://$BUCKET/docs/" --region "$REGION"
curl -sS -X POST "$API_URL/v1/rag/ingest" -H "X-API-Key: $KEY"; echo
