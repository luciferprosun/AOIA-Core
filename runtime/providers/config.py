from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from .base import ModelProvider, require_provider_calls_enabled
from .gemini_provider import GeminiProvider
from .openai_compatible import OpenAICompatibleProvider
from .errors import typed_provider_error, validate_model_response_text
from runtime.safety.atomic_persistence import atomic_write_json, state_resource_lock_path
from runtime.sensitive_redaction import (
    RUNTIME_SECRET_ENV_NAMES,
    build_current_runtime_redactor,
)
from runtime_paths import runtime_state_dir
from trace_context import ModelCallContext, TraceContext, TracedModelOutput


PROVIDER_NETWORK_SURFACE = True
APPROVED_RUNTIME_PROVIDER_FLOW = False
PROVIDER_CALLS_FROZEN = True


DEFAULT_MODEL = "openrouter/google/gemma-3-27b-it"
DEFAULT_PROVIDER_CHAIN = [
    {"name": "openrouter", "model": "google/gemma-3-27b-it", "enabled": True},
    {"name": "gemini", "model": "gemini-2.5-flash", "enabled": True},
    {"name": "xai", "model": "grok-4.3", "enabled": True},
    {"name": "deepseek", "model": "deepseek-chat", "enabled": True},
]

DEFAULT_MODEL_PRESETS: dict[str, str] = {
    "gemma": "openrouter/google/gemma-3-27b-it",
    "openrouter": "openrouter/free",
    "openrouter-gemma": "openrouter/google/gemma-3-27b-it",
    "gemini": "gemini/gemini-2.5-flash",
    "grok": "xai/grok-4.3",
    "xai": "xai/grok-4.3",
    "deepseek": "deepseek/deepseek-chat",
}

API_FILE_CANDIDATES = [
    Path.home() / ".config" / "aoia" / "secrets" / "openrouter.env",
    Path.home() / ".config" / "aoia" / "secrets" / "gemini.env",
    Path.home() / ".config" / "aoia" / "secrets" / "xai.env",
    Path.home() / ".config" / "aoia" / "secrets" / "deepseek.env",
    Path.home() / ".config" / "openrouter" / "api.env",
    Path.home() / ".config" / "gemini" / "api.env",
    Path.home() / ".config" / "xai" / "api.env",
    Path.home() / ".config" / "grok" / "api.env",
    Path.home() / ".config" / "deepseek" / "api.env",
]

REMOVED_PROVIDERS = {"openai", "huggingface", "gemma-hf"}


ModelAttemptObserver = Callable[
    [str, ModelCallContext, str, str, int],
    None,
]


@dataclass
class ProviderConfig:
    name: str
    model: str
    enabled: bool = True

    @property
    def full_name(self) -> str:
        return f"{self.name}/{self.model}"


def _read_api_environment_values() -> dict[str, str]:
    """Parse configured local provider files without logging or activating them."""

    combined: dict[str, str] = {}
    for env_path in API_FILE_CANDIDATES:
        if not env_path.exists():
            continue
        for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[len("export ") :].strip()
            name, value = line.split("=", 1)
            name = name.strip()
            value = value.strip().strip('"').strip("'")
            if name and value:
                combined[name] = value
    return combined


def load_api_environment() -> None:
    """Load private local API env files without exposing secrets."""

    for name, value in _read_api_environment_values().items():
        if not os.getenv(name):
            os.environ[name] = value


