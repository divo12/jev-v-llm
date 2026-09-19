"""Usage-derived list-price estimates, not provider invoices. USD / million tokens."""

import math

PRICE_DATE = "2026-09-19"
PRICES = {
    "gpt-4.1-nano-2025-04-14": (0.10, 0.025, 0.40),
    "gpt-4.1-mini-2025-04-14": (0.40, 0.10, 1.60),
    "gpt-5.4-nano-2026-03-17": (0.20, 0.02, 1.25),
    "gpt-5.4-mini-2026-03-17": (0.75, 0.075, 4.50),
    "gpt-5.4-2026-03-05": (2.50, 0.25, 15.00),
    "jev-1.13.0": (0.042, 0.042, 0),
}
SOURCES = [
    "https://developers.openai.com/api/docs/models/gpt-4.1-nano",
    "https://developers.openai.com/api/docs/models/gpt-4.1-mini",
    "https://developers.openai.com/api/docs/models/gpt-5.4-nano",
    "https://developers.openai.com/api/docs/models/gpt-5.4-mini",
    "https://developers.openai.com/api/docs/models/gpt-5.4",
    "https://typesafe.ai/",
]


def cost(call):
    usage = call.get("usage")
    if call.get("status") != 200 or not isinstance(usage, dict):
        return None
    model = call.get("model")
    if model not in PRICES:
        return None
    if "prompt_tokens" in usage:
        inp, out = usage["prompt_tokens"], usage.get("completion_tokens")
        cached = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
    else:
        inp, out = usage.get("input_tokens"), usage.get("output_tokens")
        cached = 0
    if any(type(x) is not int or x < 0 for x in (inp, out, cached)) or cached > inp:
        return None
    a, b, c = PRICES[model]
    return ((inp - cached) * a + cached * b + out * c) / 1_000_000


def percentile(values, q):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * q) - 1)]
