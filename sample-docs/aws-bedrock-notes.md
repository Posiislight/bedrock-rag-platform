# Amazon Bedrock notes

Amazon Bedrock is a managed service for calling foundation models through a single API.
The Converse API gives a uniform request and response shape across model providers and returns
token usage for every call, which makes per-request cost tracking straightforward.

## Access control

Applications should call Bedrock through an IAM role attached to the compute resource. Scope the
role to bedrock:InvokeModel on the specific foundation-model ARN it needs. Never embed access keys.

## Retries

SQS redelivers a message when the consumer does not delete it before the visibility timeout expires.
After maxReceiveCount deliveries the message moves to the dead-letter queue for inspection.
