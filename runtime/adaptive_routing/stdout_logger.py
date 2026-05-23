#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


def new_correlation_id() -> str:
    """Create a short correlation id for one local AOIA decision trace."""
    return uuid4().hex[:12]


def log_event(correlation_id: str, event: str, detail: str = "") -> None:
    """Write one plain-text AOIA log line to stdout."""
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    suffix = f" detail={detail}" if detail else ""
    print(f"ts={timestamp} cid={correlation_id} event={event}{suffix}")


if __name__ == "__main__":
    cid = new_correlation_id()
    log_event(cid, "aoia_logger_ready", "stdout_only=true")

