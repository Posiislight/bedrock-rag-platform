"""USD per 1,000 tokens (on-demand). Verify against the Bedrock pricing page and override via env if needed."""
import os

# (input, output)
PRICES_PER_1K = {
    "anthropic.claude-3-haiku-20240307-v1:0": (0.00025, 0.00125),
    "anthropic.claude-3-5-haiku-20241022-v1:0": (0.0008, 0.004),
    "anthropic.claude-3-5-sonnet-20240620-v1:0": (0.003, 0.015),
    "amazon.titan-embed-text-v2:0": (0.00002, 0.0),
}


def cost_usd(model_id: str, input_tokens: int, output_tokens: int) -> float:
    if "INPUT_PRICE_PER_1K" in os.environ and "OUTPUT_PRICE_PER_1K" in os.environ:
        pin, pout = float(os.environ["INPUT_PRICE_PER_1K"]), float(os.environ["OUTPUT_PRICE_PER_1K"])
    else:
        pin, pout = PRICES_PER_1K.get(model_id, (0.0, 0.0))
    return input_tokens / 1000 * pin + output_tokens / 1000 * pout
