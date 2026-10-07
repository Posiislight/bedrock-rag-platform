# Bedrock LLM + RAG Platform

An LLM-backed FastAPI service on EC2 calling Amazon Bedrock, with RAG over S3 documents, CloudWatch observability, async inference via SQS, and the whole stack in CloudFormation.

## What's in it

| Folder | What it does |
|---|---|
| `infra/cloudformation/` | 5 stacks: secrets, storage, messaging, compute, observability |
| `app/llm_platform/api/` | FastAPI app, `X-API-Key` auth (key read from Secrets Manager) |
| `app/llm_platform/llm/` | Bedrock Converse client + per-model pricing |
| `app/llm_platform/rag/` | Chunking, Titan embeddings, S3-backed vector index, cited answers |
| `app/llm_platform/observability/` | Batched CloudWatch metrics: latency, tokens, errors, cost |
| `app/llm_platform/jobs/` | SQS worker, DynamoDB job state, retry and dead-letter handling |
| `scripts/` | deploy, package, update, ingest |
| `sample-docs/`, `tests/` | Example corpus; unit tests |

## Architecture

```
client --X-API-Key--> FastAPI (EC2) --Converse--> Bedrock (one chat model)
                         |  \--embed--> Bedrock (Titan embeddings)
                         |--> S3: docs/ + index/ (vectors.npy, chunks.json)
                         |--> SQS inference queue --> worker (EC2) --> DynamoDB job state
                         |                 \--(3 failed receives)--> DLQ
                         \--> CloudWatch: LLMPlatform metrics --> dashboard + alarms --> SNS
```

- **No hard-coded keys.** The instance role can only `bedrock:InvokeModel` on the chat model ARN and the embedding model ARN (embeddings are a separate model, so RAG needs that second ARN). `cloudwatch:PutMetricData` is limited to the `LLMPlatform` namespace. IMDSv2 is enforced and there is no SSH (use SSM Session Manager).
- **Secrets Manager** generates the API key. It is never in the template or the repo.
- **Observability.** Every call emits `Requests`, `LatencyMs`, `InputTokens`, `OutputTokens`, `CostUSD`, `Errors` (dimension `Operation` = `chat` | `embed`). Average `CostUSD` is cost per request. Alarms: error burst, p95 latency, hourly cost, DLQ not empty, queue backlog age.
- **Async.** `POST /v1/jobs` enqueues and returns a `job_id`. On failure the worker leaves the message; SQS retries after the visibility timeout and moves it to the DLQ after `MaxReceiveCount` (3) attempts. Job status is `queued → running → succeeded | retrying | failed`.

## Deploy

Prereqs: AWS CLI configured, Bedrock model access granted for the chat and Titan embedding models in your region.

```bash
export AWS_REGION=us-east-1
VPC_ID=vpc-xxxx SUBNET_ID=subnet-xxxx ALLOWED_CIDR=<your-ip>/32 ALARM_EMAIL=you@example.com scripts/deploy.sh
```

The script deploys the stacks in order, uploads the app to S3, and prints the API URL. Update code later with `scripts/update-app.sh`.

## Use

```bash
export API_URL=http://<public-ip>:8000
export KEY=$(aws secretsmanager get-secret-value --secret-id llm-platform/api-key --query SecretString --output text)

# load documents, build the vector index
API_URL=$API_URL scripts/ingest-docs.sh ./sample-docs

# sync chat
curl -s $API_URL/v1/chat -H "X-API-Key: $KEY" -H 'content-type: application/json' \
  -d '{"prompt":"Explain SQS dead-letter queues in one sentence."}'

# RAG with citations
curl -s $API_URL/v1/rag/query -H "X-API-Key: $KEY" -H 'content-type: application/json' \
  -d '{"question":"How should apps authenticate to Bedrock?"}'

# async
curl -s $API_URL/v1/jobs -H "X-API-Key: $KEY" -H 'content-type: application/json' \
  -d '{"type":"rag","rag":{"question":"What happens after maxReceiveCount?"}}'
curl -s $API_URL/v1/jobs/<job_id> -H "X-API-Key: $KEY"
```

## Local development

```bash
pip install -r requirements-dev.txt
pytest
```

## Notes and limits

- Port 8000 is plain HTTP. Put an ALB with ACM TLS in front before real use, and restrict `AllowedCidr`.
- The vector index is a single in-memory numpy matrix loaded from S3 (fine for thousands of chunks). Swap `rag/store.py` for OpenSearch or pgvector at larger scale.
- `llm/pricing.py` holds on-demand prices; verify them against current Bedrock pricing or override with `INPUT_PRICE_PER_1K` / `OUTPUT_PRICE_PER_1K`.
- This code was unit-tested and the templates pass `cfn-lint`, but it has not been deployed against a live AWS account.
