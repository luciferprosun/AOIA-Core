from __future__ import annotations

from dataclasses import asdict, dataclass

from runtime.memory_hats.unix_hat import (
    NON_AUTHORITATIVE,
    UnixHatDescriptor,
    UnixHatRoutingError,
    validate_unix_hat_descriptor,
)


@dataclass(frozen=True)
class MemoryHatRecord:
    hat_id: str
    name: str
    domain: str
    status: str
    purpose: str
    canonical_paths: tuple[str, ...]
    candidate_paths: tuple[str, ...]
    runtime_visible: bool
    execution_allowed: bool
    human_review_required: bool
    promotion_policy: str
    notes: tuple[str, ...]


MEMORY_HATS: tuple[MemoryHatRecord, ...] = (
    MemoryHatRecord(
        hat_id="hat_001",
        name="Hat 001 - Bash Safety",
        domain="bash_safety",
        status="ACTIVE_CORE",
        purpose="Classify shell-command risk and approval state for pre-execution review.",
        canonical_paths=(
            "runtime/safety/bash_parser.py",
            "runtime/safety/approval_gate.py",
            "tests/corpus/",
        ),
        candidate_paths=("tests/",),
        runtime_visible=True,
        execution_allowed=False,
        human_review_required=True,
        promotion_policy="Core safety changes require tests and human review before merge.",
        notes=("Inert control surface only.", "Does not execute shell commands."),
    ),
    MemoryHatRecord(
        hat_id="hat_002",
        name="Hat 002 - Linux/RHCSA",
        domain="linux_rhcsa",
        status="ACTIVE_KNOWLEDGE",
        purpose="Track local Linux/RHCSA knowledge surfaces and retrieval boundaries.",
        canonical_paths=(
            "knowledge/",
            "runtime/knowledge/",
            "runtime/retrieval/",
        ),
        candidate_paths=("knowledge/hats/", "tests/"),
        runtime_visible=True,
        execution_allowed=False,
        human_review_required=True,
        promotion_policy="Knowledge promotion requires source review and provenance checks.",
        notes=("Local-first knowledge surface.", "Not trusted truth by default."),
    ),
    MemoryHatRecord(
        hat_id="hat_003",
        name="Hat 003 - Python",
        domain="python",
        status="DRAFT_KNOWLEDGE",
        purpose="Track draft Python knowledge and advisory-review status.",
        canonical_paths=("knowledge/languages/python/",),
        candidate_paths=("knowledge/hats/hat_003_python/", "tests/"),
        runtime_visible=True,
        execution_allowed=False,
        human_review_required=True,
        promotion_policy="Draft Python records remain non-canonical until reviewed.",
        notes=("Draft knowledge surface.", "No code execution authority."),
    ),
    MemoryHatRecord(
        hat_id="hat_004",
        name="Hat 004 - Browser Governance",
        domain="browser_governance",
        status="FROZEN_GOVERNANCE",
        purpose="Track browser-governance boundaries and frozen proposal-only schemas.",
        canonical_paths=(
            "runtime/schemas/hat004_action_proposals.py",
            "runtime/schemas/chat4_agentic_proposals.py",
            "docs/audit/HAT_004_BROWSER_GOVERNANCE_POLICY.md",
        ),
        candidate_paths=("tests/hat004/", "docs/audit/"),
        runtime_visible=True,
        execution_allowed=False,
        human_review_required=True,
        promotion_policy="Browser-related proposals remain inert until separate governance review.",
        notes=("Frozen governance surface.", "Does not launch browsers or fetch URLs."),
    ),
)


def get_memory_hats() -> tuple[MemoryHatRecord, ...]:
    """Return static Memory Hat records.

    This registry is inert metadata. It does not scan the filesystem, call
    external model services, execute tools, read environment secrets, or promote knowledge.
    """
    return MEMORY_HATS


def get_memory_hat_payload() -> dict[str, object]:
    return {
        "ok": True,
        "product": "AIOA White Hat",
        "surface": "Memory Hats / White Hat Control Surface",
        "notice": "Memory Hats classify knowledge and review domains. They do not execute actions.",
        "execution_allowed": False,
        "human_review_required": True,
        "hats": [_record_to_dict(record) for record in get_memory_hats()],
    }


def _record_to_dict(record: MemoryHatRecord) -> dict[str, object]:
    payload = asdict(record)
    payload["canonical_paths"] = list(record.canonical_paths)
    payload["candidate_paths"] = list(record.candidate_paths)
    payload["notes"] = list(record.notes)
    return payload


@dataclass(frozen=True, slots=True)
class UnixHatRegistry:
    """Immutable registry for validated UNIX Hat descriptor metadata."""

    descriptors: tuple[UnixHatDescriptor, ...] = ()
    authority_status: str = NON_AUTHORITATIVE

    def register(self, descriptor: UnixHatDescriptor) -> "UnixHatRegistry":
        validate_unix_hat_descriptor(descriptor)
        if self.authority_status != NON_AUTHORITATIVE:
            raise UnixHatRoutingError(
                "STALE_HAT_DESCRIPTOR",
                "registry authority status is invalid",
            )
        if any(item.hat_id == descriptor.hat_id for item in self.descriptors):
            raise UnixHatRoutingError(
                "DUPLICATE_HAT_ID",
                "Hat ID is already registered",
            )
        if any(
            item.descriptor_hash == descriptor.descriptor_hash
            for item in self.descriptors
        ):
            raise UnixHatRoutingError(
                "DUPLICATE_HAT_HASH",
                "Hat descriptor hash is already registered",
            )
        return UnixHatRegistry(
            descriptors=tuple(
                sorted(
                    (*self.descriptors, descriptor),
                    key=lambda item: item.hat_id,
                )
            )
        )

    def resolve(self, hat_id: str) -> UnixHatDescriptor | None:
        if not isinstance(hat_id, str):
            raise TypeError("hat_id must be a string")
        return next(
            (item for item in self.descriptors if item.hat_id == hat_id),
            None,
        )

    def list_descriptors(self) -> tuple[UnixHatDescriptor, ...]:
        return self.descriptors