class ProviderManager:
    """Cloud-provider manager with fallback routing and no fake offline mode."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self.runtime_state_root = runtime_state_dir(project_dir)
        self.state_dir = self.runtime_state_root / "state"
        self.config_path = self.state_dir / "model_config.json"
        self.providers_path = self.state_dir / "providers.json"
        self.provider_chain = self._load_provider_chain()
        self.current_model = self.normalize_model_name(self._load_model_name())
        self.provider: ModelProvider | None = None
        self.last_used_model = ""
        self._refresh_output_redactor()

    def _refresh_output_redactor(self) -> None:
        configured = _read_api_environment_values()
        secret_names = frozenset(RUNTIME_SECRET_ENV_NAMES)
        self.output_redactor = build_current_runtime_redactor(
            environ=os.environ,
            additional_values=(
                value
                for name, value in configured.items()
                if name in secret_names
            )
        )

    def generate(self, prompt: str) -> str:
        return self.generate_with_fallback(prompt)

    def generate_traced(
        self,
        prompt: str,
        trace_context: TraceContext,
        *,
        on_attempt: ModelAttemptObserver | None = None,
    ) -> TracedModelOutput:
        """Invoke fallback providers while identifying every actual call attempt."""

        errors: list[str] = []
        provider_errors: list[BaseException] = []
        tried: set[str] = set()
        provider_attempt = 0
        for full_model in self._fallback_candidates():
            if full_model in tried:
                continue
            tried.add(full_model)
            provider_attempt += 1
            provider_id = full_model.split("/", 1)[0]
            model_call = trace_context.new_model_call()
            if on_attempt is not None:
                on_attempt(
                    "started",
                    model_call,
                    provider_id,
                    full_model,
                    provider_attempt,
                )
            try:
                require_provider_calls_enabled(provider_id)
                load_api_environment()
                self._refresh_output_redactor()
                provider = self._build_provider(full_model)
                response = self.output_redactor.redact_text(
                    validate_model_response_text(
                        provider.generate(self.output_redactor.redact_text(prompt))
                    )
                )
                self.provider = provider
                self.current_model = full_model
                self.last_used_model = provider.full_name
            except Exception as error:
                if on_attempt is not None:
                    try:
                        on_attempt(
                            "failed",
                            model_call,
                            provider_id,
                            full_model,
                            provider_attempt,
                        )
                    except Exception as observer_error:
                        try:
                            observer_error.add_note(
                                "Provider call also failed; provider failure type: "
                                f"{type(error).__name__}."
                            )
                        except AttributeError:  # pragma: no cover
                            pass
                        raise observer_error from error
                self._refresh_output_redactor()
                errors.append(
                    self.output_redactor.redact_text(f"{full_model}: {error}")
                )
                provider_errors.append(error)
                continue
            # A terminal observer is a security persistence boundary, not part
            # of the provider call. Its failure must not be misclassified as a
            # provider failure or trigger a second provider dispatch.
            if on_attempt is not None:
                on_attempt(
                    "succeeded",
                    model_call,
                    provider_id,
                    full_model,
                    provider_attempt,
                )
            return TracedModelOutput(
                text=response,
                model_call=model_call,
                provider=provider_id,
                model=full_model,
            )

        if not errors:
            raise RuntimeError("No enabled cloud providers are configured.")

        terminal_error = typed_provider_error(provider_errors[-1])
        terminal_error.args = (
            "No configured cloud provider succeeded. Checked:\n- "
            + "\n- ".join(errors),
        )
        raise terminal_error from provider_errors[-1]

    def generate_with_fallback(self, prompt: str) -> str:
        errors: list[str] = []
        provider_errors: list[BaseException] = []
        tried: set[str] = set()
        for full_model in self._fallback_candidates():
            if full_model in tried:
                continue
            tried.add(full_model)
            try:
                provider_id = full_model.split("/", 1)[0]
                require_provider_calls_enabled(provider_id)
                load_api_environment()
                self._refresh_output_redactor()
                provider = self._build_provider(full_model)
                response = self.output_redactor.redact_text(
                    validate_model_response_text(
                        provider.generate(self.output_redactor.redact_text(prompt))
                    )
                )
                self.provider = provider
                self.current_model = full_model
                self.last_used_model = provider.full_name
                return response
            except Exception as error:
                self._refresh_output_redactor()
                errors.append(
                    self.output_redactor.redact_text(f"{full_model}: {error}")
                )
                provider_errors.append(error)

        if not errors:
            raise RuntimeError("No enabled cloud providers are configured.")

        terminal_error = typed_provider_error(provider_errors[-1])
        terminal_error.args = (
            "No configured cloud provider succeeded. Checked:\n- "
            + "\n- ".join(errors),
        )
        raise terminal_error from provider_errors[-1]

    def switch_model(self, model_name: str) -> str:
        normalized = self.normalize_model_name(model_name)
        self.current_model = normalized
        self.last_used_model = ""
        self.provider = None
        atomic_write_json(
            self.config_path,
            {"model": normalized},
            lock_path=state_resource_lock_path(self.state_dir, self.config_path),
        )
        return self.current_model

    def describe(self) -> str:
        return self.last_used_model or self.current_model

    def active_fallback_chain(self) -> list[str]:
        return [provider.full_name for provider in self.provider_chain if provider.enabled]

    def available_models(self) -> list[str]:
        return [
            f"{alias:<15} -> {model}"
            for alias, model in DEFAULT_MODEL_PRESETS.items()
            if model.split("/", 1)[0] not in REMOVED_PROVIDERS
            and self._provider_is_available(model.split("/", 1)[0])
        ]

    def provider_status(self) -> list[dict[str, str | bool]]:
        rows: list[dict[str, str | bool]] = []
        for provider in self.provider_chain:
            rows.append(
                {
                    "name": provider.name,
                    "model": provider.model,
                    "enabled": provider.enabled,
                    "available": self._provider_is_available(provider.name),
                    "full_name": provider.full_name,
                }
            )
        return rows

    def model_notice(self, model_name: str) -> str | None:
        normalized = self.normalize_model_name(model_name)
        provider = normalized.split("/", 1)[0]
        if provider == "gemini":
            return "Gemini uses GEMINI_API_KEY and the google-genai SDK."
        if provider == "openrouter":
            return "OpenRouter uses OPENROUTER_API_KEY. Current Gemma preset: google/gemma-3-27b-it."
        if provider == "deepseek":
            return "DeepSeek uses DEEPSEEK_API_KEY and an OpenAI-compatible endpoint."
        if provider == "xai":
            return "Grok uses XAI_API_KEY and the OpenAI-compatible xAI endpoint."
        if provider in REMOVED_PROVIDERS:
            return "This provider was removed from the terminal app because it is not configured."
        return None

    def normalize_model_name(self, model_name: str) -> str:
        value = model_name.strip()
        if not value:
            raise ValueError("Model name cannot be empty.")

        lowered = value.lower()
        if lowered in DEFAULT_MODEL_PRESETS:
            return DEFAULT_MODEL_PRESETS[lowered]

        if ":" in value and "/" not in value:
            provider, model = value.split(":", 1)
            value = f"{provider.strip()}/{model.strip()}"

        if "/" not in value:
            return f"gemini/{value}"

        provider, model = value.split("/", 1)
        provider = provider.strip().lower()
        model = model.strip()
        if not provider or not model:
            raise ValueError(f"Invalid model name: {model_name}")
        return f"{provider}/{model}"

    def _fallback_candidates(self) -> list[str]:
        candidates = [self.current_model]
        candidates.extend(
            provider.full_name
            for provider in self.provider_chain
            if provider.enabled and self._provider_is_available(provider.name)
        )
        return candidates

    def _load_provider_chain(self) -> list[ProviderConfig]:
        if not self.providers_path.exists():
            return [ProviderConfig(**payload) for payload in DEFAULT_PROVIDER_CHAIN]

        try:
            payload = json.loads(self.providers_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {"providers": DEFAULT_PROVIDER_CHAIN}

        providers: list[ProviderConfig] = []
        for item in payload.get("providers", []):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip().lower()
            model = str(item.get("model", "")).strip()
            if name in REMOVED_PROVIDERS:
                continue
            if name and model:
                providers.append(
                    ProviderConfig(
                        name=name,
                        model=model,
                        enabled=bool(item.get("enabled", True)),
                    )
                )

        if not providers:
            return [ProviderConfig(**item) for item in DEFAULT_PROVIDER_CHAIN]

        existing = {(provider.name, provider.model) for provider in providers}
        for item in DEFAULT_PROVIDER_CHAIN:
            key = (item["name"], item["model"])
            if key not in existing:
                providers.append(ProviderConfig(**item))
        return providers

    def _load_model_name(self) -> str:
        if not self.config_path.exists():
            return DEFAULT_MODEL
        try:
            payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return DEFAULT_MODEL
        model = str(payload.get("model") or DEFAULT_MODEL)
        provider = model.split("/", 1)[0].lower()
        if provider in REMOVED_PROVIDERS:
            return DEFAULT_MODEL
        return model

    def _build_provider(self, model_name: str) -> ModelProvider:
        provider, model = model_name.split("/", 1)
        require_provider_calls_enabled(provider)

        if provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise FileNotFoundError("GEMINI_API_KEY not found")
            return GeminiProvider(api_key, model)
        if provider == "openrouter":
            return OpenAICompatibleProvider(
                provider="openrouter",
                api_key=self._load_env_key("OPENROUTER_API_KEY"),
                model=model,
                base_url="https://openrouter.ai/api/v1",
            )
        if provider == "deepseek":
            return OpenAICompatibleProvider(
                provider="deepseek",
                api_key=self._load_env_key("DEEPSEEK_API_KEY"),
                model=model,
                base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            )
        if provider == "xai":
            return OpenAICompatibleProvider(
                provider="xai",
                api_key=self._load_xai_key(),
                model=model,
                base_url=os.getenv("XAI_BASE_URL", "https://api.x.ai/v1"),
            )
        if provider in REMOVED_PROVIDERS:
            raise ValueError(f"Provider removed from terminal app: {provider}")

        raise ValueError(f"Unsupported provider: {provider}")

    @staticmethod
    def _load_env_key(env_name: str) -> str:
        value = os.getenv(env_name, "").strip()
        if value:
            return value
        raise FileNotFoundError(f"{env_name} not found")

    @staticmethod
    def _load_xai_key() -> str:
        value = os.getenv("XAI_API_KEY", "").strip()
        if value:
            return value
        raise FileNotFoundError("XAI_API_KEY not found")

    @staticmethod
    def _provider_is_available(provider: str) -> bool:
        if provider == "gemini":
            return bool(os.getenv("GEMINI_API_KEY", "").strip())
        if provider == "openrouter":
            return bool(os.getenv("OPENROUTER_API_KEY", "").strip())
        if provider == "xai":
            return bool(os.getenv("XAI_API_KEY", "").strip())
        if provider == "deepseek":
            return bool(os.getenv("DEEPSEEK_API_KEY", "").strip())
        if provider in REMOVED_PROVIDERS:
            return False
        return False
