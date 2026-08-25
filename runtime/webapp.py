#!/usr/bin/env python3
"""Local AOIA-Core web interface and JSON API."""

from __future__ import annotations

import argparse
import json
import os
import traceback
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

from evidence_review import ReviewInputError, bundled_scenario, review_candidate
from main import (
    DEBUG_RAW_RESPONSE,
    PROMPT_FILE,
    AgentRuntime,
    ProviderManager,
    load_prompt_template,
)


RUNTIME_DIR = Path(__file__).resolve().parent
REPOSITORY_DIR = RUNTIME_DIR.parent
WEB_DIR = REPOSITORY_DIR / "web"
HOST = os.getenv("AOIA_WEB_HOST", "127.0.0.1")
PORT = int(os.getenv("AOIA_WEB_PORT", "4311"))
MAX_REQUEST_BYTES = 24_000
LOOPBACK_HOSTS = {"127.0.0.1", "localhost"}


class WebRuntimeService:
    """Shared runtime adapter used by the local AOIA-Core UI."""

    def __init__(self) -> None:
        self.runtime = AgentRuntime(
            provider_manager=ProviderManager(RUNTIME_DIR),
            prompt_template=load_prompt_template(PROMPT_FILE),
            project_dir=RUNTIME_DIR,
            debug_raw=DEBUG_RAW_RESPONSE,
        )
        self.lock = Lock()

    def status_payload(self) -> dict:
        payload = self.runtime.snapshot_status()
        payload["available_models"] = self.runtime.provider_manager.available_models()
        payload["evidence_review"] = {
            "enabled": True,
            "provider_call": False,
            "authority": "METADATA_ONLY_NO_AUTHORITY",
        }
        return payload

    def switch_model(self, model_name: str) -> dict:
        with self.lock:
            selected = self.runtime.provider_manager.switch_model(model_name)
            return {
                "ok": True,
                "model": selected,
                "notice": self.runtime.provider_manager.model_notice(selected),
                "status": self.status_payload(),
            }

    def run_prompt(self, prompt: str) -> dict:
        with self.lock:
            result = self.runtime.run_text_request(prompt)
            return {
                "ok": True,
                "transcript": result["transcript"],
                "status": result["status"],
            }


_SERVICE: WebRuntimeService | None = None
_SERVICE_LOCK = Lock()


def get_service() -> WebRuntimeService:
    """Initialize the model runtime only when an endpoint needs it."""

    global _SERVICE
    if _SERVICE is None:
        with _SERVICE_LOCK:
            if _SERVICE is None:
                _SERVICE = WebRuntimeService()
    return _SERVICE


class AOIAWebHandler(SimpleHTTPRequestHandler):
    """Serve one static AOIA-Core UI and its bounded local APIs."""

    server_version = "AOIA-Core/1.0"

    def __init__(self, *args, service: WebRuntimeService | None = None, **kwargs):
        self.runtime_service = service
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def _service(self) -> WebRuntimeService:
        return self.runtime_service or get_service()

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        )
        super().end_headers()

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._write_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "system": "AOIA-Core",
                    "network": "local-only",
                    "evidence_review": "enabled",
                },
            )
            return
        if parsed.path == "/api/status":
            self._write_json(HTTPStatus.OK, self._service().status_payload())
            return
        if parsed.path == "/api/models":
            service = self._service()
            self._write_json(
                HTTPStatus.OK,
                {
                    "current_model": service.runtime.provider_manager.describe(),
                    "available_models": service.runtime.provider_manager.available_models(),
                },
            )
            return
        if parsed.path == "/api/review/scenario":
            self._write_json(HTTPStatus.OK, bundled_scenario())
            return
        if parsed.path in {"/", "/index.html"}:
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parsed = urlparse(self.path)
        payload = self._read_json_body()
        if payload is None:
            return

        try:
            if parsed.path == "/api/chat":
                prompt = str(payload.get("prompt", "")).strip()
                if not prompt:
                    self._write_json(
                        HTTPStatus.BAD_REQUEST,
                        {"ok": False, "error": "prompt is required"},
                    )
                    return
                self._write_json(HTTPStatus.OK, self._service().run_prompt(prompt))
                return

            if parsed.path == "/api/model":
                model_name = str(payload.get("model", "")).strip()
                if not model_name:
                    self._write_json(
                        HTTPStatus.BAD_REQUEST,
                        {"ok": False, "error": "model is required"},
                    )
                    return
                self._write_json(HTTPStatus.OK, self._service().switch_model(model_name))
                return

            if parsed.path == "/api/review":
                try:
                    result = review_candidate(payload.get("candidate_answer"))
                except ReviewInputError as error:
                    self._write_json(
                        HTTPStatus.BAD_REQUEST,
                        {"ok": False, "error": "invalid_request", "detail": str(error)},
                    )
                    return
                self._write_json(HTTPStatus.OK, result)
                return

            self._write_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
        except Exception as error:  # pragma: no cover - local debugging path
            if DEBUG_RAW_RESPONSE:
                traceback.print_exc()
            self._write_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": "internal_error", "detail": str(error)},
            )

    def log_message(self, format: str, *args: object) -> None:
        # Request bodies and candidate answers are never logged.
        return

    def _read_json_body(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError:
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": "invalid_content_length"},
            )
            return None
        if length <= 0 or length > MAX_REQUEST_BYTES:
            self._write_json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {"ok": False, "error": "request_size_out_of_bounds"},
            )
            return None
        raw_body = self.rfile.read(length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": "invalid_json_body"},
            )
            return None
        if not isinstance(payload, dict):
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": "request_body_must_be_an_object"},
            )
            return None
        return payload

    def _write_json(self, status: HTTPStatus, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def make_server(
    host: str = HOST,
    port: int = PORT,
    service: WebRuntimeService | None = None,
) -> ThreadingHTTPServer:
    """Create the single local AOIA-Core server."""

    if host not in LOOPBACK_HOSTS:
        raise ValueError("AOIA-Core web UI may bind only to a loopback interface")
    handler = partial(AOIAWebHandler, service=service)
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local AOIA-Core web interface.")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", default=PORT, type=int)
    return parser


def main() -> None:
    args = _parser().parse_args()
    server = make_server(args.host, args.port)
    address, bound_port = server.server_address[:2]
    print(f"AOIA-Core web UI running on http://{address}:{bound_port}")
    print("One local runtime | dated evidence review | human authority retained")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
