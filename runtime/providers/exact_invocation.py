"""Exact, single-call provider facade for manually confirmed Orchestra stages.

This module never selects a fallback model and never retries.  It consumes a
process-local live-stage authorization before reading current connection
metadata or credentials, then delegates the one exact request to the existing
provider gateway and adapter implementation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Callable

from runtime.epistemic_orchestra.canonical import (
    canonical_sha256,
    exact_text_sha256,
    require_sha256,
)
from runtime.epistemic_orchestra.live_session import (
    LiveStageInvocationBinding,
    consume_live_stage_authorization,
)
from runtime.epistemic_orchestra.contracts import NON_AUTHORITATIVE
from runtime.providers.redaction import redact_provider_text
from runtime.providers.user_connections import (
    ProviderConnection,
    UserProviderStore,
    UserProviderStoreError,
)


UNTRUSTED = "UNTRUSTED"
CONNECTION_TEST_ACTION = "TEST_PROVIDER_CONNECTION_ONCE"
MAXIMUM_EXACT_RESPONSE_CHARACTERS = 100_000
MAXIMUM_CONNECTION_TEST_PREVIEW_CHARACTERS = 240
CONNECTION_TEST_PROMPT = "Reply with exactly AOIA_CONNECTION_OK."
CONNECTION_TEST_MAXIMUM_OUTPUT_TOKENS = 16
CONNECTION_TEST_TIMEOUT_SECONDS = 10


class ExactInvocationError(RuntimeError):
    """Bounded, redacted exact-invocation failure."""


@dataclass(frozen=True, slots=True)
class ExactInvocationResult:
    connection_id: str
    model_profile_id: str
    remote_model_id: str
    binding_hash: str
    response_text: str
    response_hash: str
    latency_ms: int
    trust_status: str = UNTRUSTED
    authority_status: str = NON_AUTHORITATIVE
    authoritative: bool = False
    can_approve: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_satisfy_gate: bool = False
    automatic_fallback_used: bool = False
    automatic_retry_used: bool = False

    def __post_init__(self) -> None:
        require_sha256("binding_hash", self.binding_hash)
        if not isinstance(self.response_text, str) or not self.response_text.strip():
            raise ExactInvocationError("provider response text is missing")
        if len(self.response_text) > MAXIMUM_EXACT_RESPONSE_CHARACTERS:
            raise ExactInvocationError("provider response exceeds the bounded result size")
        if self.response_hash != exact_text_sha256(self.response_text):
            raise ExactInvocationError("provider response hash differs")
        if self.trust_status != UNTRUSTED:
            raise ExactInvocationError("provider output must remain UNTRUSTED")
        if self.authority_status != NON_AUTHORITATIVE:
            raise ExactInvocationError("provider output must remain NON_AUTHORITATIVE")
        for name in (
            "authoritative",
            "can_approve",
            "can_write",
            "can_execute",
            "can_satisfy_gate",
            "automatic_fallback_used",
            "automatic_retry_used",
        ):
            if type(getattr(self, name)) is not bool or getattr(self, name):
                raise ExactInvocationError("provider result contains authority or routing escalation")
        if isinstance(self.latency_ms, bool) or not isinstance(self.latency_ms, int) or self.latency_ms < 0:
            raise ExactInvocationError("provider latency is malformed")


@dataclass(frozen=True, slots=True)
class ConnectionTestAuthorization:
    action: str
    connection_id: str
    connection_revision_hash: str
    model_profile_id: str
    model_revision_hash: str
    issued_at_epoch: int
    expires_at_epoch: int
    authorization_hash: str
    _service: "ExactProviderInvoker" = field(repr=False, compare=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action,
            "connection_id": self.connection_id,
            "connection_revision_hash": self.connection_revision_hash,
            "model_profile_id": self.model_profile_id,
            "model_revision_hash": self.model_revision_hash,
            "issued_at_epoch": self.issued_at_epoch,
            "expires_at_epoch": self.expires_at_epoch,
            "authorization_hash": self.authorization_hash,
            "serializable_authority": False,
        }


@dataclass(frozen=True, slots=True)
class ConnectionTestResult:
    success: bool
    connection_id: str
    model_profile_id: str
    remote_model_id: str
    latency_ms: int | None
    response_preview: str
    tested_at_epoch: int
    trust_status: str = UNTRUSTED
    authority_status: str = NON_AUTHORITATIVE
    authoritative: bool = False
    can_approve: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_satisfy_gate: bool = False

    def __post_init__(self) -> None:
        if type(self.success) is not bool:
            raise ExactInvocationError("connection-test success must be boolean")
        if self.latency_ms is not None and (
            isinstance(self.latency_ms, bool)
            or not isinstance(self.latency_ms, int)
            or self.latency_ms < 0
        ):
            raise ExactInvocationError("connection-test latency is malformed")
        if len(self.response_preview) > MAXIMUM_CONNECTION_TEST_PREVIEW_CHARACTERS:
            raise ExactInvocationError("connection-test preview exceeds its bound")
        if self.trust_status != UNTRUSTED:
            raise ExactInvocationError("connection-test output must remain UNTRUSTED")
        if self.authority_status != NON_AUTHORITATIVE:
            raise ExactInvocationError(
                "connection-test output must remain NON_AUTHORITATIVE"
            )
        for name in ("authoritative", "can_approve", "can_write", "can_execute", "can_satisfy_gate"):
            if type(getattr(self, name)) is not bool or getattr(self, name):
                raise ExactInvocationError("connection-test result contains an authority claim")

    def to_dict(self) -> dict[str, object]:
        return {
            "success": self.success,
            "connection_id": self.connection_id,
            "model_profile_id": self.model_profile_id,
            "remote_model_id": self.remote_model_id,
            "latency_ms": self.latency_ms,
            "response_preview": self.response_preview,
            "tested_at_epoch": self.tested_at_epoch,
            "trust_status": UNTRUSTED,
            "authority_status": NON_AUTHORITATIVE,
            "authoritative": False,
            "can_approve": False,
            "can_write": False,
            "can_execute": False,
            "can_satisfy_gate": False,
        }


@dataclass(frozen=True, slots=True)
class _GatewayTransportMaterial:
    purpose: str
    connection_id: str
    connection_revision_hash: str
    model_profile_id: str
    model_revision_hash: str
    remote_model_id: str
    api_style: str
    base_url: str
    native_adapter_id: str
    credential_reference: str
    prompt_hash: str
    max_tokens: int
    timeout_seconds: int

    def to_dict(self) -> dict[str, object]:
        return {
            "purpose": self.purpose,
            "connection_id": self.connection_id,
            "connection_revision_hash": self.connection_revision_hash,
            "model_profile_id": self.model_profile_id,
            "model_revision_hash": self.model_revision_hash,
            "remote_model_id": self.remote_model_id,
            "api_style": self.api_style,
            "base_url": self.base_url,
            "native_adapter_id": self.native_adapter_id,
            "credential_reference": self.credential_reference,
            "prompt_hash": self.prompt_hash,
            "max_tokens": self.max_tokens,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class GatewayTransportAuthorization:
    material: _GatewayTransportMaterial
    transport_hash: str
    _registry: "_TransportUseRegistry" = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class GatewayTransportReceipt:
    material: _GatewayTransportMaterial
    transport_hash: str
    receipt_hash: str
    _registry: "_TransportUseRegistry" = field(repr=False, compare=False)


class _TransportUseRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._issued: dict[int, GatewayTransportAuthorization] = {}
        self._authorization_receipts: dict[
            int, tuple[GatewayTransportAuthorization, GatewayTransportReceipt]
        ] = {}
        self._receipts: dict[int, GatewayTransportReceipt] = {}
        self._consumed_receipts: dict[int, GatewayTransportReceipt] = {}

    def issue(self, material: _GatewayTransportMaterial) -> GatewayTransportAuthorization:
        transport_hash = canonical_sha256(
            {"domain": "orchestra-exact-provider-transport-1a", **material.to_dict()}
        )
        authorization = GatewayTransportAuthorization(
            material=material,
            transport_hash=transport_hash,
            _registry=self,
        )
        with self._lock:
            self._issued[id(authorization)] = authorization
        return authorization

    def consume_authorization(
        self,
        authorization: GatewayTransportAuthorization,
        expected: _GatewayTransportMaterial,
    ) -> GatewayTransportReceipt:
        if authorization.material != expected:
            raise ExactInvocationError("gateway transport inputs differ from exact authorization")
        identity = id(authorization)
        with self._lock:
            if self._issued.get(identity) is not authorization:
                raise ExactInvocationError("gateway transport authorization is foreign or consumed")
            self._issued.pop(identity)
            receipt = GatewayTransportReceipt(
                material=expected,
                transport_hash=authorization.transport_hash,
                receipt_hash=canonical_sha256(
                    {
                        "domain": "orchestra-exact-provider-transport-receipt-1a",
                        "transport_hash": authorization.transport_hash,
                    }
                ),
                _registry=self,
            )
            self._receipts[id(receipt)] = receipt
            self._authorization_receipts[identity] = (authorization, receipt)
            return receipt

    def consume_receipt(
        self,
        receipt: GatewayTransportReceipt,
        expected: _GatewayTransportMaterial,
    ) -> None:
        if receipt.material != expected:
            raise ExactInvocationError("gateway receipt inputs differ from exact authorization")
        identity = id(receipt)
        with self._lock:
            if self._receipts.get(identity) is not receipt:
                raise ExactInvocationError("gateway transport receipt is foreign or consumed")
            self._receipts.pop(identity)
            self._consumed_receipts[identity] = receipt

    def require_fully_consumed(self, receipt: GatewayTransportReceipt) -> None:
        with self._lock:
            if self._consumed_receipts.get(id(receipt)) is not receipt:
                raise ExactInvocationError("provider adapter did not consume the exact transport receipt")

    def require_authorization_fully_consumed(
        self,
        authorization: GatewayTransportAuthorization,
    ) -> None:
        with self._lock:
            issued = self._authorization_receipts.get(id(authorization))
            if issued is None or issued[0] is not authorization:
                raise ExactInvocationError(
                    "provider gateway did not consume the exact transport authorization"
                )
            receipt = issued[1]
            if self._consumed_receipts.get(id(receipt)) is not receipt:
                raise ExactInvocationError(
                    "provider gateway did not consume the exact transport authorization"
                )
            # The complete exact capability chain has been checked.  Release its
            # strong references without retaining a reusable hash-only success bit.
            self._authorization_receipts.pop(id(authorization))
            self._consumed_receipts.pop(id(receipt))

    def retire_authorization(self, authorization: GatewayTransportAuthorization) -> None:
        """Release an exact transport chain that failed before full verification."""

        identity = id(authorization)
        with self._lock:
            self._issued.pop(identity, None)
            issued = self._authorization_receipts.pop(identity, None)
            if issued is not None:
                receipt = issued[1]
                self._receipts.pop(id(receipt), None)
                self._consumed_receipts.pop(id(receipt), None)


def _transport_material(
    *,
    purpose: str,
    connection_id: str,
    connection_revision_hash: str,
    model_profile_id: str,
    model_revision_hash: str,
    remote_model_id: str,
    api_style: str,
    base_url: str | None,
    native_adapter_id: str | None,
    credential_reference: str,
    prompt: str,
    max_tokens: int,
    timeout_seconds: int,
) -> _GatewayTransportMaterial:
    return _GatewayTransportMaterial(
        purpose=purpose,
        connection_id=connection_id,
        connection_revision_hash=connection_revision_hash,
        model_profile_id=model_profile_id,
        model_revision_hash=model_revision_hash,
        remote_model_id=remote_model_id,
        api_style=api_style,
        base_url=base_url or "",
        native_adapter_id=native_adapter_id or "",
        credential_reference=credential_reference,
        prompt_hash=exact_text_sha256(prompt),
        max_tokens=max_tokens,
        timeout_seconds=timeout_seconds,
    )


def consume_gateway_transport_authorization(
    authorization: object,
    **kwargs: object,
) -> GatewayTransportReceipt:
    if not isinstance(authorization, GatewayTransportAuthorization):
        raise ExactInvocationError("gateway transport authorization is required")
    expected = _transport_material(**kwargs)  # type: ignore[arg-type]
    return authorization._registry.consume_authorization(authorization, expected)


def consume_gateway_transport_receipt(
    receipt: object,
    **kwargs: object,
) -> None:
    if not isinstance(receipt, GatewayTransportReceipt):
        raise ExactInvocationError("gateway transport receipt is required")
    expected = _transport_material(**kwargs)  # type: ignore[arg-type]
    receipt._registry.consume_receipt(receipt, expected)


class ExactProviderInvoker:
    """One-store exact invoker with no fallback and no retry behavior."""

    def __init__(
        self,
        store: UserProviderStore,
        *,
        gateway_call: Callable[..., object] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if not isinstance(store, UserProviderStore):
            raise TypeError("store must be a UserProviderStore")
        if gateway_call is None:
            from runtime.providers.gateway import run_exact_provider_request_once

            gateway_call = run_exact_provider_request_once
        self.store = store
        self._gateway_call = gateway_call
        self._monotonic = monotonic
        self._transport_registry = _TransportUseRegistry()
        self._lock = Lock()
        self._issued_connection_tests: dict[int, ConnectionTestAuthorization] = {}

    def invoke_exact(
        self,
        *,
        stage_authorization: object,
        binding: LiveStageInvocationBinding,
        prompt: str,
        max_tokens: int,
        timeout_seconds: int,
    ) -> ExactInvocationResult:
        consume_live_stage_authorization(
            stage_authorization,
            binding=binding,
            provider_prompt=prompt,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )
        connection, profile = self._current_exact_target(
            binding.connection_id,
            binding.model_profile_id,
        )
        if (
            connection.connection_revision_hash != binding.connection_revision_hash
            or profile.model_revision_hash != binding.model_revision_hash
            or profile.remote_model_id != binding.remote_model_id
            or binding.operator_role not in profile.allowed_roles
        ):
            raise ExactInvocationError("selected provider connection or model revision is stale")
        self._assert_payload_excludes_credentials(binding.to_dict())
        return self._call_once(
            purpose="orchestra_live_stage",
            connection=connection,
            model_profile_id=profile.model_profile_id,
            model_revision_hash=profile.model_revision_hash,
            remote_model_id=profile.remote_model_id,
            prompt=prompt,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            binding_hash=binding.binding_hash,
        )

    def authorize_connection_test(
        self,
        *,
        connection_id: str,
        model_profile_id: str,
        explicit_operator_action: bool,
        issued_at_epoch: int,
        expires_at_epoch: int,
    ) -> ConnectionTestAuthorization:
        if explicit_operator_action is not True:
            raise ExactInvocationError("explicit operator connection-test action is required")
        if (
            isinstance(issued_at_epoch, bool)
            or not isinstance(issued_at_epoch, int)
            or isinstance(expires_at_epoch, bool)
            or not isinstance(expires_at_epoch, int)
            or issued_at_epoch <= 0
            or expires_at_epoch < issued_at_epoch
            or expires_at_epoch - issued_at_epoch > 300
        ):
            raise ExactInvocationError("connection-test evidence lifetime is invalid")
        connection, profile = self._current_exact_target(connection_id, model_profile_id)
        material = {
            "domain": "orchestra-connection-test-authorization-1a",
            "action": CONNECTION_TEST_ACTION,
            "connection_id": connection.connection_id,
            "connection_revision_hash": connection.connection_revision_hash,
            "model_profile_id": profile.model_profile_id,
            "model_revision_hash": profile.model_revision_hash,
            "issued_at_epoch": issued_at_epoch,
            "expires_at_epoch": expires_at_epoch,
        }
        authorization = ConnectionTestAuthorization(
            action=CONNECTION_TEST_ACTION,
            connection_id=connection.connection_id,
            connection_revision_hash=connection.connection_revision_hash,
            model_profile_id=profile.model_profile_id,
            model_revision_hash=profile.model_revision_hash,
            issued_at_epoch=issued_at_epoch,
            expires_at_epoch=expires_at_epoch,
            authorization_hash=canonical_sha256(material),
            _service=self,
        )
        with self._lock:
            self._issued_connection_tests[id(authorization)] = authorization
        return authorization

    def test_connection(
        self,
        authorization: ConnectionTestAuthorization,
        *,
        current_epoch: int,
    ) -> ConnectionTestResult:
        if not isinstance(authorization, ConnectionTestAuthorization) or authorization._service is not self:
            raise ExactInvocationError("connection-test authorization is required")
        identity = id(authorization)
        with self._lock:
            if self._issued_connection_tests.get(identity) is not authorization:
                raise ExactInvocationError("connection-test authorization is foreign or consumed")
            self._issued_connection_tests.pop(identity)
        if (
            isinstance(current_epoch, bool)
            or not isinstance(current_epoch, int)
            or current_epoch < authorization.issued_at_epoch
            or current_epoch > authorization.expires_at_epoch
        ):
            raise ExactInvocationError("connection-test authorization is stale or expired")
        remote_model_id = ""
        try:
            connection, profile = self._current_exact_target(
                authorization.connection_id,
                authorization.model_profile_id,
            )
            remote_model_id = profile.remote_model_id
            if (
                connection.connection_revision_hash != authorization.connection_revision_hash
                or profile.model_revision_hash != authorization.model_revision_hash
            ):
                raise ExactInvocationError("connection-test target revision is stale")
            result = self._call_once(
                purpose="connection_test",
                connection=connection,
                model_profile_id=profile.model_profile_id,
                model_revision_hash=profile.model_revision_hash,
                remote_model_id=profile.remote_model_id,
                prompt=CONNECTION_TEST_PROMPT,
                max_tokens=CONNECTION_TEST_MAXIMUM_OUTPUT_TOKENS,
                timeout_seconds=CONNECTION_TEST_TIMEOUT_SECONDS,
                binding_hash=authorization.authorization_hash,
            )
            test_result = ConnectionTestResult(
                success=True,
                connection_id=connection.connection_id,
                model_profile_id=profile.model_profile_id,
                remote_model_id=profile.remote_model_id,
                latency_ms=result.latency_ms,
                response_preview=result.response_text[:MAXIMUM_CONNECTION_TEST_PREVIEW_CHARACTERS],
                tested_at_epoch=current_epoch,
            )
            self._assert_payload_excludes_credentials(test_result.to_dict())
            return test_result
        except (ExactInvocationError, UserProviderStoreError, OSError, ValueError, RuntimeError):
            test_result = ConnectionTestResult(
                success=False,
                connection_id=authorization.connection_id,
                model_profile_id=authorization.model_profile_id,
                remote_model_id=remote_model_id,
                latency_ms=None,
                response_preview="",
                tested_at_epoch=current_epoch,
            )
            self._assert_payload_excludes_credentials(test_result.to_dict())
            return test_result

    def _current_exact_target(self, connection_id: str, model_profile_id: str):
        connection = self.store.get_connection(connection_id)
        profile = self.store.get_model_profile(model_profile_id)
        if not connection.enabled:
            raise ExactInvocationError("disabled connection cannot be invoked")
        if not profile.enabled:
            raise ExactInvocationError("disabled model profile cannot be invoked")
        if profile.connection_id != connection.connection_id:
            raise ExactInvocationError("model profile belongs to another connection")
        return connection, profile

    def _call_once(
        self,
        *,
        purpose: str,
        connection: ProviderConnection,
        model_profile_id: str,
        model_revision_hash: str,
        remote_model_id: str,
        prompt: str,
        max_tokens: int,
        timeout_seconds: int,
        binding_hash: str,
    ) -> ExactInvocationResult:
        try:
            api_key = self.store.read_credential(connection.credential_reference)
        except UserProviderStoreError as error:
            raise ExactInvocationError("configured provider credential is unavailable") from error
        try:
            self.store.assert_text_excludes_configured_credentials(prompt)
        except UserProviderStoreError as error:
            raise ExactInvocationError(str(error)) from None
        if api_key in prompt:
            raise ExactInvocationError(
                "provider prompt contains configured credential material"
            )
        material = _transport_material(
            purpose=purpose,
            connection_id=connection.connection_id,
            connection_revision_hash=connection.connection_revision_hash,
            model_profile_id=model_profile_id,
            model_revision_hash=model_revision_hash,
            remote_model_id=remote_model_id,
            api_style=connection.api_style,
            base_url=connection.base_url,
            native_adapter_id=connection.native_adapter_id,
            credential_reference=connection.credential_reference,
            prompt=prompt,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )
        self._assert_payload_excludes_credentials(material.to_dict())
        transport_authorization = self._transport_registry.issue(material)
        started = self._monotonic()
        try:
            gateway_result = self._gateway_call(
                purpose=purpose,
                connection_id=connection.connection_id,
                connection_revision_hash=connection.connection_revision_hash,
                model_profile_id=model_profile_id,
                model_revision_hash=model_revision_hash,
                api_style=connection.api_style,
                native_adapter_id=connection.native_adapter_id,
                base_url=connection.base_url or "",
                credential_reference=connection.credential_reference,
                remote_model_id=remote_model_id,
                api_key=api_key,
                prompt=prompt,
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
                transport_authorization=transport_authorization,
            )
        except Exception as error:
            self._transport_registry.retire_authorization(transport_authorization)
            try:
                # Redact the captured credential first. A concurrent config or
                # permission failure must not interrupt sanitization and expose
                # the provider-controlled exception through implicit context.
                safe = redact_provider_text(error, known_secrets=(api_key,))
            except Exception:
                safe = "redacted provider failure"
            try:
                safe = self.store.redact_configured_credentials(safe)
            except Exception:
                safe = redact_provider_text(safe, known_secrets=(api_key,))
            safe = safe[:300]
            # Do not chain a provider-controlled exception: traceback/log formatters
            # would otherwise reveal the unsanitized cause even when this message is
            # redacted.
            raise ExactInvocationError(f"exact provider call failed: {safe}") from None
        latency_ms = max(0, int((self._monotonic() - started) * 1000))
        try:
            self._transport_registry.require_authorization_fully_consumed(
                transport_authorization
            )
        except ExactInvocationError:
            self._transport_registry.retire_authorization(transport_authorization)
            raise
        for name, expected in (
            ("connection_id", connection.connection_id),
            ("model_profile_id", model_profile_id),
            ("remote_model_id", remote_model_id),
            ("trust_status", UNTRUSTED),
            ("authority_status", NON_AUTHORITATIVE),
            ("authoritative", False),
            ("can_approve", False),
            ("can_write", False),
            ("can_execute", False),
            ("can_satisfy_gate", False),
        ):
            actual = getattr(gateway_result, name, None)
            if type(expected) is bool:
                differs = type(actual) is not bool or actual is not expected
            else:
                differs = actual != expected
            if differs:
                raise ExactInvocationError(f"exact gateway result {name} differs")
        response_text = getattr(gateway_result, "response_text", None)
        if not isinstance(response_text, str) or not response_text.strip():
            raise ExactInvocationError("exact gateway response is malformed")
        response_text = self.store.redact_configured_credentials(response_text)
        result = ExactInvocationResult(
            connection_id=connection.connection_id,
            model_profile_id=model_profile_id,
            remote_model_id=remote_model_id,
            binding_hash=binding_hash,
            response_text=response_text,
            response_hash=exact_text_sha256(response_text),
            latency_ms=latency_ms,
        )
        self._assert_payload_excludes_credentials(
            {
                "connection_id": result.connection_id,
                "model_profile_id": result.model_profile_id,
                "remote_model_id": result.remote_model_id,
                "binding_hash": result.binding_hash,
                "response_text": result.response_text,
                "response_hash": result.response_hash,
                "latency_ms": result.latency_ms,
                "trust_status": result.trust_status,
                "authority_status": result.authority_status,
                "authoritative": result.authoritative,
                "can_approve": result.can_approve,
                "can_write": result.can_write,
                "can_execute": result.can_execute,
                "can_satisfy_gate": result.can_satisfy_gate,
                "automatic_fallback_used": result.automatic_fallback_used,
                "automatic_retry_used": result.automatic_retry_used,
            }
        )
        return result

    def _assert_payload_excludes_credentials(self, value: object) -> None:
        try:
            self.store.assert_payload_excludes_configured_credentials(value)
        except UserProviderStoreError as error:
            raise ExactInvocationError(str(error)) from None


__all__ = [
    "CONNECTION_TEST_ACTION",
    "CONNECTION_TEST_MAXIMUM_OUTPUT_TOKENS",
    "CONNECTION_TEST_PROMPT",
    "CONNECTION_TEST_TIMEOUT_SECONDS",
    "ConnectionTestAuthorization",
    "ConnectionTestResult",
    "ExactInvocationError",
    "ExactInvocationResult",
    "ExactProviderInvoker",
    "GatewayTransportAuthorization",
    "GatewayTransportReceipt",
    "consume_gateway_transport_authorization",
    "consume_gateway_transport_receipt",
]
