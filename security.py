"""Lightweight app-layer guards. Not a replacement for provider safety controls."""

import re
import time
from collections import deque

MAX_INPUT_CHARS = 8000
MAX_CALLS_PER_WINDOW = 20
WINDOW_SECONDS = 600

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"reveal\s+(the\s+)?system\s+prompt",
    r"(show|print|dump|reveal)\s+.*(api\s*key|secret|token|credentials)",
    r"jailbreak",
    r"developer\s+message",
    r"hidden\s+(prompt|instructions)",
]

SECRET_PATTERNS = [
    r"sk-or-v1-[A-Za-z0-9_-]{20,}",
    r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----",
]


def validate_user_input(text: str) -> tuple[bool, str]:
    """Reject obvious injection, secret leakage, and excessive input."""
    if not text or not text.strip():
        return False, "Please enter an answer first."

    if len(text) > MAX_INPUT_CHARS:
        return False, f"Input is too long. Limit answers to {MAX_INPUT_CHARS:,} characters."

    lowered = text.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            return False, (
                "This input looks like a prompt-injection or secret-extraction attempt. "
                "Please keep the response focused on interview practice."
            )

    for pattern in SECRET_PATTERNS:
        if re.search(pattern, text):
            return False, (
                "Your message appears to contain a secret or private key. "
                "Remove credentials before submitting."
            )

    return True, ""


def enforce_rate_limit(session_state) -> tuple[bool, str]:
    """Simple per-session rate limiter to reduce automated abuse/cost spikes."""
    now = time.time()
    if "api_call_times" not in session_state:
        session_state.api_call_times = deque()

    calls = session_state.api_call_times
    while calls and now - calls[0] > WINDOW_SECONDS:
        calls.popleft()

    if len(calls) >= MAX_CALLS_PER_WINDOW:
        return False, (
            "Rate limit reached for this session. "
            "Please wait before making more model requests."
        )

    calls.append(now)
    return True, ""
