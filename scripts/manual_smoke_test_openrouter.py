#!/usr/bin/env python3
"""Manual, explicitly-invoked smoke test against the REAL OpenRouter API.

This script is never run automatically (not by the test suite, not by
the launcher, not by any other script in this repository). It only
runs when a human:

1. sets the OPENROUTER_API_KEY environment variable, and
2. explicitly runs this script directly:

       OPENROUTER_API_KEY=sk-... python3 scripts/manual_smoke_test_openrouter.py

By default it makes exactly one small chat-completion request and then
exits. It does not loop, retry, or fall back to a different provider.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.aoia_desktop_demo.providers.base import ChatMessage, ProviderError  # noqa: E402
from apps.aoia_desktop_demo.providers.openrouter import OpenRouterClient, OpenRouterConfig  # noqa: E402

DEFAULT_MODEL = "openrouter/auto"


def main() -> int:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print(
            "This manual smoke test only runs when you set OPENROUTER_API_KEY "
            "and invoke this script yourself. Example:\n\n"
            "    OPENROUTER_API_KEY=sk-... python3 scripts/manual_smoke_test_openrouter.py\n",
            file=sys.stderr,
        )
        return 1

    model = os.environ.get("AOIA_DEMO_SMOKE_MODEL", DEFAULT_MODEL)
    client = OpenRouterClient(OpenRouterConfig(api_key=api_key, timeout_seconds=30.0))

    print(f"Making exactly one request to OpenRouter using model '{model}'...")
    try:
        result = client.send_chat(
            model=model,
            messages=[ChatMessage(role="user", content="Reply with the single word: OK")],
            max_tokens=10,
        )
    except ProviderError as error:
        print(f"Request failed: {error}", file=sys.stderr)
        return 1

    print(f"Model used: {result.model}")
    print(f"Response: {result.content!r}")
    print("Smoke test complete. No retry, no fallback, no second request was made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
