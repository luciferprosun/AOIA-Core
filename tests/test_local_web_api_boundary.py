from __future__ import annotations

import json
import http.client
import threading
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from email.message import Message
from http import HTTPStatus
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch

from runtime import webapp


SYNTHETIC_OPERATOR_TOKEN = "NZ_P012_SYNTHETIC_OPERATOR_TOKEN_001"
ALLOWED_ORIGIN = "http://127.0.0.1:4311"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _headers(*pairs: tuple[str, str]) -> Message:
    headers = Message()
    for name, value in pairs:
        headers[name] = value
    return headers


def _config(
    *,
    token: str = SYNTHETIC_OPERATOR_TOKEN,
    max_json_bytes: int = webapp.DEFAULT_MAX_JSON_BYTES,
    origins: frozenset[str] = frozenset({ALLOWED_ORIGIN}),
) -> webapp.WebBoundaryConfig:
    return webapp.WebBoundaryConfig(
        operator_token=token,
        allowed_origins=origins,
        max_json_bytes=max_json_bytes,
    )


class _ReadForbidden:
    def read(self, _length: int = -1) -> bytes:
        raise AssertionError("request body must not be read")


def _invoke(
    method: str,
    path: str,
    *,
    headers: Message | None = None,
    body: bytes = b"",
    stream=None,
    config: webapp.WebBoundaryConfig | None = None,
) -> list[tuple[HTTPStatus, dict[str, object]]]:
    writes: list[tuple[HTTPStatus, dict[str, object]]] = []
    handler = object.__new__(webapp.CodexStyleHandler)
    handler.path = path
    handler.headers = headers if headers is not None else Message()
    handler.rfile = stream if stream is not None else BytesIO(body)
    if config is not None:
        handler.web_boundary_config = config
    handler._write_json = lambda status, payload: writes.append((status, payload))
    getattr(webapp.CodexStyleHandler, f"do_{method}")(handler)
    return writes


def _json_headers(
    body: bytes,
    *,
    token: str | None = SYNTHETIC_OPERATOR_TOKEN,
    origin: str | None = None,
    content_type: str = "application/json",
    content_length: str | None = None,
) -> Message:
    pairs: list[tuple[str, str]] = []
    if token is not None:
        pairs.append(("Authorization", f"Bearer {token}"))
    if origin is not None:
        pairs.append(("Origin", origin))
    pairs.append(("Content-Type", content_type))
    pairs.append(("Content-Length", str(len(body)) if content_length is None else content_length))
    return _headers(*pairs)


def _loopback_request(
    port: int,
    method: str,
    path: str,
    *,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, object], dict[str, str]]:
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


