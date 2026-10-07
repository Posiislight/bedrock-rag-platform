#!/usr/bin/env bash
# Deploys all CloudFormation stacks in order and uploads the app artifact.
# Usage: VPC_ID=vpc-xxx SUBNET_ID=subnet-xxx [ALLOWED_CIDR=1.2.3.4/32] [ALARM_EMAIL=you@x.com] scripts/deploy.sh
set -euo pipefail

PROJECT="${PROJECT:-llm-platform}"
REGION="${AWS_REGION:-us-east-1}"
CFN_DIR="$(cd "$(dirname "$0")/../infra/cloudformation" && pwd)"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
: "${VPC_ID:?set VPC_ID}"
: "${SUBNET_ID:?set SUBNET_ID}"

deploy() { # name template [params...]
  local name="$1" tpl="$2"; shift 2
  aws cloudformation deploy --region "$REGION" --stack-name "$PROJECT-$name" \
    --template-file "$CFN_DIR/$tpl" --capabilities CAPABILITY_NAMED_IAM \
    --no-fail-on-empty-changeset --parameter-overrides ProjectName="$PROJECT" "$@"
}

deploy secrets       01-secrets.yaml
deploy storage       02-storage.yaml
deploy messaging     03-messaging.yaml

BUCKET=$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$PROJECT-storage" \
  --query "Stacks[0].Outputs[?OutputKey=='DataBucketName'].OutputValue" --output text)
"$ROOT/scripts/package-app.sh" "$BUCKET" "$REGION"

deploy compute       04-compute.yaml VpcId="$VPC_ID" SubnetId="$SUBNET_ID" \
  AllowedCidr="${ALLOWED_CIDR:-0.0.0.0/0}" ModelId="${MODEL_ID:-anthropic.claude-3-haiku-20240307-v1:0}"
deploy observability 05-observability.yaml AlarmEmail="${ALARM_EMAIL:-}"

aws cloudformation describe-stacks --region "$REGION" --stack-name "$PROJECT-compute" \
  --query "Stacks[0].Outputs" --output table
