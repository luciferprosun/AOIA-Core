"""Legacy transitional web-reader surface.

This module is not an approved H4 browser execution path. It must not be
reachable from model/proposal/public runtime flow. Do not use it as an executor.
"""

import os
import requests
from bs4 import BeautifulSoup
import hashlib

from runtime_paths import aoia_state_home

LEGACY_BROWSER_SURFACE = True
APPROVED_RUNTIME_BROWSER_FLOW = False
H4_APPROVED_BROWSER_FLOW = False
BROWSER_EXECUTION_FROZEN = True
AOIA_LEGACY_BROWSER_ENABLED = os.environ.get("AOIA_LEGACY_BROWSER_ENABLED") == "1"


def _require_legacy_browser_enabled() -> None:
    if not AOIA_LEGACY_BROWSER_ENABLED:
        raise RuntimeError(
            "Legacy browser surface is frozen and not approved for runtime use. "
            "Set AOIA_LEGACY_BROWSER_ENABLED=1 only for isolated legacy/manual testing."
        )


def cache_name(url: str):
    cache_dir = aoia_state_home() / "web_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{hashlib.md5(url.encode()).hexdigest()}.txt"

def fetch_page(url: str):
    _require_legacy_browser_enabled()
    cache_file = cache_name(url)

    if cache_file.exists():
        return cache_file.read_text()

    response = requests.get(
        url,
        timeout=20,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    soup = BeautifulSoup(response.text, "html.parser")

    text = soup.get_text(separator="\n")

    cleaned = "\n".join(
        line.strip()
        for line in text.splitlines()
        if line.strip()
    )

    cache_file.write_text(cleaned)

    return cleaned[:15000]

if name == "main":
    url = input("URL: ")
    print(fetch_page(url))
