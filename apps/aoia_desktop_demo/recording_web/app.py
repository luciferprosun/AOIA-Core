"""Loopback-only FastAPI shell for the final recording demo."""

from __future__ import annotations

import json
import re
import secrets
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .runtime import DEFAULT_MODEL_ID, DemoEngine, DemoRuntimeError, OBSERVER_ROLES


STATIC_ROOT = Path(__file__).resolve().parent / "static"
MAXIMUM_REQUEST_BYTES = 32 * 1024
RUN_ID_PATTERN = re.compile(r"run-[0-9a-f]{32}\Z")


@dataclass(slots=True)
class _Run:
    run_id: str
    prompt: str
    model_id: str
    critical_loop: bool
    german_law: bool
    observer_models: tuple[str, ...]
    state: str = "QUEUED"
    stage: str = "queued"
    status_text: str = "Waiting for the bounded local worker."
    observers: list[dict[str, object]] = field(default_factory=list)
    result: dict[str, object] | None = None
    error_code: str | None = None

    def projection(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "state": self.state,
            "stage": self.stage,
            "status_text": self.status_text,
            "model_id": self.model_id,
            "critical_loop": self.critical_loop,
            "german_law": self.german_law,
            "observers": list(self.observers),
            "result": self.result,
            "error_code": self.error_code,
        }


class _RunStore:
    def __init__(self, engine: DemoEngine) -> None:
        self._engine = engine
        self._runs: dict[str, _Run] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="aioa-final-recording")

    def submit(
        self,
        *,
        prompt: str,
        model_id: str,
        critical_loop: bool,
        german_law: bool,
        observer_models: tuple[str, ...],
    ) -> dict[str, object]:
        run = _Run(
            run_id="run-" + uuid4().hex,
            prompt=prompt,
            model_id=model_id,
            critical_loop=critical_loop,
            german_law=german_law,
            observer_models=observer_models,
        )
        with self._lock:
            if any(value.state in {"QUEUED", "RUNNING"} for value in self._runs.values()):
                raise DemoRuntimeError("RUN_ALREADY_ACTIVE")
            self._runs[run.run_id] = run
            while len(self._runs) > 12:
                oldest = next(iter(self._runs))
                if self._runs[oldest].state in {"QUEUED", "RUNNING"}:
                    break
                self._runs.pop(oldest)
        self._executor.submit(self._work, run.run_id)
        return run.projection()

    def get(self, run_id: str) -> dict[str, object] | None:
        if RUN_ID_PATTERN.fullmatch(run_id) is None:
            return None
        with self._lock:
            value = self._runs.get(run_id)
            return value.projection() if value is not None else None

    def has_active(self) -> bool:
        with self._lock:
            return any(value.state in {"QUEUED", "RUNNING"} for value in self._runs.values())

    def close(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=False)

    def _work(self, run_id: str) -> None:
        self._update(run_id, state="RUNNING", stage="starting", status_text="Starting the selected flow.")

        def progress(stage: str, text: str, observers) -> None:
            changes: dict[str, Any] = {"stage": stage, "status_text": text}
            if observers is not None:
                changes["observers"] = [dict(value) for value in observers]
            self._update(run_id, **changes)

        with self._lock:
            run = self._runs[run_id]
            request = {
                "prompt": run.prompt,
                "model_id": run.model_id,
                "critical_loop": run.critical_loop,
                "german_law": run.german_law,
                "observer_models": run.observer_models,
            }
        try:
            result = self._engine.execute(run_id=run_id, progress=progress, **request)
        except DemoRuntimeError as error:
            self._update(
                run_id,
                state="FAILED",
                stage="failed",
                status_text="The selected flow stopped safely.",
                error_code=str(error),
            )
            return
        except Exception:
            self._update(
                run_id,
                state="FAILED",
                stage="failed",
                status_text="The local runtime stopped safely.",
                error_code="LOCAL_RUNTIME_FAILURE",
            )
            return
        self._update(
            run_id,
            state="COMPLETED",
            stage="completed",
            status_text="Response delivered.",
            result=result,
            observers=list(result.get("observers", [])),
        )

    def _update(self, run_id: str, **changes: Any) -> None:
        with self._lock:
            run = self._runs[run_id]
            for name, value in changes.items():
                setattr(run, name, value)


