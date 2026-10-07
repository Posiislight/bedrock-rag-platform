#!/usr/bin/env bash
# Pushes new app code to the running instance (no stack replacement) via SSM.
set -euo pipefail
PROJECT="${PROJECT:-llm-platform}"; REGION="${AWS_REGION:-us-east-1}"
out() { aws cloudformation describe-stacks --region "$REGION" --stack-name "$PROJECT-$1" \
  --query "Stacks[0].Outputs[?OutputKey=='$2'].OutputValue" --output text; }
BUCKET=$(out storage DataBucketName); INSTANCE=$(out compute InstanceId)
"$(dirname "$0")/package-app.sh" "$BUCKET" "$REGION"
aws ssm send-command --region "$REGION" --instance-ids "$INSTANCE" \
  --document-name AWS-RunShellScript --comment "update llm-platform app" \
  --parameters "commands=[\"aws s3 cp s3://$BUCKET/artifacts/app.tar.gz /tmp/app.tar.gz\",\"tar -xzf /tmp/app.tar.gz -C /opt/llm-platform\",\"/opt/llm-platform/venv/bin/pip install -r /opt/llm-platform/requirements.txt\",\"systemctl restart llm-api llm-worker\"]"
