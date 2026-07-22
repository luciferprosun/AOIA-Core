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


class AppController:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.settings: DemoSettings = load_settings()
        self.secrets = SessionSecrets()
        self.session = ChatSession()
        self.knowledge_profiles: list[KnowledgeProfile] = discover_profiles(repo_root)
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="aoia-provider")

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

        self.session.add_user_message(user_text)
        model_id = self.effective_model_id()
        profile = self.current_knowledge_profile()

        evidence = []
        if profile.id != NONE_PROFILE_ID:
            evidence = retrieve_linux_evidence(self.repo_root, user_text)
        knowledge_message = build_knowledge_system_message(evidence)

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
                return SendResult(request_id=request_id, chat_result=result, error_message=None, evidence_count=len(evidence))
            except ProviderError as error:
                return SendResult(request_id=request_id, chat_result=None, error_message=str(error), evidence_count=len(evidence))
            except Exception as error:  # pragma: no cover - defensive
                message = redact_exception(error, known_secrets=self._known_secrets())
                return SendResult(request_id=request_id, chat_result=None, error_message=message, evidence_count=len(evidence))

        future = self._executor.submit(work)

        def on_future_done(finished_future: concurrent.futures.Future) -> None:
            result = finished_future.result()
            on_scheduled_callback(lambda: on_done(result))

        future.add_done_callback(on_future_done)
        return request_id

    def cancel_active_request(self) -> None:
        self.session.cancel_active_request()

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
