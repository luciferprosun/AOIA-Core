"""Provider-independent service that prepares and verifies immutable attachments."""

from __future__ import annotations

from pathlib import Path

from .bindings import DEFAULT_BINDINGS_PATH, HatBindingError, load_bindings
from .catalog import HatCatalogEntry
from .canonical import build_attachment, normalize_text, verify_attachment, verify_bundle
from .contracts import (
    HatAttachment,
    HatDescriptor,
    HatEvidenceBundle,
    HatRetrievalLimits,
    HatStatus,
    HatValidationError,
)
from .prompt_rendering import render_evidence_bundle
from .registry import NONE_HAT_ID, HatRegistry

DEFAULT_RETRIEVAL_LIMITS = HatRetrievalLimits(
    max_results=6,
    max_excerpt_chars=2_400,
    max_total_chars=8_000,
)


class HatServiceError(HatValidationError):
    """Fail-closed service error raised before any provider call."""


class HatNoEvidenceError(HatServiceError):
    """The enabled HAT returned no evidence required for provider delivery."""


class HatAttachmentService:
    def __init__(
        self,
        registry: HatRegistry,
        *,
        bindings_path: Path = DEFAULT_BINDINGS_PATH,
    ) -> None:
        self._registry = registry
        self._bindings_path = bindings_path

    @classmethod
    def default(cls) -> "HatAttachmentService":
        return cls(HatRegistry.default())

    def list_descriptors(self) -> tuple[HatDescriptor, ...]:
        return self._registry.list_descriptors()

    def inspect(self, hat_id: str) -> HatStatus:
        if hat_id == NONE_HAT_ID:
            from .canonical import canonical_sha256

            none_digest = canonical_sha256({"hat_id": NONE_HAT_ID})
            return HatStatus(
                hat_id=NONE_HAT_ID,
                state="ready",
                library_id="none",
                library_version="none",
                manifest_id="none",
                manifest_digest=none_digest,
                index_id="none",
                index_digest=none_digest,
                indexed_source_count=0,
                read_only=True,
                local_only=True,
                error_category=None,
            )
        try:
            self._registry.entry(hat_id)
        except HatValidationError:
            return self._error_status(hat_id, "invalid", "unknown_hat_id")
        try:
            bindings = load_bindings(self._registry.known_binding_keys(), self._bindings_path)
        except HatBindingError:
            return self._error_status(hat_id, "invalid", "malformed_binding_file")
        binding = bindings.get(hat_id)
        if binding is None:
            return self._error_status(hat_id, "unavailable", "missing_binding")
        try:
            status = self._registry.adapter(hat_id).inspect_status(binding)
            self._validate_status(self._registry.entry(hat_id), status)
            return status
        except Exception:
            return self._error_status(hat_id, "invalid", "adapter_contract_invalid")

    def prepare_attachment(
        self,
        hat_id: str,
        query: str,
        *,
        limits: HatRetrievalLimits = DEFAULT_RETRIEVAL_LIMITS,
    ) -> HatAttachment | None:
        if hat_id == NONE_HAT_ID:
            return None
        status = self.inspect(hat_id)
        if status.state != "ready":
            raise HatServiceError(status.error_category or "hat_not_ready")
        try:
            bindings = load_bindings(self._registry.known_binding_keys(), self._bindings_path)
            binding = bindings[hat_id]
            adapter = self._registry.adapter(hat_id)
            bundle = adapter.retrieve(binding, query, limits=limits)
            status_after = adapter.inspect_status(binding)
            self._validate_status(self._registry.entry(hat_id), status_after)
        except (HatBindingError, KeyError, HatValidationError) as exc:
            raise HatServiceError("HAT retrieval failed closed") from exc
        except Exception as exc:
            raise HatServiceError("HAT adapter failed closed") from exc
        if status_after != status:
            raise HatServiceError("HAT control identity changed during retrieval")
        self._validate_bundle(status, bundle, limits, expected_query=normalize_text(query))
        if not bundle.passages:
            raise HatNoEvidenceError("HAT retrieval returned no required evidence")
        descriptor = self._registry.entry(hat_id).descriptor
        rendered_evidence = render_evidence_bundle(bundle)
        try:
            root_spellings = {
                binding.root.as_posix(),
                binding.root.resolve(strict=True).as_posix(),
            }
        except OSError as exc:
            raise HatServiceError("HAT binding root changed during retrieval") from exc
        if any(root and root in rendered_evidence for root in root_spellings):
            raise HatServiceError("HAT evidence exposed the private binding root")
        attachment = build_attachment(descriptor, bundle, rendered_evidence)
        self.verify_attachment(attachment)
        return attachment

    def verify_attachment(self, attachment: HatAttachment) -> None:
        try:
            verify_attachment(attachment)
            entry = self._registry.entry(attachment.descriptor.hat_id)
        except HatValidationError as exc:
            raise HatServiceError("HAT attachment verification failed") from exc
        if attachment.descriptor != entry.descriptor:
            raise HatServiceError("retained HAT descriptor no longer matches the catalog")

    @staticmethod
    def _validate_bundle(
        status: HatStatus,
        bundle: HatEvidenceBundle,
        limits: HatRetrievalLimits,
        *,
        expected_query: str,
    ) -> None:
        try:
            verify_bundle(bundle)
        except HatValidationError as exc:
            raise HatServiceError("HAT evidence bundle verification failed") from exc
        expected = (
            status.hat_id,
            status.library_id,
            status.library_version,
            status.manifest_id,
            status.manifest_digest,
            status.index_id,
            status.index_digest,
        )
        actual = (
            bundle.hat_id,
            bundle.library_id,
            bundle.library_version,
            bundle.manifest_id,
            bundle.manifest_digest,
            bundle.index_id,
            bundle.index_digest,
        )
        if actual != expected:
            raise HatServiceError("HAT bundle control identity differs from inspected status")
        if bundle.normalized_query != expected_query:
            raise HatServiceError("HAT bundle query differs from the operator query")
        if len(bundle.passages) > limits.max_results:
            raise HatServiceError("HAT evidence exceeds the result-count bound")
        if any(len(passage.excerpt) > limits.max_excerpt_chars for passage in bundle.passages):
            raise HatServiceError("HAT evidence exceeds the per-excerpt bound")
        if sum(len(passage.excerpt) for passage in bundle.passages) > limits.max_total_chars:
            raise HatServiceError("HAT evidence exceeds the total-character bound")

    @staticmethod
    def _validate_status(entry: HatCatalogEntry, status: HatStatus) -> None:
        if not isinstance(status, HatStatus):
            raise HatServiceError("adapter returned an invalid HAT status")
        if status.hat_id != entry.descriptor.hat_id:
            raise HatServiceError("adapter status HAT id differs from the catalog")
        if status.state != "ready":
            return
        expected = (
            entry.library_id,
            entry.library_version,
            entry.manifest_id,
            entry.manifest_digest,
            entry.index_id,
            entry.index_digest,
            entry.indexed_source_count,
        )
        actual = (
            status.library_id,
            status.library_version,
            status.manifest_id,
            status.manifest_digest,
            status.index_id,
            status.index_digest,
            status.indexed_source_count,
        )
        if actual != expected:
            raise HatServiceError("adapter status control identity differs from the catalog")

    @staticmethod
    def _error_status(hat_id: str, state: str, category: str) -> HatStatus:
        safe_hat_id = hat_id if isinstance(hat_id, str) and hat_id.strip() else "invalid"
        return HatStatus(
            hat_id=safe_hat_id,
            state=state,  # type: ignore[arg-type]
            library_id=None,
            library_version=None,
            manifest_id=None,
            manifest_digest=None,
            index_id=None,
            index_digest=None,
            indexed_source_count=None,
            read_only=True,
            local_only=True,
            error_category=category,
        )