class LocalWebApiBoundaryTests(unittest.TestCase):
    def assert_safe_error(
        self,
        writes: list[tuple[HTTPStatus, dict[str, object]]],
        expected_status: HTTPStatus,
        expected_reason: str,
    ) -> dict[str, object]:
        self.assertEqual(1, len(writes))
        status, payload = writes[0]
        self.assertEqual(expected_status, status)
        self.assertFalse(payload["ok"])
        self.assertEqual(expected_reason, payload["reason_code"])
        self.assertEqual(payload["message_safe"], payload["error"])
        self.assertRegex(str(payload["request_id"]), r"^request_[0-9a-f]{32}$")
        self.assertRegex(str(payload["trace_id"]), r"^trace_[0-9a-f]{32}$")
        self.assertEqual(expected_reason, payload["outcome"]["reason_code"])
        return payload

    def test_endpoint_policy_is_complete_and_restrictive(self) -> None:
        self.assertEqual({"/api/health"}, set(webapp.PUBLIC_HEALTH_PATHS))
        self.assertEqual(
            {
                "/api/status",
                "/api/models",
                "/api/model-catalog",
                "/api/memory-hats",
                "/api/provider-config-status",
                "/api/commits",
                "/api/operator/status",
                "/api/boundaries",
                "/api/router/status",
                "/api/evidence/sample",
                "/api/agent-loop/status",
                "/api/audit/status",
            },
            set(webapp.AUTHENTICATED_READ_PATHS),
        )
        self.assertEqual(
            {
                "/api/chat",
                "/api/operator/chat",
                "/api/router/preview",
                "/api/cpt/transform",
                "/api/model",
                "/api/model-selection/propose",
            },
            set(webapp.AUTHENTICATED_MUTATION_PATHS),
        )

    def test_public_health_is_the_only_api_that_needs_no_token(self) -> None:
        writes = _invoke("GET", "/api/health")

        self.assertEqual(HTTPStatus.OK, writes[0][0])
        self.assertTrue(writes[0][1]["ok"])
        self.assertEqual("SUCCESS", writes[0][1]["status"])
        self.assertNotIn("operator_token", json.dumps(writes[0][1]).casefold())

    def test_every_authenticated_get_rejects_missing_token(self) -> None:
        for path in webapp.AUTHENTICATED_READ_PATHS:
            with self.subTest(path=path):
                writes = _invoke("GET", path, config=_config())
                self.assert_safe_error(
                    writes,
                    HTTPStatus.UNAUTHORIZED,
                    "WEB_AUTHENTICATION_REQUIRED",
                )

    def test_every_mutation_rejects_missing_token_before_reading_body(self) -> None:
        for path in webapp.AUTHENTICATED_MUTATION_PATHS:
            with self.subTest(path=path):
                writes = _invoke(
                    "POST",
                    path,
                    headers=_headers(
                        ("Content-Type", "application/json"),
                        ("Content-Length", "999999999"),
                    ),
                    stream=_ReadForbidden(),
                    config=_config(),
                )
                self.assert_safe_error(
                    writes,
                    HTTPStatus.UNAUTHORIZED,
                    "WEB_AUTHENTICATION_REQUIRED",
                )

    def test_wrong_and_duplicate_authorization_are_rejected(self) -> None:
        wrong = _headers(("Authorization", "Bearer definitely-wrong"))
        duplicate = _headers(
            ("Authorization", f"Bearer {SYNTHETIC_OPERATOR_TOKEN}"),
            ("Authorization", f"Bearer {SYNTHETIC_OPERATOR_TOKEN}"),
        )
        for headers in (wrong, duplicate):
            with self.subTest(headers=headers.get_all("Authorization")):
                writes = _invoke("GET", "/api/memory-hats", headers=headers, config=_config())
                self.assert_safe_error(
                    writes,
                    HTTPStatus.UNAUTHORIZED,
                    "WEB_AUTHENTICATION_REQUIRED",
                )

    def test_query_token_is_rejected_and_never_authenticates(self) -> None:
        writes = _invoke(
            "GET",
            f"/api/status?token={SYNTHETIC_OPERATOR_TOKEN}",
            config=_config(),
        )

        payload = self.assert_safe_error(
            writes,
            HTTPStatus.BAD_REQUEST,
            "WEB_AUTH_QUERY_REJECTED",
        )
        self.assertNotIn(SYNTHETIC_OPERATOR_TOKEN, json.dumps(payload))

    def test_all_api_queries_are_rejected_but_static_cache_busters_remain_valid(self) -> None:
        sensitive_names = (
            "AOIA_WEB_OPERATOR_TOKEN",
            "bearer",
            "jwt",
            "password",
            "secret",
            "credential",
        )
        for name in sensitive_names:
            with self.subTest(name=name):
                writes = _invoke(
                    "GET",
                    f"/api/health?{name}={SYNTHETIC_OPERATOR_TOKEN}",
                    config=_config(),
                )
                payload = self.assert_safe_error(
                    writes,
                    HTTPStatus.BAD_REQUEST,
                    "WEB_AUTH_QUERY_REJECTED",
                )
                self.assertNotIn(SYNTHETIC_OPERATOR_TOKEN, json.dumps(payload))

        unsupported = _invoke("GET", "/api/health?view=compact", config=_config())
        self.assert_safe_error(
            unsupported,
            HTTPStatus.BAD_REQUEST,
            "WEB_QUERY_UNSUPPORTED",
        )

        handler = object.__new__(webapp.CodexStyleHandler)
        handler.headers = Message()
        writes: list[tuple[HTTPStatus, dict[str, object]]] = []
        handler._write_json = lambda status, payload: writes.append((status, payload))
        rejected = handler._reject_query(
            webapp.urlparse("/app.js?v=operator-console-1a"),
            False,
            webapp.TraceContext.new_request(),
        )
        self.assertFalse(rejected)
        self.assertEqual([], writes)

    def test_correct_synthetic_token_allows_local_json_mutation(self) -> None:
        body = json.dumps(
            {"prompt": "Review this local change.", "mode": "balanced_critic"}
        ).encode("utf-8")
        writes = _invoke(
            "POST",
            "/api/cpt/transform",
            headers=_json_headers(body),
            body=body,
            config=_config(),
        )

        self.assertEqual(HTTPStatus.OK, writes[0][0])
        self.assertTrue(writes[0][1]["ok"])
        self.assertRegex(str(writes[0][1]["request_id"]), r"^request_[0-9a-f]{32}$")
        self.assertRegex(str(writes[0][1]["trace_id"]), r"^trace_[0-9a-f]{32}$")

    def test_non_loopback_configuration_never_disables_authentication(self) -> None:
        environment = {
            webapp.WEB_OPERATOR_TOKEN_ENV: SYNTHETIC_OPERATOR_TOKEN,
            webapp.WEB_ALLOWED_ORIGINS_ENV: "http://operator.example:4311",
        }
        config = webapp.load_web_boundary_config(
            host="0.0.0.0",
            port=4311,
            environ=environment,
        )

        writes = _invoke("GET", "/api/status", config=config)
        self.assert_safe_error(
            writes,
            HTTPStatus.UNAUTHORIZED,
            "WEB_AUTHENTICATION_REQUIRED",
        )

    def test_missing_secret_and_nonloopback_origin_configuration_fail_closed(self) -> None:
        with self.assertRaises(webapp.WebBoundaryConfigurationError):
            webapp.load_web_boundary_config(environ={})
        with self.assertRaises(webapp.WebBoundaryConfigurationError):
            webapp.load_web_boundary_config(
                host="0.0.0.0",
                environ={webapp.WEB_OPERATOR_TOKEN_ENV: SYNTHETIC_OPERATOR_TOKEN},
            )

    def test_secret_is_hidden_from_config_repr(self) -> None:
        representation = repr(_config())
        self.assertNotIn(SYNTHETIC_OPERATOR_TOKEN, representation)
        self.assertNotIn("operator_token=", representation)

    def test_oversized_body_is_rejected_without_read(self) -> None:
        headers = _headers(
            ("Authorization", f"Bearer {SYNTHETIC_OPERATOR_TOKEN}"),
            ("Content-Type", "application/json"),
            ("Content-Length", "65"),
        )
        writes = _invoke(
            "POST",
            "/api/cpt/transform",
            headers=headers,
            stream=_ReadForbidden(),
            config=_config(max_json_bytes=64),
        )
        self.assert_safe_error(
            writes,
            HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            "WEB_REQUEST_TOO_LARGE",
        )

    def test_huge_numeric_content_length_is_safe_and_never_converted(self) -> None:
        headers = _headers(
            ("Authorization", f"Bearer {SYNTHETIC_OPERATOR_TOKEN}"),
            ("Content-Type", "application/json"),
            ("Content-Length", "9" * 5000),
        )
        writes = _invoke(
            "POST",
            "/api/cpt/transform",
            headers=headers,
            stream=_ReadForbidden(),
            config=_config(),
        )
        self.assert_safe_error(
            writes,
            HTTPStatus.BAD_REQUEST,
            "WEB_CONTENT_LENGTH_INVALID",
        )

    def test_missing_invalid_negative_and_duplicate_content_length_are_rejected(self) -> None:
        variants = (
            _headers(
                ("Authorization", f"Bearer {SYNTHETIC_OPERATOR_TOKEN}"),
                ("Content-Type", "application/json"),
            ),
            _headers(
                ("Authorization", f"Bearer {SYNTHETIC_OPERATOR_TOKEN}"),
                ("Content-Type", "application/json"),
                ("Content-Length", "nope"),
            ),
            _headers(
                ("Authorization", f"Bearer {SYNTHETIC_OPERATOR_TOKEN}"),
                ("Content-Type", "application/json"),
                ("Content-Length", "-1"),
            ),
            _headers(
                ("Authorization", f"Bearer {SYNTHETIC_OPERATOR_TOKEN}"),
                ("Content-Type", "application/json"),
                ("Content-Length", "2"),
                ("Content-Length", "2"),
            ),
        )
        expected = (
            (HTTPStatus.LENGTH_REQUIRED, "WEB_CONTENT_LENGTH_REQUIRED"),
            (HTTPStatus.BAD_REQUEST, "WEB_CONTENT_LENGTH_INVALID"),
            (HTTPStatus.BAD_REQUEST, "WEB_CONTENT_LENGTH_INVALID"),
            (HTTPStatus.BAD_REQUEST, "WEB_CONTENT_LENGTH_INVALID"),
        )
        for headers, (status, reason) in zip(variants, expected, strict=True):
            with self.subTest(values=headers.get_all("Content-Length")):
                writes = _invoke(
                    "POST",
                    "/api/cpt/transform",
                    headers=headers,
                    stream=_ReadForbidden(),
                    config=_config(),
                )
                self.assert_safe_error(writes, status, reason)

    def test_transfer_encoding_and_wrong_content_type_are_rejected_without_read(self) -> None:
        variants = (
            (
                _headers(
                    ("Authorization", f"Bearer {SYNTHETIC_OPERATOR_TOKEN}"),
                    ("Transfer-Encoding", "chunked"),
                    ("Content-Type", "application/json"),
                ),
                HTTPStatus.BAD_REQUEST,
                "WEB_TRANSFER_ENCODING_UNSUPPORTED",
            ),
            (
                _headers(
                    ("Authorization", f"Bearer {SYNTHETIC_OPERATOR_TOKEN}"),
                    ("Content-Type", "text/plain"),
                    ("Content-Length", "2"),
                ),
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "WEB_CONTENT_TYPE_UNSUPPORTED",
            ),
        )
        for headers, status, reason in variants:
            with self.subTest(reason=reason):
                writes = _invoke(
                    "POST",
                    "/api/cpt/transform",
                    headers=headers,
                    stream=_ReadForbidden(),
                    config=_config(),
                )
                self.assert_safe_error(writes, status, reason)

    def test_utf8_json_content_type_is_accepted_and_other_charset_rejected(self) -> None:
        body = b'{"prompt":"review"}'
        accepted = _invoke(
            "POST",
            "/api/cpt/transform",
            headers=_json_headers(body, content_type="application/json; charset=UTF-8"),
            body=body,
            config=_config(),
        )
        rejected = _invoke(
            "POST",
            "/api/cpt/transform",
            headers=_json_headers(body, content_type="application/json; charset=latin-1"),
            stream=_ReadForbidden(),
            config=_config(),
        )

        self.assertEqual(HTTPStatus.OK, accepted[0][0])
        self.assert_safe_error(
            rejected,
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            "WEB_CONTENT_TYPE_UNSUPPORTED",
        )

    def test_malformed_nonobject_duplicate_and_nonfinite_json_are_rejected(self) -> None:
        bodies = (
            b"\xff",
            b"{",
            b"[]",
            b"null",
            b'{"prompt":"one","prompt":"two"}',
            b'{"prompt":NaN}',
            ('{"nested":' + "[" * 1200 + "0" + "]" * 1200 + "}").encode("utf-8"),
        )
        for body in bodies:
            with self.subTest(body=body):
                writes = _invoke(
                    "POST",
                    "/api/cpt/transform",
                    headers=_json_headers(body),
                    body=body,
                    config=_config(),
                )
                self.assert_safe_error(
                    writes,
                    HTTPStatus.BAD_REQUEST,
                    "WEB_JSON_INVALID",
                )

    def test_real_loopback_server_enforces_boundary_without_token_leakage(self) -> None:
        server = webapp.AOIAWebServer(
            ("127.0.0.1", 0),
            webapp.CodexStyleHandler,
            boundary_config=_config(),
        )
        port = int(server.server_address[1])
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        captured_stdout = StringIO()
        captured_stderr = StringIO()
        responses: list[dict[str, object]] = []
        thread.start()
        try:
            with redirect_stdout(captured_stdout), redirect_stderr(captured_stderr):
                health_status, health, health_headers = _loopback_request(
                    port, "GET", "/api/health"
                )
                responses.append(health)
                missing_status, missing, _missing_headers = _loopback_request(
                    port, "GET", "/api/memory-hats"
                )
                responses.append(missing)
                wrong_status, wrong, _wrong_headers = _loopback_request(
                    port,
                    "GET",
                    "/api/memory-hats",
                    headers={"Authorization": "Bearer wrong-synthetic-value"},
                )
                responses.append(wrong)
                traversal_status, traversal, _traversal_headers = _loopback_request(
                    port, "GET", "/api/%2e%2e/index.html"
                )
                responses.append(traversal)
                allowed_status, allowed, allowed_headers = _loopback_request(
                    port,
                    "GET",
                    "/api/memory-hats",
                    headers={"Authorization": f"Bearer {SYNTHETIC_OPERATOR_TOKEN}"},
                )
                responses.append(allowed)
                request_body = b'{"prompt":"loopback review"}'
                post_status, posted, post_headers = _loopback_request(
                    port,
                    "POST",
                    "/api/cpt/transform",
                    body=request_body,
                    headers={
                        "Authorization": f"Bearer {SYNTHETIC_OPERATOR_TOKEN}",
                        "Content-Type": "application/json",
                        "Content-Length": str(len(request_body)),
                    },
                )
                responses.append(posted)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

        self.assertEqual(HTTPStatus.OK, health_status)
        self.assertEqual(HTTPStatus.UNAUTHORIZED, missing_status)
        self.assertEqual(HTTPStatus.UNAUTHORIZED, wrong_status)
        self.assertEqual(HTTPStatus.UNAUTHORIZED, traversal_status)
        self.assertEqual(HTTPStatus.OK, allowed_status)
        self.assertEqual(HTTPStatus.OK, post_status)
        self.assertTrue(allowed["ok"])
        self.assertTrue(posted["ok"])
        for headers in (health_headers, allowed_headers, post_headers):
            self.assertEqual("no-store", headers["cache-control"])
            self.assertEqual("nosniff", headers["x-content-type-options"])
        artifacts = (
            json.dumps(responses)
            + captured_stdout.getvalue()
            + captured_stderr.getvalue()
        )
        self.assertNotIn(SYNTHETIC_OPERATOR_TOKEN, artifacts)

    def test_real_loopback_mutations_are_serialized_for_single_operator(self) -> None:
        server = webapp.AOIAWebServer(
            ("127.0.0.1", 0),
            webapp.CodexStyleHandler,
            boundary_config=_config(),
        )
        port = int(server.server_address[1])
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        clients_ready = threading.Barrier(3)
        counter_lock = threading.Lock()
        active = 0
        peak = 0
        results: list[tuple[int, dict[str, object], dict[str, str]]] = []

        def delayed_transform(*, prompt: str, mode: str) -> dict[str, object]:
            nonlocal active, peak
            self.assertEqual("balanced_critic", mode)
            self.assertTrue(prompt)
            with counter_lock:
                active += 1
                peak = max(peak, active)
            try:
                time.sleep(0.08)
                return {"ok": True, "record": {"transformed_prompt": prompt}}
            finally:
                with counter_lock:
                    active -= 1

        def client() -> None:
            request_body = b'{"prompt":"serialized review"}'
            clients_ready.wait(timeout=3)
            result = _loopback_request(
                port,
                "POST",
                "/api/cpt/transform",
                body=request_body,
                headers={
                    "Authorization": f"Bearer {SYNTHETIC_OPERATOR_TOKEN}",
                    "Content-Type": "application/json",
                    "Content-Length": str(len(request_body)),
                },
            )
            results.append(result)

        client_threads = [threading.Thread(target=client) for _index in range(2)]
        server_thread.start()
        try:
            with patch.object(
                webapp,
                "build_cpt_transform_payload",
                side_effect=delayed_transform,
            ):
                for thread in client_threads:
                    thread.start()
                clients_ready.wait(timeout=3)
                for thread in client_threads:
                    thread.join(timeout=3)
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=3)

        self.assertTrue(all(not thread.is_alive() for thread in client_threads))
        self.assertEqual(2, len(results))
        self.assertEqual([HTTPStatus.OK, HTTPStatus.OK], sorted(item[0] for item in results))
        self.assertEqual(1, peak)

    def test_foreign_null_and_duplicate_origins_are_rejected_before_read(self) -> None:
        variants = (
            _headers(
                ("Authorization", f"Bearer {SYNTHETIC_OPERATOR_TOKEN}"),
                ("Origin", "https://evil.example"),
            ),
            _headers(
                ("Authorization", f"Bearer {SYNTHETIC_OPERATOR_TOKEN}"),
                ("Origin", "null"),
            ),
            _headers(
                ("Authorization", f"Bearer {SYNTHETIC_OPERATOR_TOKEN}"),
                ("Origin", ALLOWED_ORIGIN),
                ("Origin", ALLOWED_ORIGIN),
            ),
        )
        for headers in variants:
            with self.subTest(origin=headers.get_all("Origin")):
                writes = _invoke(
                    "POST",
                    "/api/cpt/transform",
                    headers=headers,
                    stream=_ReadForbidden(),
                    config=_config(),
                )
                self.assert_safe_error(
                    writes,
                    HTTPStatus.FORBIDDEN,
                    "WEB_ORIGIN_REJECTED",
                )

    def test_exact_allowed_origin_and_absent_cli_origin_are_allowed(self) -> None:
        body = b'{"prompt":"review"}'
        for origin in (ALLOWED_ORIGIN, None):
            with self.subTest(origin=origin):
                writes = _invoke(
                    "POST",
                    "/api/cpt/transform",
                    headers=_json_headers(body, origin=origin),
                    body=body,
                    config=_config(),
                )
                self.assertEqual(HTTPStatus.OK, writes[0][0])

    def test_internal_exception_returns_no_traceback_raw_text_path_or_token(self) -> None:
        sentinel = (
            f"internal {SYNTHETIC_OPERATOR_TOKEN} traceback "
            "/private/runtime/webapp.py"
        )
        headers = _headers(("Authorization", f"Bearer {SYNTHETIC_OPERATOR_TOKEN}"))
        with patch.object(webapp, "route_get_payload", side_effect=RuntimeError(sentinel)):
            writes = _invoke(
                "GET",
                "/api/status",
                headers=headers,
                config=_config(),
            )

        payload = self.assert_safe_error(
            writes,
            HTTPStatus.INTERNAL_SERVER_ERROR,
            "RUNTIME_ERROR",
        )
        serialized = json.dumps(payload)
        self.assertNotIn(SYNTHETIC_OPERATOR_TOKEN, serialized)
        self.assertNotIn("/private/runtime", serialized)
        self.assertNotIn(sentinel, serialized)
        self.assertNotIn("traceback", serialized.casefold())

    def test_http_error_with_outcome_discards_raw_error_text_data_and_identities(self) -> None:
        sentinel = f"{SYNTHETIC_OPERATOR_TOKEN} /private/provider.py traceback"
        source = webapp.NZOutcome.build(
            webapp.NZOutcomeStatus.FAILED,
            "MODEL_PROVIDER_ERROR",
            message_safe=sentinel,
            request_id="request_" + "1" * 32,
            trace_id="trace_" + "2" * 32,
            data={"error": sentinel},
            metadata={"path": sentinel},
        ).to_dict()
        body = b'{"provider_id":"kimi_chat","model_id":"synthetic","prompt":"review"}'
        routed = {
            "ok": False,
            "error": sentinel,
            "response_text": sentinel,
            "outcome": source,
        }
        with patch.object(
            webapp,
            "route_post_payload",
            return_value=(HTTPStatus.BAD_GATEWAY, routed),
        ):
            writes = _invoke(
                "POST",
                "/api/operator/chat",
                headers=_json_headers(body),
                body=body,
                config=_config(),
            )

        payload = self.assert_safe_error(
            writes,
            HTTPStatus.BAD_GATEWAY,
            "MODEL_PROVIDER_ERROR",
        )
        serialized = json.dumps(payload)
        self.assertNotIn(sentinel, serialized)
        self.assertNotIn("response_text", payload)
        self.assertNotIn("data", payload["outcome"])
        self.assertNotIn("metadata", payload["outcome"])
        self.assertNotEqual("request_" + "1" * 32, payload["request_id"])
        self.assertNotEqual("trace_" + "2" * 32, payload["trace_id"])

    def test_http_200_logical_failure_discards_transcript_and_maps_status(self) -> None:
        sentinel = f"traceback {SYNTHETIC_OPERATOR_TOKEN} /private/runtime.py"
        source = webapp.NZOutcome.build(
            webapp.NZOutcomeStatus.FAILED,
            "REQUEST_FAILED",
            message_safe=sentinel,
        ).to_dict()
        body = b'{"prompt":"review"}'
        with patch.object(
            webapp,
            "route_post_payload",
            return_value=(
                HTTPStatus.OK,
                {
                    "ok": False,
                    "transcript": sentinel,
                    "error": sentinel,
                    "outcome": source,
                },
            ),
        ):
            writes = _invoke(
                "POST",
                "/api/chat",
                headers=_json_headers(body),
                body=body,
                config=_config(),
            )

        payload = self.assert_safe_error(
            writes,
            HTTPStatus.BAD_GATEWAY,
            "REQUEST_FAILED",
        )
        self.assertNotIn(sentinel, json.dumps(payload))
        self.assertNotIn("transcript", payload)

    def test_get_and_all_non_success_outcomes_use_safe_shared_projection(self) -> None:
        cases = (
            (webapp.NZOutcomeStatus.PARTIAL, "STEP_BUDGET_EXHAUSTED", HTTPStatus.OK),
            (webapp.NZOutcomeStatus.DEGRADED, "BROWSER_FALLBACK_UNVERIFIED", HTTPStatus.OK),
            (webapp.NZOutcomeStatus.BLOCKED, "CAPABILITY_POLICY_DENIED", HTTPStatus.FORBIDDEN),
            (webapp.NZOutcomeStatus.CANCELLED, "HUMAN_APPROVAL_DECLINED", HTTPStatus.CONFLICT),
            (webapp.NZOutcomeStatus.FAILED, "REQUEST_FAILED", HTTPStatus.BAD_GATEWAY),
            (webapp.NZOutcomeStatus.TIMEOUT, "MODEL_TIMEOUT", HTTPStatus.GATEWAY_TIMEOUT),
            (webapp.NZOutcomeStatus.CONFLICT, "IDEMPOTENCY_CONFLICT", HTTPStatus.CONFLICT),
            (webapp.NZOutcomeStatus.UNKNOWN_OUTCOME, "UNKNOWN_OUTCOME", HTTPStatus.CONFLICT),
            (
                webapp.NZOutcomeStatus.MANUAL_REVIEW_REQUIRED,
                "MANUAL_REVIEW_REQUIRED",
                HTTPStatus.CONFLICT,
            ),
        )
        sentinel = f"{SYNTHETIC_OPERATOR_TOKEN} raw GET error"
        headers = _headers(("Authorization", f"Bearer {SYNTHETIC_OPERATOR_TOKEN}"))
        for outcome_status, reason, expected_http in cases:
            with self.subTest(status=outcome_status.value):
                outcome = webapp.NZOutcome.build(
                    outcome_status,
                    reason,
                    message_safe=sentinel,
                    data={"raw": sentinel},
                ).to_dict()
                with patch.object(
                    webapp,
                    "route_get_payload",
                    return_value=(
                        HTTPStatus.OK,
                        {"ok": False, "error": sentinel, "outcome": outcome},
                    ),
                ):
                    writes = _invoke(
                        "GET",
                        "/api/status",
                        headers=headers,
                        config=_config(),
                    )
                payload = self.assert_safe_error(writes, expected_http, reason)
                self.assertNotIn(sentinel, json.dumps(payload))

    def test_client_cannot_supply_http_correlation_identities(self) -> None:
        body = json.dumps(
            {
                "prompt": "review",
                "request_id": "request_" + "1" * 32,
                "trace_id": "trace_" + "2" * 32,
            }
        ).encode("utf-8")
        writes = _invoke(
            "POST",
            "/api/cpt/transform",
            headers=_json_headers(body),
            body=body,
            config=_config(),
        )

        payload = writes[0][1]
        self.assertNotEqual("request_" + "1" * 32, payload["request_id"])
        self.assertNotEqual("trace_" + "2" * 32, payload["trace_id"])

    def test_api_namespace_and_recovery_mutators_never_fall_through_static(self) -> None:
        auth = _headers(("Authorization", f"Bearer {SYNTHETIC_OPERATOR_TOKEN}"))
        for method, path in (
            ("GET", "/api"),
            ("GET", "/api/recovery/tasks"),
            ("POST", "/api/recovery/cancel"),
        ):
            with self.subTest(method=method, path=path):
                writes = _invoke(
                    method,
                    path,
                    headers=auth,
                    stream=_ReadForbidden(),
                    config=_config(),
                )
                self.assert_safe_error(
                    writes,
                    HTTPStatus.NOT_FOUND,
                    "WEB_ROUTE_NOT_FOUND",
                )

    def test_encoded_and_normalized_api_paths_cannot_bypass_auth_to_static(self) -> None:
        for path in (
            "/api%2Fstatus",
            "//api/status",
            "/public/%2e%2e/api/status",
            "/api/../index.html",
            "/api/%2e%2e/index.html",
        ):
            with self.subTest(path=path):
                writes = _invoke("GET", path, config=_config())
                self.assert_safe_error(
                    writes,
                    HTTPStatus.UNAUTHORIZED,
                    "WEB_AUTHENTICATION_REQUIRED",
                )

    def test_malformed_absolute_request_target_returns_safe_error(self) -> None:
        for method in ("GET", "POST"):
            with self.subTest(method=method):
                writes = _invoke(method, "http://[")
                self.assert_safe_error(
                    writes,
                    HTTPStatus.BAD_REQUEST,
                    "WEB_PATH_INVALID",
                )

    def test_frontend_keeps_operator_token_in_memory_and_header_only(self) -> None:
        app_source = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")
        index_source = (PROJECT_ROOT / "web" / "index.html").read_text(encoding="utf-8")
        combined = app_source + "\n" + index_source

        self.assertIn('id="operator-token"', index_source)
        self.assertIn('type="password"', index_source)
        self.assertIn('autocomplete="off"', index_source)
        self.assertIn("Authorization: `Bearer ${state.operatorToken}`", app_source)
        self.assertIn("operatorToken", app_source)
        self.assertNotIn("localStorage", combined)
        self.assertNotIn("sessionStorage", combined)
        self.assertNotIn("document.cookie", combined)
        self.assertNotIn("?token=", combined)
        self.assertNotIn(SYNTHETIC_OPERATOR_TOKEN, combined)


if __name__ == "__main__":
    unittest.main()
