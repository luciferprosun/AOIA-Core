from __future__ import annotations

import http.client
import json
import socket
import sys
import threading
import time
import unittest
from dataclasses import replace
from http import HTTPStatus
from unittest.mock import patch

from runtime import webapp
from runtime.web_resource_governance import (
    BoundedExecutor,
    BoundedRateLimiter,
    ClientActivityLimiter,
    WebResourceLimits,
    client_key,
    load_web_resource_limits,
)


TOKEN = "NZ_P11_SYNTHETIC_OPERATOR_TOKEN_001"
ORIGIN = "http://127.0.0.1:4311"


def _limits(**changes) -> WebResourceLimits:
    base = WebResourceLimits(
        max_concurrent_requests=2,
        max_queued_requests=2,
        listen_backlog=4,
        max_client_requests=4,
        header_timeout_seconds=0.4,
        body_timeout_seconds=0.4,
        write_timeout_seconds=0.4,
        request_deadline_seconds=1.0,
        rate_window_seconds=1.0,
        health_rate_limit=20,
        read_rate_limit=20,
        mutation_rate_limit=20,
        rate_max_entries=16,
        rate_ttl_seconds=2.0,
    )
    return replace(base, **changes)


def _config(limits: WebResourceLimits) -> webapp.WebBoundaryConfig:
    return webapp.WebBoundaryConfig(
        operator_token=TOKEN,
        allowed_origins=frozenset({ORIGIN}),
        resource_limits=limits,
    )


