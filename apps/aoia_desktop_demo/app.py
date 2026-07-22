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
    ObserverConfig,
    ObserverReviewResult,
    ProviderResolver,
    ReviewSnapshot,
    ReviewValidationError,
)
from .knowledge.prompt_context import build_knowledge_system_message
from .knowledge.registry import NONE_PROFILE_ID, KnowledgeProfile, discover_profiles, find_profile
from .knowledge.retrieval_adapter import retrieve_linux_evidence
from .providers.base import ChatResult, ModelInfo, ProviderError
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


@dataclass
class SendResult:
    request_id: int
    chat_result: ChatResult | None
    error_message: str | None
    evidence_count: int
    completed_turn: CompletedPrimaryTurn | None


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

        def work() -> SendResult:
            try:
                client = self._build_client()
                messages = self.session.messages_for_provider(extra_system_message=knowledge_message)
                result = client.send_chat(
                    model=model_id,
                    messages=messages,
                    max_tokens=self.settings.max_response_tokens,
                )
                completed_turn = CompletedPrimaryTurn(
                    session_id=self.session_id,
                    original_prompt=original_prompt,
                    primary_response=result.content,
                    primary_provider_id=provider_id,
                    primary_model_id=model_id,
                    knowledge_profile_id=knowledge_profile_id,
                    evidence_text=evidence_text,
                )
                return SendResult(
                    request_id=request_id,
                    chat_result=result,
                    error_message=None,
                    evidence_count=len(evidence),
                    completed_turn=completed_turn,
                )
            except ProviderError as error:
                return SendResult(
                    request_id=request_id,
                    chat_result=None,
                    error_message=str(error),
                    evidence_count=len(evidence),
                    completed_turn=None,
                )
            except Exception as error:  # pragma: no cover - defensive
                message = redact_exception(error, known_secrets=self._known_secrets())
                return SendResult(
                    request_id=request_id,
                    chat_result=None,
                    error_message=message,
                    evidence_count=len(evidence),
                    completed_turn=None,
                )

        future = self._executor.submit(work)

        def on_future_done(finished_future: concurrent.futures.Future) -> None:
            result = finished_future.result()
            on_scheduled_callback(lambda: on_done(result))

        future.add_done_callback(on_future_done)
        return request_id

    def accept_completed_primary_turn(self, result: SendResult) -> None:
        """Retain only a successful result already accepted by the UI."""
        if result.error_message is None and result.chat_result is not None and result.completed_turn is not None:
            self.latest_completed_primary_turn = result.completed_turn

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
