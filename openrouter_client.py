"""Minimal OpenRouter Chat Completions client."""

from __future__ import annotations

import os
import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
DEFAULT_MODEL = "openai/gpt-5-mini"


def get_api_key(streamlit_module=None) -> str | None:
    """Read key from Streamlit secrets first, then environment."""
    if streamlit_module is not None:
        try:
            key = streamlit_module.secrets.get("OPENROUTER_API_KEY")
            if key:
                return str(key)
        except Exception:
            pass
    return os.getenv("OPENROUTER_API_KEY")


def chat_completion(
    *,
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1200,
    temperature: float = 0.4,
    reasoning_effort: str | None = "low",
) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Optional OpenRouter attribution headers:
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "AI Solutions Architect Interview Coach",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if reasoning_effort:
        # Reasoning models (e.g. the gpt-5 family) spend part of max_tokens on
        # hidden reasoning before writing the visible answer. Capping effort
        # keeps enough of the budget free for actual output — without it,
        # short max_tokens values can be fully consumed by reasoning, leaving
        # an empty `content` (and no `reasoning` text) in the response.
        payload["reasoning"] = {"effort": reasoning_effort}

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=90,
    )

    if not response.ok:
        detail = response.text[:800]
        raise RuntimeError(
            f"OpenRouter request failed ({response.status_code}): {detail}"
        )

    data = response.json()
    message = data["choices"][0]["message"]
    # Some OpenRouter responses place model reasoning in a separate field
    # and may set `content` to null. Prefer `content`, then fall back to
    # `reasoning` if available so callers receive a usable string.
    content = message.get("content") or message.get("reasoning")
    return {
        "content": content,
        "usage": data.get("usage", {}),
        "model": data.get("model", model),
    }


def get_model_pricing(model: str) -> dict | None:
    """Look up a model's per-token USD pricing from OpenRouter's public model list."""
    response = requests.get(OPENROUTER_MODELS_URL, timeout=15)
    response.raise_for_status()
    for entry in response.json().get("data", []):
        if entry.get("id") == model:
            pricing = entry.get("pricing") or {}
            return {
                "prompt": float(pricing.get("prompt") or 0),
                "completion": float(pricing.get("completion") or 0),
            }
    return None


def estimate_cost(usage: dict, pricing: dict) -> float:
    """Estimate USD cost of a call from its token usage and per-token pricing."""
    prompt_tokens = usage.get("prompt_tokens") or 0
    completion_tokens = usage.get("completion_tokens") or 0
    return prompt_tokens * pricing["prompt"] + completion_tokens * pricing["completion"]
