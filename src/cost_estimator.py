"""
Cost estimation for translation runs.

Estimates token usage and API cost based on source text length,
batch configuration, and model pricing.
"""

from typing import Dict, List, Optional

# Approximate pricing per 1M tokens (input / output) as of March 2026.
# These are rough estimates — actual pricing may change.
_MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4.1":      {"input": 2.00,  "output": 8.00},
    "gpt-4.1-mini": {"input": 0.40,  "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10,  "output": 0.40},
    "gpt-5.2":      {"input": 3.00,  "output": 12.00},
    "gpt-4o":       {"input": 2.50,  "output": 10.00},
    "gpt-4o-mini":  {"input": 0.15,  "output": 0.60},
}

# Rough chars-per-token ratio for mixed content (English + markup)
_CHARS_PER_TOKEN = 3.5

# Overhead tokens for system prompt + JSON framing per API call
_PROMPT_OVERHEAD_TOKENS = 600

# Output tokens are typically ~1.3x input for translation (target text + JSON envelope)
_OUTPUT_MULTIPLIER = 1.4


def estimate_tokens(text_chars: int) -> int:
    """Estimate token count from character count."""
    return max(1, int(text_chars / _CHARS_PER_TOKEN))


def estimate_cost(
    work_items: List[Dict],
    model: str = "gpt-4.1",
    batch_size: int = 20,
) -> Dict:
    """
    Estimate token usage and cost for a translation run.

    Parameters
    ----------
    work_items : list of dicts with a "text" key
    model      : model identifier
    batch_size : items per API call

    Returns
    -------
    dict with keys:
        total_chars, estimated_input_tokens, estimated_output_tokens,
        estimated_total_tokens, estimated_api_calls, estimated_cost_usd,
        model, pricing_per_1m
    """
    total_chars = sum(len(item.get("text", "")) for item in work_items)
    content_tokens = estimate_tokens(total_chars)

    num_calls = max(1, (len(work_items) + batch_size - 1) // batch_size) if work_items else 0
    prompt_tokens = num_calls * _PROMPT_OVERHEAD_TOKENS

    input_tokens = content_tokens + prompt_tokens
    output_tokens = int(content_tokens * _OUTPUT_MULTIPLIER)

    pricing = _MODEL_PRICING.get(model, _MODEL_PRICING["gpt-4.1"])
    cost_input = (input_tokens / 1_000_000) * pricing["input"]
    cost_output = (output_tokens / 1_000_000) * pricing["output"]
    total_cost = cost_input + cost_output

    return {
        "total_chars": total_chars,
        "estimated_input_tokens": input_tokens,
        "estimated_output_tokens": output_tokens,
        "estimated_total_tokens": input_tokens + output_tokens,
        "estimated_api_calls": num_calls,
        "estimated_cost_usd": round(total_cost, 4),
        "model": model,
        "pricing_per_1m": pricing,
    }