def create_app(
    *,
    engine: DemoEngine,
    port: int,
    migration_count: int,
    rls_table_count: int,
) -> FastAPI:
    if not isinstance(engine, DemoEngine):
        raise TypeError("DemoEngine is required")
    app = FastAPI(
        title="AIOA Memory Patch Final Recording Demo",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    store = _RunStore(engine)
    session_id = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    allowed_origin = f"http://127.0.0.1:{port}"

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
            "base-uri 'none'; form-action 'self'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    def require_session(request: Request) -> None:
        if not secrets.compare_digest(
            request.cookies.get("aioa_recording_session", ""), session_id
        ):
            raise HTTPException(status_code=401, detail="LOCAL_SESSION_REQUIRED")

    def require_write(request: Request) -> None:
        require_session(request)
        if request.headers.get("origin") != allowed_origin:
            raise HTTPException(status_code=403, detail="LOCAL_ORIGIN_REQUIRED")
        if not secrets.compare_digest(request.headers.get("x-aioa-csrf", ""), csrf_token):
            raise HTTPException(status_code=403, detail="CSRF_VALIDATION_FAILED")

    @app.get("/")
    async def index() -> FileResponse:
        response = FileResponse(STATIC_ROOT / "index.html", media_type="text/html")
        response.set_cookie(
            "aioa_recording_session",
            session_id,
            httponly=True,
            secure=False,
            samesite="strict",
            path="/",
        )
        return response

    @app.get("/health")
    async def health() -> dict[str, object]:
        return {
            "status": "READY",
            "mode": "AIOA_FINAL_RECORDING_DEMO",
            "cockroachdb": "CONNECTED",
            "migration_count": migration_count,
            "rls_table_count": rls_table_count,
        }

    @app.get("/api/status")
    async def status(request: Request) -> dict[str, object]:
        require_session(request)
        return {
            "csrf_token": csrf_token,
            "default_model_id": DEFAULT_MODEL_ID,
            "models": engine.available_models,
            "observer_roles": OBSERVER_ROLES,
            "demo_prompt": engine.demo_prompt,
            "cockroachdb": "CONNECTED",
            "accounting": engine.accounting(),
        }

    @app.post("/api/runs")
    async def create_run(request: Request) -> JSONResponse:
        require_write(request)
        raw = await request.body()
        if len(raw) > MAXIMUM_REQUEST_BYTES:
            raise HTTPException(status_code=413, detail="REQUEST_TOO_LARGE")
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise HTTPException(status_code=400, detail="REQUEST_INVALID") from None
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="REQUEST_INVALID")
        prompt = payload.get("prompt")
        model_id = payload.get("model_id")
        critical_loop = payload.get("critical_loop")
        german_law = payload.get("german_law")
        observer_models = payload.get("observer_models", [])
        if (
            not isinstance(prompt, str)
            or not isinstance(model_id, str)
            or not isinstance(critical_loop, bool)
            or not isinstance(german_law, bool)
            or not isinstance(observer_models, list)
            or any(not isinstance(value, str) for value in observer_models)
        ):
            raise HTTPException(status_code=400, detail="REQUEST_INVALID")
        if critical_loop and german_law:
            raise HTTPException(
                status_code=409,
                detail="COMPOSITION_UNAVAILABLE_RECORDING_BUILD",
            )
        try:
            projection = store.submit(
                prompt=prompt,
                model_id=model_id,
                critical_loop=critical_loop,
                german_law=german_law,
                observer_models=tuple(observer_models),
            )
        except DemoRuntimeError as error:
            raise HTTPException(status_code=409, detail=str(error)) from None
        return JSONResponse(projection, status_code=202)

    @app.get("/api/runs/{run_id}")
    async def get_run(run_id: str, request: Request) -> dict[str, object]:
        require_session(request)
        projection = store.get(run_id)
        if projection is None:
            raise HTTPException(status_code=404, detail="RUN_NOT_FOUND")
        return projection

    @app.post("/api/reset")
    async def reset(request: Request) -> dict[str, object]:
        require_write(request)
        if store.has_active():
            raise HTTPException(status_code=409, detail="RUN_ALREADY_ACTIVE")
        engine.clear_conversation()
        return {"status": "CLEARED"}

    app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")
    app.state.run_store = store
    return app


__all__ = ["create_app"]
