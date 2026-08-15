#!/usr/bin/env python3
"""Start one loopback-only final AIOA recording application."""

from __future__ import annotations

import http.client
import json
import os
import socket
import sys

import uvicorn

from apps.aoia_desktop_demo.recording_web import DemoEngine, create_app
from apps.aoia_desktop_demo.recording_web.cockroach_runtime import start_owned_runtime


DEFAULT_PORT = 8765


def _port() -> int:
    try:
        value = int(os.environ.get("AIOA_RECORDING_PORT", str(DEFAULT_PORT)))
    except ValueError as error:
        raise RuntimeError("AIOA_RECORDING_PORT_INVALID") from error
    if not 1024 <= value <= 65535:
        raise RuntimeError("AIOA_RECORDING_PORT_INVALID")
    return value


def _already_ready(port: int) -> bool:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
    try:
        connection.request("GET", "/health")
        response = connection.getresponse()
        raw = response.read(4097)
        if response.status != 200 or len(raw) > 4096:
            return False
        payload = json.loads(raw)
        return (
            isinstance(payload, dict)
            and payload.get("status") == "READY"
            and payload.get("mode") == "AIOA_FINAL_RECORDING_DEMO"
        )
    except (OSError, http.client.HTTPException, json.JSONDecodeError, UnicodeError):
        return False
    finally:
        connection.close()


def _assert_available(port: int) -> None:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind(("127.0.0.1", port))
    except OSError as error:
        raise RuntimeError("LOCAL_PORT_OCCUPIED") from error
    finally:
        probe.close()


def main() -> int:
    port = _port()
    if _already_ready(port):
        print(f"Final recording demo already ready: http://127.0.0.1:{port}", flush=True)
        return 0
    _assert_available(port)
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print("Final recording demo did not start: PROVIDER_CREDENTIAL_UNAVAILABLE", file=sys.stderr)
        return 70

    owned = None
    app = None
    try:
        owned = start_owned_runtime()
        engine = DemoEngine(api_key=api_key, runner=owned.runner)
        app = create_app(
            engine=engine,
            port=port,
            migration_count=owned.migration_count,
            rls_table_count=owned.rls_table_count,
        )
        print(f"Final recording demo ready: http://127.0.0.1:{port}", flush=True)
        print("Press Ctrl+C to stop the owned local runtime.", flush=True)
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=port,
            workers=1,
            proxy_headers=False,
            access_log=False,
            log_level="warning",
        )
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as error:
        reason = str(error)
        if not reason or len(reason) > 100 or any(character.isspace() for character in reason):
            reason = type(error).__name__.upper()
        print(f"Final recording demo did not start: {reason}", file=sys.stderr)
        return 70
    finally:
        if app is not None:
            app.state.run_store.close()
        if owned is not None:
            cleanup = owned.close()
            if not cleanup.get("already_closed") and (
                not cleanup.get("pid_exited")
                or not cleanup.get("ports_closed")
                or not cleanup.get("temporary_store_removed")
                or cleanup.get("panic_detected")
                or cleanup.get("force_kill_used")
            ):
                print("Owned local CockroachDB cleanup needs inspection.", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
