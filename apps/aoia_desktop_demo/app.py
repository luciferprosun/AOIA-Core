"""Application controller: wires state, providers, and knowledge together.

No ``tkinter`` import here — this module is importable and unit-testable
in an environment without a display or without ``tkinter`` installed.
The UI layer (``ui/main_window.py``) owns the Tk event loop and schedules
calls into this controller from callbacks.
"""

from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .critical_review import (
    CriticalReviewRunner,
    ExecutionStatus,
    ObserverConfig,
    ObserverReviewResult,
    ProviderResolver,
    ReviewSnapshot,
    ReviewValidationError,
    SequentialReviewCanceled,
    build_final_revision_messages,
)
from .knowledge.prompt_context import build_knowledge_system_message
from .knowledge.registry import NONE_PROFILE_ID, KnowledgeProfile, discover_profiles, find_profile
from .knowledge.retrieval_adapter import retrieve_linux_evidence
from .providers.base import ChatMessage, ChatResult, ModelInfo, ProviderError
from .providers.openrouter import OPENROUTER_BASE_URL, OpenRouterClient, OpenRouterConfig
from .security.secret_redaction import redact_exception
from .state.chat_session import ChatSession
from .state.settings import DemoSettings, SessionSecrets, load_settings, save_settings

STATUS_UNTRUSTED = "Provider output: Untrusted suggestion"
STATUS_EVIDENCE_ONLY = "Knowledge: Evidence only"
STATUS_ACTIONS_DISABLED = "Actions: Disabled"
STATUS_HUMAN_REQUIRED = "Human control: Required"
SUGGESTION_LABEL = "AI-generated suggestion — not authority"
SOURCES_LABEL = "Sources attached — inspect evidence before relying on the answer"

PRE_DELIVERY_PRIMARY_DRAFT_STARTED = "PRIMARY_DRAFT_STARTED"
PRE_DELIVERY_PRIMARY_DRAFT_COMPLETED = "PRIMARY_DRAFT_COMPLETED"
PRE_DELIVERY_OBSERVER_STARTED = "OBSERVER_STARTED"
PRE_DELIVERY_OBSERVER_COMPLETED = "OBSERVER_COMPLETED"
PRE_DELIVERY_PRIMARY_FINAL_STARTED = "PRIMARY_FINAL_STARTED"

_PRIMARY_DRAFT_SYSTEM_INSTRUCTION = (
    "Create one internal draft answer to the user's latest prompt. The draft is "
    "untrusted working material for a bounded AOIA review and will not be shown "
    "to the human. Do not claim approval or authority. Return only the draft."
)


def _require_requested_model(result: ChatResult, requested_model_id: str) -> None:
    """Reject provider-side model substitution before retaining model output."""
    if result.model != requested_model_id:
        raise ProviderError("Provider returned a different model than the one explicitly selected.")


@dataclass
class SendResult:
    request_id: int
    chat_result: ChatResult | None
    error_message: str | None
    evidence_count: int
    completed_turn: CompletedPrimaryTurn | None
    observer_results: tuple[ObserverReviewResult, ...] = ()
    pre_delivery_reviewed: bool = False


@dataclass(frozen=True, slots=True)
class SendProgress:
    request_id: int
    stage: str
    observer_index: int | None = None
    observer_result: ObserverReviewResult | None = None


@dataclass(frozen=True, slots=True)
class CompletedPrimaryTurn:
    session_id: str
    original_prompt: str
    primary_response: str
    primary_provider_id: str
    primary_model_id: str
    knowledge_profile_id: str | None
    evidence_text: str


@dataclass(frozen=True, slots=True)
class CriticalReviewCompletion:
    results: tuple[ObserverReviewResult, ...]
    error_category: str | None = None


class _SessionProviderResolver:
    """Resolve only the controller's existing configured session connection."""

    def __init__(self, controller: AppController) -> None:
        self._controller = controller

    def resolve(self, provider_connection_id: str):
        if provider_connection_id not in self._controller.settings.configured_provider_ids():
            return None
        if not self._controller.provider_route_is_eligible():
            return None
        try:
            return self._controller._build_client()
        except ProviderError:
            return None