def _start(limits: WebResourceLimits):
    server = webapp.AOIAWebServer(
        ("127.0.0.1", 0),
        webapp.CodexStyleHandler,
        boundary_config=_config(limits),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _stop(server, thread) -> None:
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def _request(port: int, method: str, path: str, *, body=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        raw = response.read()
        return (
            response.status,
            json.loads(raw.decode("utf-8")),
            {name.casefold(): value for name, value in response.getheaders()},
        )
    finally:
        connection.close()


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def _recv_all(client: socket.socket) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = client.recv(8192)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _raw_payload(response: bytes) -> tuple[bytes, dict[str, object]]:
    head, body = response.split(b"\r\n\r\n", 1)
    return head, json.loads(body.decode("utf-8"))


class _FakeSocket:
    def __init__(self) -> None:
        self.sent = b""
        self.closed = False

    def settimeout(self, _timeout: float) -> None:
        pass

    def sendall(self, payload: bytes) -> None:
        self.sent += payload

    def shutdown(self, _how: int) -> None:
        pass

    def close(self) -> None:
        self.closed = True


class WebGovernancePrimitiveTests(unittest.TestCase):
    def test_resource_config_is_strict_and_rotation_stays_restart_only(self) -> None:
        loaded = load_web_resource_limits({})
        self.assertEqual(WebResourceLimits(), loaded)
        self.assertEqual("restart_required", webapp.WEB_TOKEN_ROTATION_MODE)
        for name, value in (
            ("AOIA_WEB_MAX_CONCURRENT_REQUESTS", "0"),
            ("AOIA_WEB_MAX_QUEUED_REQUESTS", "-1"),
            ("AOIA_WEB_HEADER_TIMEOUT_SECONDS", "nan"),
            ("AOIA_WEB_RATE_MAX_ENTRIES", "999999"),
        ):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    load_web_resource_limits({name: value})

    def test_bounded_executor_retains_capacity_until_work_actually_finishes(self) -> None:
        entered = threading.Event()
        release = threading.Event()
        executor = BoundedExecutor(max_workers=1, max_queue=0, thread_name_prefix="p11-test")

        def blocked() -> str:
            entered.set()
            release.wait(timeout=2)
            return "done"

        first = executor.submit(blocked)
        self.assertIsNotNone(first)
        self.assertTrue(entered.wait(timeout=1))
        self.assertIsNone(executor.submit(lambda: "overflow"))
        release.set()
        self.assertEqual("done", first.result(timeout=1))  # type: ignore[union-attr]
        deadline = time.monotonic() + 1
        next_future = None
        while next_future is None and time.monotonic() < deadline:
            next_future = executor.submit(lambda: "next")
        self.assertIsNotNone(next_future)
        self.assertEqual("next", next_future.result(timeout=1))  # type: ignore[union-attr]
        executor.shutdown()

    def test_limiter_refill_expiry_rollback_and_memory_are_bounded(self) -> None:
        now = [10.0]
        limiter = BoundedRateLimiter(
            max_entries=2,
            ttl_seconds=2.0,
            clock=lambda: now[0],
        )
        self.assertTrue(limiter.allow("read", b"a", capacity=2, window_seconds=1.0))
        self.assertTrue(limiter.allow("read", b"a", capacity=2, window_seconds=1.0))
        self.assertFalse(limiter.allow("read", b"a", capacity=2, window_seconds=1.0))
        now[0] = 10.5
        self.assertTrue(limiter.allow("read", b"a", capacity=2, window_seconds=1.0))
        now[0] = 9.0
        self.assertFalse(limiter.allow("read", b"a", capacity=2, window_seconds=1.0))
        self.assertTrue(limiter.allow("read", b"b", capacity=1, window_seconds=1.0))
        self.assertFalse(limiter.allow("read", b"c", capacity=1, window_seconds=1.0))
        self.assertEqual(2, limiter.entry_count)
        now[0] = 13.0
        self.assertTrue(limiter.allow("read", b"c", capacity=1, window_seconds=1.0))
        self.assertLessEqual(limiter.entry_count, 2)

    def test_per_client_activity_uses_socket_host_not_port_or_headers(self) -> None:
        limiter = ClientActivityLimiter(max_clients=2, max_per_client=1)
        first = client_key(("127.0.0.1", 1))
        second_port = client_key(("127.0.0.1", 65535))
        self.assertEqual(first, second_port)
        self.assertTrue(limiter.acquire(first))
        self.assertFalse(limiter.acquire(second_port))
        limiter.release(first)
        self.assertTrue(limiter.acquire(second_port))
        limiter.release(second_port)

    def test_dispatch_gate_has_one_atomic_winner(self) -> None:
        for _index in range(100):
            gate = webapp._DispatchGate()
            barrier = threading.Barrier(3)
            results: list[tuple[str, bool]] = []

            def begin() -> None:
                barrier.wait(timeout=1)
                results.append(("begin", gate.begin(now=1.0, deadline=2.0)))

            def cancel() -> None:
                barrier.wait(timeout=1)
                results.append(("cancel", gate.cancel_if_pending()))

            threads = [threading.Thread(target=begin), threading.Thread(target=cancel)]
            for thread in threads:
                thread.start()
            barrier.wait(timeout=1)
            for thread in threads:
                thread.join(timeout=1)
            self.assertEqual(1, sum(value for _name, value in results))


class WebGovernanceServerTests(unittest.TestCase):
    def assert_safe(self, status, payload, headers, reason) -> None:
        self.assertEqual(reason, payload["reason_code"])
        self.assertFalse(payload["ok"])
        self.assertRegex(str(payload["request_id"]), r"^request_[0-9a-f]{32}$")
        self.assertRegex(str(payload["trace_id"]), r"^trace_[0-9a-f]{32}$")
        self.assertEqual("no-store", headers["cache-control"])
        self.assertEqual("nosniff", headers["x-content-type-options"])
        self.assertEqual("no-referrer", headers["referrer-policy"])
        self.assertEqual("close", headers["connection"])
        self.assertEqual(
            len(json.dumps(payload, ensure_ascii=False).encode("utf-8")),
            int(headers["content-length"]),
        )
        self.assertNotIn(TOKEN, json.dumps(payload))

    def test_backlog_is_installed_before_activation(self) -> None:
        observed: list[int] = []

        class ObservedServer(webapp.AOIAWebServer):
            def server_activate(self) -> None:
                observed.append(self.request_queue_size)
                super().server_activate()

        server = ObservedServer(
            ("127.0.0.1", 0),
            webapp.CodexStyleHandler,
            boundary_config=_config(_limits(listen_backlog=7)),
        )
        try:
            self.assertEqual([7], observed)
        finally:
            server.server_close()

    def test_submit_failure_releases_client_admission_and_closes_safely(self) -> None:
        limits = _limits(
            max_concurrent_requests=1,
            max_queued_requests=0,
            max_client_requests=1,
        )
        server = webapp.AOIAWebServer(
            ("127.0.0.1", 0),
            webapp.CodexStyleHandler,
            boundary_config=_config(limits),
        )
        request = _FakeSocket()
        address = ("127.0.0.1", 32123)
        try:
            with patch.object(
                server.request_executor,
                "submit",
                side_effect=RuntimeError("synthetic executor shutdown"),
            ):
                server.process_request(request, address)
            self.assertTrue(request.closed)
            self.assertIn(b"503 Service Unavailable", request.sent)
            key = client_key(address)
            self.assertTrue(server.client_activity.acquire(key))
            server.client_activity.release(key)
        finally:
            server.server_close()

    def test_concurrency_overflow_gets_safe_503_and_capacity_recovers(self) -> None:
        limits = _limits(
            max_concurrent_requests=1,
            max_queued_requests=0,
            max_client_requests=1,
        )
        server, server_thread = _start(limits)
        entered = threading.Event()
        release = threading.Event()
        first_result: list[tuple] = []

        def blocked_route(path: str):
            entered.set()
            release.wait(timeout=2)
            return HTTPStatus.OK, {"ok": True}

        first = threading.Thread(
            target=lambda: first_result.append(
                _request(server.server_address[1], "GET", "/api/status", headers=_auth_headers())
            )
        )
        try:
            with patch.object(webapp, "route_get_payload", side_effect=blocked_route):
                first.start()
                self.assertTrue(entered.wait(timeout=1))
                status, payload, headers = _request(
                    server.server_address[1], "GET", "/api/status", headers=_auth_headers()
                )
                self.assertEqual(HTTPStatus.SERVICE_UNAVAILABLE, status)
                self.assert_safe(status, payload, headers, "WEB_SERVER_BUSY")
                release.set()
                first.join(timeout=2)
            status, _payload, _headers = _request(
                server.server_address[1], "GET", "/api/health"
            )
            self.assertEqual(HTTPStatus.OK, status)
        finally:
            release.set()
            first.join(timeout=2)
            _stop(server, server_thread)

    def test_rate_limit_is_explicit_and_token_independent(self) -> None:
        server, server_thread = _start(_limits(read_rate_limit=1))
        try:
            first = _request(server.server_address[1], "GET", "/api/memory-hats", headers=_auth_headers())
            second = _request(server.server_address[1], "GET", "/api/memory-hats", headers=_auth_headers())
            self.assertEqual(HTTPStatus.OK, first[0])
            self.assertEqual(HTTPStatus.TOO_MANY_REQUESTS, second[0])
            self.assert_safe(*second, "WEB_RATE_LIMITED")
        finally:
            _stop(server, server_thread)

    def test_pre_auth_flood_is_limited_and_expiry_allows_valid_token(self) -> None:
        server, server_thread = _start(
            _limits(
                read_rate_limit=1,
                rate_window_seconds=0.1,
                rate_ttl_seconds=0.1,
            )
        )
        try:
            wrong = _request(
                server.server_address[1],
                "GET",
                "/api/memory-hats",
                headers={"Authorization": "Bearer wrong-synthetic-token"},
            )
            limited = _request(
                server.server_address[1],
                "GET",
                "/api/memory-hats",
                headers=_auth_headers(),
            )
            self.assertEqual(HTTPStatus.UNAUTHORIZED, wrong[0])
            self.assertEqual(HTTPStatus.TOO_MANY_REQUESTS, limited[0])
            self.assertEqual("WEB_RATE_LIMITED", limited[1]["reason_code"])
            time.sleep(0.14)
            allowed = _request(
                server.server_address[1],
                "GET",
                "/api/memory-hats",
                headers=_auth_headers(),
            )
            self.assertEqual(HTTPStatus.OK, allowed[0])
        finally:
            _stop(server, server_thread)

    def test_operation_timeout_exception_is_not_http_deadline(self) -> None:
        server, server_thread = _start(_limits(request_deadline_seconds=0.8))
        try:
            with patch.object(
                webapp,
                "route_get_payload",
                side_effect=TimeoutError("synthetic operation timeout"),
            ):
                status, payload, _headers = _request(
                    server.server_address[1],
                    "GET",
                    "/api/memory-hats",
                    headers=_auth_headers(),
                )
            self.assertEqual(HTTPStatus.INTERNAL_SERVER_ERROR, status)
            self.assertEqual("PROCESS_TIMEOUT", payload["reason_code"])
            self.assertNotIn("WEB_REQUEST_DEADLINE", json.dumps(payload))
        finally:
            _stop(server, server_thread)

    def test_queued_request_uses_acceptance_relative_deadline(self) -> None:
        limits = _limits(
            max_concurrent_requests=1,
            max_queued_requests=1,
            max_client_requests=2,
            request_deadline_seconds=0.22,
        )
        server, server_thread = _start(limits)
        first_entered = threading.Event()
        call_lock = threading.Lock()
        call_count = 0
        results: list[tuple[float, tuple]] = []

        def delayed(_path: str):
            nonlocal call_count
            with call_lock:
                call_count += 1
                current = call_count
            if current == 1:
                first_entered.set()
            time.sleep(0.16)
            return HTTPStatus.OK, {"ok": True}

        def client() -> None:
            started = time.monotonic()
            response = _request(
                server.server_address[1],
                "GET",
                "/api/memory-hats",
                headers=_auth_headers(),
            )
            results.append((time.monotonic() - started, response))

        threads = [threading.Thread(target=client), threading.Thread(target=client)]
        try:
            with patch.object(webapp, "route_get_payload", side_effect=delayed):
                threads[0].start()
                self.assertTrue(first_entered.wait(timeout=1))
                threads[1].start()
                for thread in threads:
                    thread.join(timeout=2)
            self.assertTrue(all(not thread.is_alive() for thread in threads))
            self.assertEqual(2, len(results))
            statuses = sorted(response[0] for _elapsed, response in results)
            self.assertEqual(
                [HTTPStatus.OK, HTTPStatus.GATEWAY_TIMEOUT],
                statuses,
            )
            self.assertLess(max(elapsed for elapsed, _response in results), 0.5)
        finally:
            _stop(server, server_thread)

    def test_slow_header_and_stalled_body_return_safe_408(self) -> None:
        server, server_thread = _start(
            _limits(header_timeout_seconds=0.12, body_timeout_seconds=0.12)
        )
        port = server.server_address[1]
        dispatch_calls: list[str] = []
        try:
            slow = socket.create_connection(("127.0.0.1", port), timeout=2)
            slow.sendall(b"GET /api/health HTTP/1.1\r\nHost: local\r\nX-Slow: ")
            slow_response = _recv_all(slow)
            slow.close()
            head, payload = _raw_payload(slow_response)
            self.assertIn(b" 408 ", head)
            self.assertEqual("WEB_HEADER_TIMEOUT", payload["reason_code"])

            body = socket.create_connection(("127.0.0.1", port), timeout=2)
            request = (
                f"POST /api/cpt/transform HTTP/1.1\r\nHost: local\r\n"
                f"Authorization: Bearer {TOKEN}\r\nContent-Type: application/json\r\n"
                "Content-Length: 40\r\n\r\n{}"
            ).encode("ascii")
            with patch.object(
                webapp,
                "build_cpt_transform_payload",
                side_effect=lambda **_kwargs: dispatch_calls.append("called"),
            ):
                body.sendall(request)
                body_response = _recv_all(body)
            body.close()
            head, payload = _raw_payload(body_response)
            self.assertIn(b" 408 ", head)
            self.assertEqual("WEB_BODY_TIMEOUT", payload["reason_code"])
            self.assertEqual([], dispatch_calls)
        finally:
            _stop(server, server_thread)

    def test_request_deadline_bounds_read_and_keeps_operation_permit(self) -> None:
        limits = _limits(
            max_concurrent_requests=1,
            max_queued_requests=0,
            max_client_requests=1,
            request_deadline_seconds=0.15,
        )
        server, server_thread = _start(limits)
        entered = threading.Event()
        release = threading.Event()

        def blocked(_path: str):
            entered.set()
            release.wait(timeout=2)
            return HTTPStatus.OK, {"ok": True}

        try:
            start = time.monotonic()
            with patch.object(webapp, "route_get_payload", side_effect=blocked):
                status, payload, headers = _request(
                    server.server_address[1], "GET", "/api/status", headers=_auth_headers()
                )
            elapsed = time.monotonic() - start
            self.assertTrue(entered.is_set())
            self.assertLess(elapsed, 0.6)
            self.assertEqual(HTTPStatus.GATEWAY_TIMEOUT, status)
            self.assert_safe(status, payload, headers, "WEB_REQUEST_DEADLINE_EXCEEDED")
            self.assertIsNone(server.submit_operation(lambda: "must remain bounded"))
        finally:
            release.set()
            _stop(server, server_thread)

    def test_finished_after_deadline_cannot_return_false_success(self) -> None:
        server, server_thread = _start(_limits(request_deadline_seconds=0.1))
        previous_interval = sys.getswitchinterval()

        def late_success(_path: str):
            deadline = time.monotonic() + 0.16
            while time.monotonic() < deadline:
                pass
            return HTTPStatus.OK, {"ok": True, "late": "success"}

        try:
            sys.setswitchinterval(0.5)
            with patch.object(webapp, "route_get_payload", side_effect=late_success):
                status, payload, headers = _request(
                    server.server_address[1],
                    "GET",
                    "/api/memory-hats",
                    headers=_auth_headers(),
                )
            self.assertEqual(HTTPStatus.GATEWAY_TIMEOUT, status)
            self.assert_safe(
                status,
                payload,
                headers,
                "WEB_REQUEST_DEADLINE_EXCEEDED",
            )
            self.assertNotIn("late", payload)
        finally:
            sys.setswitchinterval(previous_interval)
            _stop(server, server_thread)

    def test_health_and_static_success_have_no_expired_deadline_grace(self) -> None:
        class DelayedHandler(webapp.CodexStyleHandler):
            def do_GET(self) -> None:
                deadline = time.monotonic() + 0.16
                while time.monotonic() < deadline:
                    pass
                super().do_GET()

        limits = _limits(request_deadline_seconds=0.1)
        server = webapp.AOIAWebServer(
            ("127.0.0.1", 0),
            DelayedHandler,
            boundary_config=_config(limits),
        )
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        previous_interval = sys.getswitchinterval()
        try:
            sys.setswitchinterval(0.5)
            for path in ("/api/health", "/"):
                with self.subTest(path=path):
                    status, payload, _headers = _request(
                        server.server_address[1], "GET", path
                    )
                    self.assertEqual(HTTPStatus.GATEWAY_TIMEOUT, status)
                    self.assertEqual(
                        "WEB_REQUEST_DEADLINE_EXCEEDED",
                        payload["reason_code"],
                    )
        finally:
            sys.setswitchinterval(previous_interval)
            _stop(server, server_thread)

    def test_response_prepare_toctou_never_grants_normal_success_grace(self) -> None:
        limits = _limits(request_deadline_seconds=0.1)

        class SlowRedactor:
            def redact(self, payload):
                time.sleep(0.16)
                return payload

        server, server_thread = _start(limits)
        try:
            with patch.object(
                webapp.CodexStyleHandler,
                "_response_redactor",
                return_value=SlowRedactor(),
            ):
                status, payload, _headers = _request(
                    server.server_address[1], "GET", "/api/health"
                )
            self.assertEqual(HTTPStatus.GATEWAY_TIMEOUT, status)
            self.assertEqual("WEB_REQUEST_DEADLINE_EXCEEDED", payload["reason_code"])
        finally:
            _stop(server, server_thread)

        class SlowPrepareHandler(webapp.CodexStyleHandler):
            def _prepare_response_writer(self, config, *, allow_expired_grace):
                if not allow_expired_grace:
                    time.sleep(0.16)
                return super()._prepare_response_writer(
                    config,
                    allow_expired_grace=allow_expired_grace,
                )

        static_server = webapp.AOIAWebServer(
            ("127.0.0.1", 0),
            SlowPrepareHandler,
            boundary_config=_config(limits),
        )
        static_thread = threading.Thread(
            target=static_server.serve_forever,
            daemon=True,
        )
        static_thread.start()
        try:
            status, payload, _headers = _request(
                static_server.server_address[1], "GET", "/"
            )
            self.assertEqual(HTTPStatus.GATEWAY_TIMEOUT, status)
            self.assertEqual("WEB_REQUEST_DEADLINE_EXCEEDED", payload["reason_code"])
        finally:
            _stop(static_server, static_thread)

    def test_started_mutation_deadline_is_unknown_and_never_late_writes(self) -> None:
        limits = _limits(
            max_concurrent_requests=1,
            max_queued_requests=0,
            max_client_requests=1,
            request_deadline_seconds=0.15,
        )
        server, server_thread = _start(limits)
        entered = threading.Event()
        release = threading.Event()

        def blocked_transform(**_kwargs):
            entered.set()
            release.wait(timeout=2)
            return {"ok": True, "record": {"transformed_prompt": "late"}}

        request_body = b'{"prompt":"review"}'
        headers = {
            **_auth_headers(),
            "Content-Type": "application/json",
            "Content-Length": str(len(request_body)),
        }
        try:
            with patch.object(
                webapp,
                "build_cpt_transform_payload",
                side_effect=blocked_transform,
            ):
                status, payload, response_headers = _request(
                    server.server_address[1],
                    "POST",
                    "/api/cpt/transform",
                    body=request_body,
                    headers=headers,
                )
            self.assertTrue(entered.is_set())
            self.assertEqual(HTTPStatus.GATEWAY_TIMEOUT, status)
            self.assertEqual("UNKNOWN_OUTCOME", payload["status"])
            self.assert_safe(
                status,
                payload,
                response_headers,
                "WEB_REQUEST_DEADLINE_UNKNOWN",
            )
        finally:
            release.set()
            _stop(server, server_thread)

    def test_lock_wait_expires_without_late_mutation_dispatch(self) -> None:
        server, server_thread = _start(_limits(request_deadline_seconds=0.12))
        called: list[str] = []
        request_body = b'{"prompt":"review"}'
        headers = {
            **_auth_headers(),
            "Content-Type": "application/json",
            "Content-Length": str(len(request_body)),
        }
        server.operator_mutation_lock.acquire()
        try:
            with patch.object(
                webapp,
                "build_cpt_transform_payload",
                side_effect=lambda **_kwargs: called.append("called"),
            ):
                status, payload, response_headers = _request(
                    server.server_address[1],
                    "POST",
                    "/api/cpt/transform",
                    body=request_body,
                    headers=headers,
                )
            self.assertEqual(HTTPStatus.GATEWAY_TIMEOUT, status)
            self.assert_safe(
                status,
                payload,
                response_headers,
                "WEB_REQUEST_DEADLINE_EXCEEDED",
            )
            self.assertEqual([], called)
        finally:
            server.operator_mutation_lock.release()
            _stop(server, server_thread)


if __name__ == "__main__":
    unittest.main()
