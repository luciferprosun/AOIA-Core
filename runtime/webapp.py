#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import traceback
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

from model_catalog import get_static_model_catalog_payload
from main import (
    DEBUG_RAW_RESPONSE,
    PROMPT_FILE,
    AgentRuntime,
    ProviderManager,
    load_prompt_template,
)


PROJECT_DIR = Path(__file__).resolve().parent
WEB_DIR = PROJECT_DIR / "web"
if not WEB_DIR.exists():
    WEB_DIR = PROJECT_DIR.parent / "web"
HOST = os.getenv("APP2_WEB_HOST", "127.0.0.1")
PORT = int(os.getenv("APP2_WEB_PORT", "4311"))


class WebRuntimeService:
    """Shared runtime adapter used by the local web UI."""

    def __init__(self) -> None:
        self.runtime = AgentRuntime(
            provider_manager=ProviderManager(PROJECT_DIR),
            prompt_template=load_prompt_template(PROMPT_FILE),
            project_dir=PROJECT_DIR,
            debug_raw=DEBUG_RAW_RESPONSE,
        )
        self.lock = Lock()

    def status_payload(self) -> dict:
        payload = self.runtime.snapshot_status()
        payload["available_models"] = self.runtime.provider_manager.available_models()
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


SERVICE = WebRuntimeService()


class CodexStyleHandler(SimpleHTTPRequestHandler):
    """Serve the static UI and a small JSON API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self._write_json(HTTPStatus.OK, SERVICE.status_payload())
            return
        if parsed.path == "/api/models":
            self._write_json(
                HTTPStatus.OK,
                {
                    "current_model": SERVICE.runtime.provider_manager.describe(),
                    "available_models": SERVICE.runtime.provider_manager.available_models(),
                },
            )
            return
        if parsed.path == "/api/model-catalog":
            self._write_json(HTTPStatus.OK, get_static_model_catalog_payload())
            return
        if parsed.path in {"/", "/index.html"}:
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        payload = self._read_json_body()
        if payload is None:
            return

        try:
            if parsed.path == "/api/chat":
                prompt = str(payload.get("prompt", "")).strip()
                if not prompt:
                    self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "prompt is required"})
                    return
                self._write_json(HTTPStatus.OK, SERVICE.run_prompt(prompt))
                return

            if parsed.path == "/api/model":
                model_name = str(payload.get("model", "")).strip()
                if not model_name:
                    self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "model is required"})
                    return
                self._write_json(HTTPStatus.OK, SERVICE.switch_model(model_name))
                return

            self._write_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found"})
        except Exception as error:  # pragma: no cover - local debugging path
            self._write_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    "ok": False,
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                },
            )

    def log_message(self, format: str, *args) -> None:
        return

    def _read_json_body(self) -> dict | None:
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw_body = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "Invalid JSON body"})
            return None

    def _write_json(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), CodexStyleHandler)
    print(f"App222 web UI running on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