class AppController:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.settings: DemoSettings = load_settings()
        self.secrets = SessionSecrets()
        self.session = ChatSession()
        self.session_id = f"desktop-session-{uuid4().hex}"
        self.latest_completed_primary_turn: CompletedPrimaryTurn | None = None
        self.knowledge_profiles: list[KnowledgeProfile] = discover_profiles(repo_root)
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="aoia-provider")
        self._critical_review_runner = CriticalReviewRunner()
        self._critical_review_active = False

    # --- settings ------------------------------------------------------

    def save_current_settings(self) -> None:
        save_settings(self.settings)

    def current_knowledge_profile(self) -> KnowledgeProfile:
        return find_profile(self.knowledge_profiles, self.settings.knowledge_profile_id)

    def set_knowledge_profile(self, profile_id: str) -> None:
        self.settings.knowledge_profile_id = profile_id

    # --- provider client -------------------------------------------------

    def _build_client(self) -> OpenRouterClient:
        if not self.secrets.api_key:
            raise ProviderError("No API key set for this session. Open Settings to add one.")
        if self.settings.provider != "openrouter":
            raise ProviderError("Select OpenRouter in Settings before using a provider connection.")
        if self.settings.api_base_url.rstrip("/") != OPENROUTER_BASE_URL:
            raise ProviderError("Enter the OpenRouter API Base URL in Settings before using a provider connection.")
        config = OpenRouterConfig(
            api_key=self.secrets.api_key,
            base_url=self.settings.api_base_url,
            app_title=self.settings.app_title,
            timeout_seconds=self.settings.timeout_seconds,
        )
        return OpenRouterClient(config)

    def test_connection(self) -> None:
        """Raises ProviderError on failure; returns normally on success."""
        try:
            self._build_client().test_connection()
        except ProviderError:
            raise
        except Exception as error:  # pragma: no cover - defensive
            raise ProviderError(redact_exception(error, known_secrets=self._known_secrets())) from None

    def refresh_models(self) -> list[ModelInfo]:
        try:
            return self._build_client().list_models()
        except ProviderError:
            raise
        except Exception as error:  # pragma: no cover - defensive
            raise ProviderError(redact_exception(error, known_secrets=self._known_secrets())) from None

    def _known_secrets(self) -> tuple[str, ...]:
        return (self.secrets.api_key,) if self.secrets.api_key else ()

    def effective_model_id(self) -> str:
        return self.settings.manual_model_id.strip() or self.settings.selected_model_id.strip()

    def provider_route_is_eligible(self) -> bool:
        """Return eligibility only after complete, manual operator entry.

        This is not verification and never performs a provider call.
        """
        return self.settings.has_configured_provider_connection() and bool(self.secrets.api_key)

    # --- chat ------------------------------------------------------------

    def submit_message(
        self,
        user_text: str,
        on_done,
        on_scheduled_callback,
        *,
        observer_configs: tuple[ObserverConfig, ...] = (),
        on_progress=None,
    ) -> int | None:
        """Start a background request for ``user_text``. Returns the
        request id, or ``None`` if a request is already active (caller
        should keep Send disabled in that case so this is defensive only).

        ``on_scheduled_callback(func)`` must marshal ``func`` onto the UI
        thread (e.g. ``root.after(0, func)``); this controller never
        touches Tk directly.
        """
        if self.session.has_active_request:
            return None

        pre_delivery_enabled = self.settings.pre_delivery_critical_loop_enabled
        captured_observer_configs = tuple(observer_configs)
        if pre_delivery_enabled:
            self._critical_review_runner.validate_sequential_configs(captured_observer_configs)

        # Once a new primary request starts, an older completed turn must not
        # be reused silently as the current review subject.
        self.latest_completed_primary_turn = None
        original_prompt = user_text.strip()
        self.session.add_user_message(original_prompt)
        model_id = self.effective_model_id()
        profile = self.current_knowledge_profile()
        provider_id = self.settings.provider

        evidence = []
        if profile.id != NONE_PROFILE_ID:
            evidence = retrieve_linux_evidence(self.repo_root, original_prompt)
        knowledge_message = build_knowledge_system_message(evidence)
        evidence_text = knowledge_message or ""
        knowledge_profile_id = profile.id if profile.id != NONE_PROFILE_ID else None

        request_id = self.session.begin_request()
        if pre_delivery_enabled:
            self._critical_review_active = True

        def schedule_progress(
            stage: str,
            *,
            observer_index: int | None = None,
            observer_result: ObserverReviewResult | None = None,
        ) -> None:
            if on_progress is None:
                return
            progress = SendProgress(
                request_id=request_id,
                stage=stage,
                observer_index=observer_index,
                observer_result=observer_result,
            )
            on_scheduled_callback(lambda progress=progress: on_progress(progress))

        def completed_turn_for(content: str) -> CompletedPrimaryTurn:
            return CompletedPrimaryTurn(
                session_id=self.session_id,
                original_prompt=original_prompt,
                primary_response=content,
                primary_provider_id=provider_id,
                primary_model_id=model_id,
                knowledge_profile_id=knowledge_profile_id,
                evidence_text=evidence_text,
            )

        def work() -> SendResult:
            observer_results: tuple[ObserverReviewResult, ...] = ()
            try:
                client = self._build_client()
                if not pre_delivery_enabled:
                    messages = self.session.messages_for_provider(extra_system_message=knowledge_message)
                    result = client.send_chat(
                        model=model_id,
                        messages=messages,
                        max_tokens=self.settings.max_response_tokens,
                    )
                    _require_requested_model(result, model_id)
                    return SendResult(
                        request_id=request_id,
                        chat_result=result,
                        error_message=None,
                        evidence_count=len(evidence),
                        completed_turn=completed_turn_for(result.content),
                    )

                schedule_progress(PRE_DELIVERY_PRIMARY_DRAFT_STARTED)
                draft_messages = [
                    ChatMessage(role="system", content=_PRIMARY_DRAFT_SYSTEM_INSTRUCTION),
                    *self.session.messages_for_provider(extra_system_message=knowledge_message),
                ]
                draft_result = client.send_chat(
                    model=model_id,
                    messages=draft_messages,
                    max_tokens=self.settings.max_response_tokens,
                )
                _require_requested_model(draft_result, model_id)
                if not self.session.is_current(request_id):
                    raise SequentialReviewCanceled("operator canceled after the primary draft")
                schedule_progress(PRE_DELIVERY_PRIMARY_DRAFT_COMPLETED)

                snapshot = ReviewSnapshot.create(
                    session_id=self.session_id,
                    original_prompt=original_prompt,
                    primary_response=draft_result.content,
                    primary_provider_id=provider_id,
                    primary_model_id=model_id,
                    knowledge_profile_id=knowledge_profile_id,
                    evidence_text=evidence_text,
                )
                resolver = _SessionProviderResolver(self)
                observer_results = self._critical_review_runner.run_sequential(
                    snapshot,
                    captured_observer_configs,
                    resolver,
                    on_result=lambda index, observer_result: schedule_progress(
                        PRE_DELIVERY_OBSERVER_COMPLETED,
                        observer_index=index,
                        observer_result=observer_result,
                    ),
                    on_started=lambda index: schedule_progress(
                        PRE_DELIVERY_OBSERVER_STARTED,
                        observer_index=index,
                    ),
                    should_continue=lambda: self.session.is_current(request_id),
                )
                if any(
                    observer_result.execution_status is not ExecutionStatus.COMPLETED
                    for observer_result in observer_results
                ):
                    return SendResult(
                        request_id=request_id,
                        chat_result=None,
                        error_message=(
                            "Pre-delivery review failed closed; all three observers must complete "
                            "before a final answer can be delivered."
                        ),
                        evidence_count=len(evidence),
                        completed_turn=None,
                        observer_results=observer_results,
                    )
                if not self.session.is_current(request_id):
                    raise SequentialReviewCanceled("operator canceled before the final revision")
                final_messages = build_final_revision_messages(snapshot, observer_results)
                schedule_progress(PRE_DELIVERY_PRIMARY_FINAL_STARTED)
                final_result = client.send_chat(
                    model=model_id,
                    messages=list(final_messages),
                    max_tokens=self.settings.max_response_tokens,
                )
                _require_requested_model(final_result, model_id)
                return SendResult(
                    request_id=request_id,
                    chat_result=final_result,
                    error_message=None,
                    evidence_count=len(evidence),
                    completed_turn=completed_turn_for(final_result.content),
                    observer_results=observer_results,
                    pre_delivery_reviewed=True,
                )
            except SequentialReviewCanceled:
                return SendResult(
                    request_id=request_id,
                    chat_result=None,
                    error_message="Request canceled by operator.",
                    evidence_count=len(evidence),
                    completed_turn=None,
                    observer_results=observer_results,
                )
            except ReviewValidationError:
                return SendResult(
                    request_id=request_id,
                    chat_result=None,
                    error_message="Pre-delivery review failed closed during local validation.",
                    evidence_count=len(evidence),
                    completed_turn=None,
                    observer_results=observer_results,
                )
            except ProviderError as error:
                return SendResult(
                    request_id=request_id,
                    chat_result=None,
                    error_message=str(error),
                    evidence_count=len(evidence),
                    completed_turn=None,
                    observer_results=observer_results,
                )
            except Exception as error:  # pragma: no cover - defensive
                message = redact_exception(error, known_secrets=self._known_secrets())
                return SendResult(
                    request_id=request_id,
                    chat_result=None,
                    error_message=message,
                    evidence_count=len(evidence),
                    completed_turn=None,
                    observer_results=observer_results,
                )

        future = self._executor.submit(work)

        def on_future_done(finished_future: concurrent.futures.Future) -> None:
            result = finished_future.result()

            def finish_on_ui_thread() -> None:
                if pre_delivery_enabled:
                    self._critical_review_active = False
                on_done(result)

            on_scheduled_callback(finish_on_ui_thread)

        future.add_done_callback(on_future_done)
        return request_id

    def accept_completed_primary_turn(self, result: SendResult) -> None:
        """Deliver and retain only a successful result accepted by the UI."""
        if result.error_message is None and result.chat_result is not None and result.completed_turn is not None:
            self.latest_completed_primary_turn = result.completed_turn
            self.session.add_assistant_message(result.chat_result.content)

    def capture_review_snapshot(self) -> ReviewSnapshot | None:
        turn = self.latest_completed_primary_turn
        if turn is None:
            return None
        return ReviewSnapshot.create(
            session_id=turn.session_id,
            original_prompt=turn.original_prompt,
            primary_response=turn.primary_response,
            primary_provider_id=turn.primary_provider_id,
            primary_model_id=turn.primary_model_id,
            knowledge_profile_id=turn.knowledge_profile_id,
            evidence_text=turn.evidence_text,
        )

    @property
    def critical_review_active(self) -> bool:
        return self._critical_review_active

    def validate_pre_delivery_observers(self, observer_configs: tuple[ObserverConfig, ...]) -> None:
        """Validate the fixed three-slot setup without making a provider call."""
        self._critical_review_runner.validate_sequential_configs(observer_configs)

    def submit_critical_review(
        self,
        snapshot: ReviewSnapshot,
        observer_configs: tuple[ObserverConfig, ...],
        on_done,
        on_scheduled_callback,
        *,
        provider_resolver: ProviderResolver | None = None,
    ) -> bool:
        """Start one bounded review run using the existing provider worker."""
        if self._critical_review_active or self.session.has_active_request:
            return False
        self._critical_review_active = True
        resolver = provider_resolver or _SessionProviderResolver(self)

        def work() -> CriticalReviewCompletion:
            try:
                results = self._critical_review_runner.run(snapshot, observer_configs, resolver)
                return CriticalReviewCompletion(results=results)
            except ReviewValidationError:
                return CriticalReviewCompletion(results=(), error_category="review_validation_failed")
            except Exception:  # pragma: no cover - defensive fail-closed boundary
                return CriticalReviewCompletion(results=(), error_category="review_internal_error")

        future = self._executor.submit(work)

        def on_future_done(finished_future: concurrent.futures.Future) -> None:
            completion = finished_future.result()

            def finish_on_ui_thread() -> None:
                self._critical_review_active = False
                on_done(completion)

            on_scheduled_callback(finish_on_ui_thread)

        future.add_done_callback(on_future_done)
        return True

    def cancel_active_request(self) -> None:
        self.session.cancel_active_request()

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
