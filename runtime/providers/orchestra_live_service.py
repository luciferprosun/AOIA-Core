"""Local web-service facade for user provider configuration and live Orchestra runs.

The service keeps live previews as strong process-local objects.  A client may
confirm only the three matching hashes returned by this service; it cannot send
back a reconstructed preview, role selection, run contract, or credential.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Callable, Mapping, Sequence

from runtime.epistemic_orchestra.canonical import EpistemicContractError
from runtime.epistemic_orchestra.contracts import EpistemicRunContract
from runtime.epistemic_orchestra.human_review_workspace import (
    OrchestraHumanReviewWorkspaceError,
    build_orchestra_human_review_workspace,
)
from runtime.epistemic_orchestra.live_run_preview import (
    OrchestraLiveRunPreview,
    build_live_run_confirmation_material,
    build_live_run_preview,
)
from runtime.epistemic_orchestra.live_session import (
    LiveSessionError,
    LiveStageExecutionError,
    LiveSessionUseRegistry,
    run_live_orchestra_session,
)
from runtime.epistemic_orchestra.role_binding import (
    OrchestraOperatorRole,
    OrchestraRoleSelection,
    build_model_role_assignment,
    build_orchestra_role_selection,
    validate_role_selection_against_current_profiles,
)
from runtime.epistemic_orchestra.session_view import (
    FAILED_STAGE_EVIDENCE_SCHEMA_VERSION,
    PROVIDER_TYPE_SNAPSHOT_SCHEMA_VERSION,
    SESSION_SNAPSHOT_SCHEMA_VERSION,
    OrchestraFailedStageEvidence,
    OrchestraProviderTypeSnapshot,
    OrchestraSessionNotFoundError,
    OrchestraSessionSnapshot,
    OrchestraSessionView,
    OrchestraSessionViewError,
    build_orchestra_session_view,
    validate_orchestra_session_id,
)
from runtime.providers.exact_invocation import ExactInvocationError, ExactProviderInvoker
from runtime.providers.model_profiles import ModelProfile, ModelProfileError
from runtime.providers.user_connections import (
    ProviderConnection,
    UserProviderStore,
    UserProviderStoreError,
)


DEFAULT_PREVIEW_LIFETIME_SECONDS = 300
DEFAULT_LIVE_TIMEOUT_SECONDS = 15
DEFAULT_LIVE_MAXIMUM_OUTPUT_TOKENS = 256
MAXIMUM_ISSUED_PREVIEWS = 32
MAXIMUM_RETAINED_SESSION_VIEWS = 64
ROLE_ORDER = {
    OrchestraOperatorRole.MAIN.value: 0,
    OrchestraOperatorRole.CRITIC.value: 1,
    OrchestraOperatorRole.AUDITOR.value: 2,
    OrchestraOperatorRole.SYNTHESIZER.value: 3,
}


class OrchestraLiveWebError(ValueError):
    """A bounded, secret-free configuration or live-session API error."""


@dataclass(frozen=True, slots=True)
class _IssuedPreview:
    source_prompt: str
    role_selection: OrchestraRoleSelection
    run: EpistemicRunContract
    preview: OrchestraLiveRunPreview


def _required_text(value: object, name: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise OrchestraLiveWebError(
            f"{name} must be non-blank text no longer than {maximum} characters"
        )
    return value


def _actual_bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise OrchestraLiveWebError(f"{name} must be boolean")
    return value


def _optional_bounded_int(
    value: object,
    name: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise OrchestraLiveWebError(f"{name} must be between {minimum} and {maximum}")
    return value


class OrchestraLiveWebService:
    """Serialized local configuration plus single-use live-preview coordination."""

    def __init__(
        self,
        project_root: Path,
        *,
        store: UserProviderStore | None = None,
        exact_invoker: ExactProviderInvoker | None = None,
        session_registry: LiveSessionUseRegistry | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.store = store if store is not None else UserProviderStore(self.project_root)
        self.exact_invoker = (
            exact_invoker if exact_invoker is not None else ExactProviderInvoker(self.store)
        )
        self.session_registry = (
            session_registry if session_registry is not None else LiveSessionUseRegistry()
        )
        self._clock = clock
        self._lock = RLock()
        self._run_counter = 0
        self._issued_previews: dict[str, _IssuedPreview] = {}
        self._session_snapshots: dict[str, OrchestraSessionSnapshot] = {}
        self._last_connection_tests: dict[str, dict[str, object]] = {}

    def list_connections(self) -> dict[str, object]:
        with self._lock:
            connections = tuple(self.store.list_connections())
            response = {
                "ok": True,
                "connections": [self._connection_payload(item) for item in connections],
                "secrets_included": False,
            }
            self._assert_payload_excludes_credentials(response)
            return response

    def create_connection(self, payload: Mapping[str, object]) -> dict[str, object]:
        allowed = {
            "connection_id",
            "display_name",
            "api_style",
            "base_url",
            "native_adapter_id",
            "api_key",
        }
        self._require_payload_fields(
            payload,
            required={"connection_id", "display_name", "api_style", "api_key"},
            allowed=allowed,
        )
        connection_id = _required_text(payload["connection_id"], "connection_id", maximum=128)
        api_style = _required_text(payload["api_style"], "api_style", maximum=64)
        api_key = _required_text(payload["api_key"], "api_key", maximum=16_384)
        base_url_raw = payload.get("base_url")
        base_url = base_url_raw if isinstance(base_url_raw, str) and base_url_raw.strip() else None
        native_adapter_raw = payload.get("native_adapter_id")
        native_adapter_id = (
            native_adapter_raw
            if isinstance(native_adapter_raw, str) and native_adapter_raw.strip()
            else None
        )
        with self._lock:
            try:
                connection = self.store.create_connection(
                    connection_id=connection_id,
                    display_name=_required_text(
                        payload["display_name"], "display_name", maximum=128
                    ),
                    api_style=api_style,
                    base_url=base_url,
                    native_adapter_id=native_adapter_id,
                    credential_reference=connection_id,
                    enabled=True,
                    created_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                    api_key=api_key,
                )
            except (ModelProfileError, UserProviderStoreError) as error:
                raise OrchestraLiveWebError(str(error)) from None
            response = {
                "ok": True,
                "connection": self._connection_payload(connection),
                "secrets_included": False,
            }
            self._assert_payload_excludes_credentials(response)
            return response

    def disable_connection(self, payload: Mapping[str, object]) -> dict[str, object]:
        self._require_payload_fields(
            payload,
            required={"connection_id"},
            allowed={"connection_id"},
        )
        with self._lock:
            try:
                connection = self.store.disable_connection(payload["connection_id"])
            except UserProviderStoreError as error:
                raise OrchestraLiveWebError(str(error)) from None
            self._invalidate_unconsumed_session_snapshots(
                current_epoch=self._now(),
                reason_code="CONNECTION_CONFIGURATION_DISABLED",
            )
            self._issued_previews.clear()
            response = {"ok": True, "connection": self._connection_payload(connection)}
            self._assert_payload_excludes_credentials(response)
            return response

    def list_model_profiles(self) -> dict[str, object]:
        with self._lock:
            response = {
                "ok": True,
                "model_profiles": [
                    self._model_profile_payload(item)
                    for item in self.store.list_model_profiles()
                ],
            }
            self._assert_payload_excludes_credentials(response)
            return response

    def create_model_profile(self, payload: Mapping[str, object]) -> dict[str, object]:
        allowed = {
            "model_profile_id",
            "connection_id",
            "display_name",
            "remote_model_id",
            "allowed_roles",
            "context_limit",
            "output_limit",
        }
        self._require_payload_fields(
            payload,
            required={
                "model_profile_id",
                "connection_id",
                "display_name",
                "remote_model_id",
                "allowed_roles",
            },
            allowed=allowed,
        )
        roles = payload["allowed_roles"]
        if isinstance(roles, str) or not isinstance(roles, Sequence):
            raise OrchestraLiveWebError("allowed_roles must be an array")
        with self._lock:
            try:
                profile = self.store.create_model_profile(
                    model_profile_id=payload["model_profile_id"],
                    connection_id=payload["connection_id"],
                    display_name=payload["display_name"],
                    remote_model_id=payload["remote_model_id"],
                    enabled=True,
                    allowed_roles=tuple(roles),
                    context_limit=payload.get("context_limit"),
                    output_limit=payload.get("output_limit"),
                )
            except (ModelProfileError, UserProviderStoreError) as error:
                raise OrchestraLiveWebError(str(error)) from None
            response = {
                "ok": True,
                "model_profile": self._model_profile_payload(profile),
            }
            self._assert_payload_excludes_credentials(response)
            return response

    def disable_model_profile(self, payload: Mapping[str, object]) -> dict[str, object]:
        self._require_payload_fields(
            payload,
            required={"model_profile_id"},
            allowed={"model_profile_id"},
        )
        with self._lock:
            try:
                profile = self.store.disable_model_profile(payload["model_profile_id"])
            except UserProviderStoreError as error:
                raise OrchestraLiveWebError(str(error)) from None
            self._invalidate_unconsumed_session_snapshots(
                current_epoch=self._now(),
                reason_code="MODEL_CONFIGURATION_DISABLED",
            )
            self._issued_previews.clear()
            response = {
                "ok": True,
                "model_profile": self._model_profile_payload(profile),
            }
            self._assert_payload_excludes_credentials(response)
            return response

    def list_orchestra_models(self) -> dict[str, object]:
        with self._lock:
            connections = {
                item.connection_id: item for item in self.store.list_connections()
            }
            rows: list[dict[str, object]] = []
            for profile in self.store.list_model_profiles():
                connection = connections.get(profile.connection_id)
                if connection is None:
                    continue
                status = self._credential_status(connection)
                rows.append(
                    {
                        **self._model_profile_payload(profile),
                        "connection_name": connection.display_name,
                        "connection_status": (
                            "disabled"
                            if not connection.enabled
                            else status
                        ),
                        "model_status": "enabled" if profile.enabled else "disabled",
                        "credential_status": status,
                        "last_connection_test": self._last_connection_tests.get(
                            profile.model_profile_id,
                            {"status": "not tested"},
                        ),
                        "selected": False,
                        "assigned_role": "",
                    }
                )
            response = {
                "ok": True,
                "models": rows,
                "supported_selection_count": {"minimum": 2, "maximum": 5},
                "supported_roles": list(ROLE_ORDER),
                "secrets_included": False,
            }
            self._assert_payload_excludes_credentials(response)
            return response

    def test_connection(self, payload: Mapping[str, object]) -> dict[str, object]:
        self._require_payload_fields(
            payload,
            required={
                "connection_id",
                "model_profile_id",
                "explicit_operator_action",
            },
            allowed={
                "connection_id",
                "model_profile_id",
                "explicit_operator_action",
            },
        )
        explicit = _actual_bool(
            payload["explicit_operator_action"], "explicit_operator_action"
        )
        now = self._now()
        with self._lock:
            try:
                authorization = self.exact_invoker.authorize_connection_test(
                    connection_id=payload["connection_id"],
                    model_profile_id=payload["model_profile_id"],
                    explicit_operator_action=explicit,
                    issued_at_epoch=now,
                    expires_at_epoch=now + 60,
                )
            except (ExactInvocationError, UserProviderStoreError) as error:
                raise OrchestraLiveWebError(str(error)) from None
        result = self.exact_invoker.test_connection(authorization, current_epoch=now)
        safe_result = result.to_dict()
        with self._lock:
            self._last_connection_tests[result.model_profile_id] = {
                "status": "success" if result.success else "failure",
                "tested_at": result.tested_at_epoch,
            }
        response = {"ok": result.success, **safe_result, "secrets_included": False}
        self._assert_payload_excludes_credentials(response)
        return response

    def create_preview(self, payload: Mapping[str, object]) -> dict[str, object]:
        allowed = {
            "source_prompt",
            "selections",
            "timeout_seconds",
            "maximum_output_tokens",
        }
        self._require_payload_fields(
            payload,
            required={"source_prompt", "selections"},
            allowed=allowed,
        )
        source_prompt = _required_text(
            payload["source_prompt"], "source_prompt", maximum=20_000
        )
        timeout_seconds = _optional_bounded_int(
            payload.get("timeout_seconds"),
            "timeout_seconds",
            default=DEFAULT_LIVE_TIMEOUT_SECONDS,
            minimum=1,
            maximum=30,
        )
        maximum_output_tokens = _optional_bounded_int(
            payload.get("maximum_output_tokens"),
            "maximum_output_tokens",
            default=DEFAULT_LIVE_MAXIMUM_OUTPUT_TOKENS,
            minimum=1,
            maximum=512,
        )
        selections = payload["selections"]
        if isinstance(selections, (str, bytes)) or not isinstance(selections, Sequence):
            raise OrchestraLiveWebError("selections must be an array")
        with self._lock:
            now = self._now()
            role_selection = self._build_role_selection(selections)
            try:
                self.store.assert_text_excludes_configured_credentials(
                    source_prompt,
                )
            except UserProviderStoreError as error:
                raise OrchestraLiveWebError(str(error)) from None
            self._run_counter += 1
            orchestra_run_id = f"orchestra-web-{now}-{self._run_counter}"
            try:
                run, preview = build_live_run_preview(
                    orchestra_run_id=orchestra_run_id,
                    source_prompt=source_prompt,
                    role_selection=role_selection,
                    timeout_seconds=timeout_seconds,
                    maximum_output_tokens=maximum_output_tokens,
                    expires_at_epoch=now + DEFAULT_PREVIEW_LIFETIME_SECONDS,
                )
            except EpistemicContractError as error:
                raise OrchestraLiveWebError(str(error)) from None
            self._purge_expired_previews(now)
            if len(self._issued_previews) >= MAXIMUM_ISSUED_PREVIEWS:
                raise OrchestraLiveWebError("too many unconsumed live run previews")
            response = {
                "ok": True,
                "preview": preview.to_dict(),
                "role_selection": role_selection.to_dict(),
                "run_contract": run.to_dict(),
                "confirmation_material": build_live_run_confirmation_material(preview),
                "provider_call_permitted": False,
                "human_action_required": True,
            }
            self._assert_payload_excludes_credentials(response)
            connections = {
                item.connection_id: item for item in self.store.list_connections()
            }
            provider_types = tuple(
                OrchestraProviderTypeSnapshot(
                    schema_version=PROVIDER_TYPE_SNAPSHOT_SCHEMA_VERSION,
                    connection_id=connection_id,
                    provider_type=connections[connection_id].api_style,
                )
                for connection_id in dict.fromkeys(
                    assignment.connection_id for assignment in role_selection.assignments
                )
            )
            self._retain_session_snapshot(
                OrchestraSessionSnapshot(
                    schema_version=SESSION_SNAPSHOT_SCHEMA_VERSION,
                    session_id=run.run_id,
                    session_state="NOT_EXECUTED",
                    created_at_epoch=now,
                    updated_at_epoch=now,
                    run=run,
                    preview=preview,
                    role_selection=role_selection,
                    provider_types=provider_types,
                    plan_available=True,
                    plan_consumed=False,
                    exact_human_confirmation_recorded=False,
                    confirmation_hash=None,
                ),
                current_epoch=now,
            )
            self._issued_previews[preview.preview_hash] = _IssuedPreview(
                source_prompt=source_prompt,
                role_selection=role_selection,
                run=run,
                preview=preview,
            )
            return response

    def run_preview(self, payload: Mapping[str, object]) -> dict[str, object]:
        required = {
            "preview_hash",
            "confirmation_hash",
            "confirmed_preview_hash",
            "explicit_run_action",
        }
        self._require_payload_fields(payload, required=required, allowed=required)
        explicit = _actual_bool(payload["explicit_run_action"], "explicit_run_action")
        if explicit is not True:
            raise OrchestraLiveWebError("explicit Run Orchestra action is required")
        hashes = (
            _required_text(payload["preview_hash"], "preview_hash", maximum=64),
            _required_text(payload["confirmation_hash"], "confirmation_hash", maximum=64),
            _required_text(
                payload["confirmed_preview_hash"],
                "confirmed_preview_hash",
                maximum=64,
            ),
        )
        now = self._now()
        with self._lock:
            issued = self._issued_previews.get(hashes[0])
            if issued is None:
                raise OrchestraLiveWebError("live run preview is missing, foreign, or consumed")
            if now > issued.preview.expires_at_epoch:
                self._issued_previews.pop(hashes[0], None)
                self._replace_session_snapshot(
                    issued.run.run_id,
                    session_state="EXPIRED",
                    updated_at_epoch=issued.preview.expires_at_epoch,
                    plan_available=False,
                    plan_consumed=False,
                    exact_human_confirmation_recorded=False,
                    confirmation_hash=None,
                )
                raise OrchestraLiveWebError("live run preview has expired")
            # Consume server-held state atomically before revalidation, confirmation,
            # or any live call.  A stale or otherwise rejected Run action must never
            # leave the old preview available for a later replay.
            self._issued_previews.pop(hashes[0], None)
            self._replace_session_snapshot(
                issued.run.run_id,
                session_state="FAILED",
                updated_at_epoch=now,
                plan_available=False,
                plan_consumed=True,
                exact_human_confirmation_recorded=False,
                confirmation_hash=None,
                session_error_code="RUN_ACTION_REJECTED",
            )
            if len(set(hashes)) != 1:
                raise OrchestraLiveWebError(
                    "all three confirmation hashes must match exactly"
                )
            self._validate_current_selection(issued.role_selection)
            try:
                # Credentials deliberately do not participate in revision hashes.
                # Re-check after any possible secret rotation so newly configured
                # key material can never enter a previously issued prompt/run hash.
                self.store.assert_text_excludes_configured_credentials(
                    issued.source_prompt,
                )
                self.store.assert_payload_excludes_configured_credentials(
                    {
                        "role_selection": issued.role_selection.to_dict(),
                        "run_contract": issued.run.to_dict(),
                        "preview": issued.preview.to_dict(),
                    }
                )
            except UserProviderStoreError as error:
                raise OrchestraLiveWebError(str(error)) from None
            try:
                confirmation = self.session_registry.issue_confirmation(
                    preview=issued.preview,
                    confirmed_preview_hash=hashes[2],
                    explicit_run_action=True,
                    issued_at_epoch=now,
                )
            except LiveSessionError as error:
                raise OrchestraLiveWebError(str(error)) from None
            self._replace_session_snapshot(
                issued.run.run_id,
                session_state="RUNNING",
                updated_at_epoch=now,
                plan_available=False,
                plan_consumed=True,
                exact_human_confirmation_recorded=True,
                confirmation_hash=confirmation.confirmation_hash,
                session_error_code=None,
            )
        try:
            result = run_live_orchestra_session(
                run=issued.run,
                preview=issued.preview,
                source_prompt=issued.source_prompt,
                role_selection=issued.role_selection,
                confirmation=confirmation,
                registry=self.session_registry,
                current_epoch=now,
                exact_invoker=self.exact_invoker.invoke_exact,
            )
        except LiveStageExecutionError as error:
            completed_results = tuple(error.completed_stage_results)
            completed_stages = tuple(error.completed_stage_chain)
            redaction_warning = False
            try:
                self._assert_payload_excludes_credentials(
                    {
                        "completed_stage_results": [
                            item.to_dict() for item in completed_results
                        ],
                        "completed_stage_chain": [
                            item.to_dict() for item in completed_stages
                        ],
                    }
                )
            except OrchestraLiveWebError:
                completed_results = ()
                completed_stages = ()
                redaction_warning = True
            failed_evidence = OrchestraFailedStageEvidence(
                schema_version=FAILED_STAGE_EVIDENCE_SCHEMA_VERSION,
                reason_code="ORCHESTRA_EXACT_STAGE_FAILED",
                stage_id=error.stage_id,
                call_index=error.call_index,
                operator_role=error.operator_role,
                connection_id=error.connection_id,
                model_profile_id=error.model_profile_id,
            )
            completed_at = self._now()
            with self._lock:
                self._replace_session_snapshot(
                    issued.run.run_id,
                    session_state=("PARTIAL" if completed_results else "FAILED"),
                    updated_at_epoch=completed_at,
                    completed_stage_results=completed_results,
                    completed_stage_chain=completed_stages,
                    failed_stage=failed_evidence,
                    session_error_code=(
                        "SESSION_OUTPUT_WITHHELD_BY_CREDENTIAL_BOUNDARY"
                        if redaction_warning
                        else None
                    ),
                    redaction_warning=redaction_warning,
                )
            response = {
                "ok": False,
                "failed_stage": error.to_dict(),
                "session_consumed": True,
                "trust_status": "UNTRUSTED",
                "authority_status": "NON_AUTHORITATIVE",
                "authoritative": False,
                "human_review_required": True,
                "automatic_fallback_used": False,
                "automatic_retry_used": False,
            }
            self._assert_payload_excludes_credentials(response)
            return response
        except (EpistemicContractError, ExactInvocationError, UserProviderStoreError) as error:
            self.session_registry.retire_confirmation(confirmation)
            with self._lock:
                self._replace_session_snapshot(
                    issued.run.run_id,
                    session_state="FAILED",
                    updated_at_epoch=self._now(),
                    completed_stage_results=(),
                    completed_stage_chain=(),
                    session_result=None,
                    failed_stage=None,
                    session_error_code="SESSION_EXECUTION_VALIDATION_FAILED",
                )
            raise OrchestraLiveWebError(str(error)) from None
        try:
            self._assert_payload_excludes_credentials(
                {
                    "stage_results": [item.to_dict() for item in result.stage_results],
                    "stage_chain": [item.to_dict() for item in result.stage_chain],
                    "session_result": result.to_dict(),
                }
            )
        except OrchestraLiveWebError:
            with self._lock:
                self._replace_session_snapshot(
                    issued.run.run_id,
                    session_state="FAILED",
                    updated_at_epoch=self._now(),
                    completed_stage_results=(),
                    completed_stage_chain=(),
                    session_result=None,
                    failed_stage=None,
                    session_error_code="SESSION_OUTPUT_WITHHELD_BY_CREDENTIAL_BOUNDARY",
                    redaction_warning=True,
                )
            raise
        with self._lock:
            self._replace_session_snapshot(
                issued.run.run_id,
                session_state="COMPLETED",
                updated_at_epoch=self._now(),
                completed_stage_results=tuple(result.stage_results),
                completed_stage_chain=tuple(result.stage_chain),
                session_result=result,
                failed_stage=None,
                session_error_code=None,
                redaction_warning=False,
            )
        response = {
            "ok": True,
            "session": result.to_dict(),
            "final_draft": result.final_draft,
            "trust_status": result.trust_status,
            "authority_status": result.authority_status,
            "authoritative": False,
            "human_review_required": True,
            "automatic_fallback_used": False,
            "automatic_retry_used": False,
        }
        self._assert_payload_excludes_credentials(response)
        return response

    def get_orchestra_session_view(self, session_id: object) -> dict[str, object]:
        """Return one inert view without consuming, refreshing, or mutating state."""

        view = self._build_orchestra_session_view_for_read(session_id)
        payload = view.to_dict()
        self._assert_payload_excludes_credentials(payload)
        return payload

    def get_orchestra_human_review_workspace(
        self,
        session_id: object,
    ) -> dict[str, object]:
        """Return a comparison projection without live or mutable capabilities."""

        view = self._build_orchestra_session_view_for_read(session_id)
        try:
            payload = build_orchestra_human_review_workspace(view).to_dict()
        except OrchestraHumanReviewWorkspaceError as error:
            raise OrchestraLiveWebError(str(error)) from None
        # The workspace is derived only from the already-sanitized view.  Do
        # not reload credential files merely to inspect this read response.
        return payload

    def _build_orchestra_session_view_for_read(
        self,
        session_id: object,
    ) -> OrchestraSessionView:
        """Build the sole sanitized source accepted by read-only projections."""

        try:
            normalized = validate_orchestra_session_id(session_id)
        except OrchestraSessionViewError as error:
            raise OrchestraLiveWebError(str(error)) from None
        with self._lock:
            snapshot = self._session_snapshots.get(normalized)
        if snapshot is None:
            raise OrchestraSessionNotFoundError("Orchestra session was not found")
        current_epoch = self._now()
        if (
            snapshot.session_state == "NOT_EXECUTED"
            and current_epoch > snapshot.preview.expires_at_epoch
        ):
            snapshot = replace(
                snapshot,
                session_state="EXPIRED",
                updated_at_epoch=snapshot.preview.expires_at_epoch,
                plan_available=False,
                plan_consumed=False,
                exact_human_confirmation_recorded=False,
                confirmation_hash=None,
            )
        try:
            return build_orchestra_session_view(snapshot)
        except OrchestraSessionViewError as error:
            raise OrchestraLiveWebError(str(error)) from None

    def _build_role_selection(
        self,
        selections: Sequence[object],
    ) -> OrchestraRoleSelection:
        normalized: list[tuple[int, int, str, str]] = []
        for input_index, item in enumerate(selections):
            if not isinstance(item, Mapping) or set(item) != {"model_profile_id", "role"}:
                raise OrchestraLiveWebError(
                    "each selection must contain only model_profile_id and role"
                )
            profile_id = _required_text(
                item["model_profile_id"], "model_profile_id", maximum=128
            )
            try:
                role = OrchestraOperatorRole(item["role"]).value
            except (TypeError, ValueError):
                raise OrchestraLiveWebError("selection contains an unsupported role") from None
            normalized.append((ROLE_ORDER[role], input_index, profile_id, role))
        normalized.sort(key=lambda value: (value[0], value[1]))
        connections = {
            item.connection_id: item for item in self.store.list_connections()
        }
        profiles = {
            item.model_profile_id: item for item in self.store.list_model_profiles()
        }
        assignments = []
        try:
            for ordinal, (_rank, _input_index, profile_id, role) in enumerate(normalized):
                profile = profiles.get(profile_id)
                if profile is None:
                    raise OrchestraLiveWebError("selected model profile is missing")
                connection = connections.get(profile.connection_id)
                if connection is None:
                    raise OrchestraLiveWebError("selected provider connection is missing")
                if self._credential_status(connection) != "configured":
                    raise OrchestraLiveWebError(
                        "selected provider connection credential is not configured"
                    )
                assignments.append(
                    build_model_role_assignment(
                        ordinal=ordinal,
                        connection=connection,
                        model_profile=profile,
                        role=role,
                    )
                )
            selection = build_orchestra_role_selection(assignments)
            validate_role_selection_against_current_profiles(
                selection,
                connections_by_id=connections,
                model_profiles_by_id=profiles,
            )
            return selection
        except EpistemicContractError as error:
            raise OrchestraLiveWebError(str(error)) from None

    def _validate_current_selection(self, selection: OrchestraRoleSelection) -> None:
        connections = {
            item.connection_id: item for item in self.store.list_connections()
        }
        profiles = {
            item.model_profile_id: item for item in self.store.list_model_profiles()
        }
        try:
            validate_role_selection_against_current_profiles(
                selection,
                connections_by_id=connections,
                model_profiles_by_id=profiles,
            )
        except EpistemicContractError as error:
            raise OrchestraLiveWebError(str(error)) from None
        for assignment in selection.assignments:
            connection = connections[assignment.connection_id]
            if self._credential_status(connection) != "configured":
                raise OrchestraLiveWebError(
                    "selected provider connection credential is not configured"
                )

    def _connection_payload(self, connection: ProviderConnection) -> dict[str, object]:
        return {
            "connection_id": connection.connection_id,
            "display_name": connection.display_name,
            "api_style": connection.api_style,
            "base_url": connection.base_url,
            "native_adapter_id": connection.native_adapter_id,
            "enabled": connection.enabled,
            "created_at": connection.created_at,
            "connection_revision_hash": connection.connection_revision_hash,
            "credential_status": self._credential_status(connection),
        }

    @staticmethod
    def _model_profile_payload(profile: ModelProfile) -> dict[str, object]:
        return {
            "model_profile_id": profile.model_profile_id,
            "connection_id": profile.connection_id,
            "display_name": profile.display_name,
            "remote_model_id": profile.remote_model_id,
            "enabled": profile.enabled,
            "allowed_roles": list(profile.allowed_roles),
            "context_limit": profile.context_limit,
            "output_limit": profile.output_limit,
            "model_revision_hash": profile.model_revision_hash,
        }

    def _credential_status(self, connection: ProviderConnection) -> str:
        try:
            return self.store.credential_status(connection.credential_reference)
        except (OSError, UserProviderStoreError):
            return "missing"

    def _assert_payload_excludes_credentials(self, value: object) -> None:
        try:
            self.store.assert_payload_excludes_configured_credentials(value)
        except UserProviderStoreError as error:
            raise OrchestraLiveWebError(str(error)) from None

    def _retain_session_snapshot(
        self,
        snapshot: OrchestraSessionSnapshot,
        *,
        current_epoch: int,
    ) -> None:
        if snapshot.session_id not in self._session_snapshots and (
            len(self._session_snapshots) >= MAXIMUM_RETAINED_SESSION_VIEWS
        ):
            terminal = tuple(
                item
                for item in self._session_snapshots.values()
                if item.session_state not in {"NOT_EXECUTED", "RUNNING"}
                or current_epoch > item.preview.expires_at_epoch
            )
            if not terminal:
                raise OrchestraLiveWebError("too many active Orchestra session views")
            victim = min(
                terminal,
                key=lambda item: (
                    item.updated_at_epoch,
                    item.created_at_epoch,
                    item.session_id,
                ),
            )
            self._session_snapshots.pop(victim.session_id, None)
        self._session_snapshots[snapshot.session_id] = snapshot

    def _replace_session_snapshot(
        self,
        session_id: str,
        **changes: object,
    ) -> None:
        snapshot = self._session_snapshots.get(session_id)
        if snapshot is None:
            raise OrchestraLiveWebError("Orchestra session snapshot is missing")
        self._session_snapshots[session_id] = replace(snapshot, **changes)

    def _invalidate_unconsumed_session_snapshots(
        self,
        *,
        current_epoch: int,
        reason_code: str,
    ) -> None:
        for session_id, snapshot in tuple(self._session_snapshots.items()):
            if snapshot.plan_available and not snapshot.plan_consumed:
                self._session_snapshots[session_id] = replace(
                    snapshot,
                    session_state="INVALIDATED",
                    updated_at_epoch=current_epoch,
                    plan_available=False,
                    plan_consumed=False,
                    exact_human_confirmation_recorded=False,
                    confirmation_hash=None,
                    session_error_code=reason_code,
                )

    def _purge_expired_previews(self, current_epoch: int) -> None:
        expired = [
            preview_hash
            for preview_hash, issued in self._issued_previews.items()
            if current_epoch > issued.preview.expires_at_epoch
        ]
        for preview_hash in expired:
            issued = self._issued_previews.pop(preview_hash, None)
            if issued is not None:
                self._replace_session_snapshot(
                    issued.run.run_id,
                    session_state="EXPIRED",
                    updated_at_epoch=issued.preview.expires_at_epoch,
                    plan_available=False,
                    plan_consumed=False,
                    exact_human_confirmation_recorded=False,
                    confirmation_hash=None,
                )

    def _now(self) -> int:
        value = self._clock()
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise OrchestraLiveWebError("service clock is invalid")
        return int(value)

    @staticmethod
    def _require_payload_fields(
        payload: Mapping[str, object],
        *,
        required: set[str],
        allowed: set[str],
    ) -> None:
        if not isinstance(payload, Mapping):
            raise OrchestraLiveWebError("request JSON must be an object")
        fields = set(payload)
        if not required <= fields or not fields <= allowed:
            raise OrchestraLiveWebError("request fields are missing or unsupported")


__all__ = [
    "DEFAULT_LIVE_MAXIMUM_OUTPUT_TOKENS",
    "DEFAULT_LIVE_TIMEOUT_SECONDS",
    "DEFAULT_PREVIEW_LIFETIME_SECONDS",
    "MAXIMUM_RETAINED_SESSION_VIEWS",
    "OrchestraLiveWebError",
    "OrchestraLiveWebService",
    "ROLE_ORDER",
]
