from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping
from uuid import uuid4


class Hat004ActionDomain(str, Enum):
    BROWSER = "browser"
    FILE = "file"
    PDF = "pdf"
    ZIP = "zip"


class Hat004ReviewState(str, Enum):
    READ_ONLY_CANDIDATE = "read_only_candidate"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    FORBIDDEN_NEAR_TERM = "forbidden_near_term"


READ_ONLY_ACTIONS = frozenset(
    {
        "browser_read_current_url",
        "browser_read_page_title",
        "browser_read_visible_text",
        "browser_list_visible_links",
        "browser_list_visible_form_fields",
        "file_describe_local_candidate",
        "pdf_describe_candidate",
        "zip_describe_candidate",
    }
)

HUMAN_REVIEW_REQUIRED_ACTIONS = frozenset(
    {
        "browser_open_url",
        "browser_follow_link",
        "browser_click_visible_element",
        "browser_type_text",
        "browser_press_enter",
        "browser_capture_screenshot",
        "file_prepare_download_review",
        "pdf_extract_text_review",
        "zip_list_entries_review",
        "zip_extract_review",
    }
)

FORBIDDEN_NEAR_TERM_ACTIONS = frozenset(
    {
        "browser_login",
        "browser_enter_password",
        "browser_handle_credentials",
        "browser_create_account",
        "browser_payment_action",
        "browser_checkout",
        "browser_submit_form_without_review",
        "browser_install_extension",
        "browser_captcha_bypass",
        "browser_stealth_automation",
        "browser_cookie_access",
        "browser_session_access",
        "browser_autonomous_navigation",
        "file_execute_download",
        "pdf_parse_without_review",
        "zip_unpack_without_review",
    }
)

KNOWN_ACTIONS = READ_ONLY_ACTIONS | HUMAN_REVIEW_REQUIRED_ACTIONS | FORBIDDEN_NEAR_TERM_ACTIONS

ACTION_DOMAINS = {
    "browser": Hat004ActionDomain.BROWSER,
    "file": Hat004ActionDomain.FILE,
    "pdf": Hat004ActionDomain.PDF,
    "zip": Hat004ActionDomain.ZIP,
}


@dataclass(frozen=True)
class Hat004ActionProposal:
    action_type: str
    target: str
    reason: str
    source: str
    created_by: str
    proposal_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    dry_run: bool = True
    proposal_only: bool = True
    execution_permitted: bool = False
    autonomous_action: bool = False
    login_requested: bool = False
    credential_handling_requested: bool = False
    cookie_access_requested: bool = False
    session_access_requested: bool = False
    form_submission_requested: bool = False
    download_requested: bool = False
    file_write_requested: bool = False
    pdf_parse_requested: bool = False
    zip_unpack_requested: bool = False
    external_network_action_requested: bool = False

    def __post_init__(self) -> None:
        normalized_action = self._normalize_text("action_type", self.action_type)
        if normalized_action not in KNOWN_ACTIONS:
            raise ValueError(f"Unsupported Hat 004 action_type: {self.action_type!r}")
        object.__setattr__(self, "action_type", normalized_action)
        object.__setattr__(self, "target", self._normalize_text("target", self.target))
        object.__setattr__(self, "reason", self._normalize_text("reason", self.reason))
        object.__setattr__(self, "source", self._normalize_text("source", self.source))
        object.__setattr__(self, "created_by", self._normalize_text("created_by", self.created_by))
        if self.proposal_id is None:
            object.__setattr__(self, "proposal_id", uuid4().hex)
        elif not isinstance(self.proposal_id, str) or not self.proposal_id.strip():
            raise ValueError("proposal_id must be a nonblank string")
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        object.__setattr__(self, "metadata", dict(self.metadata))
        self._validate_inert_flags()

    @staticmethod
    def _normalize_text(name: str, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{name} must be a string")
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{name} must be nonblank")
        return normalized

    def _validate_inert_flags(self) -> None:
        bool_fields = {
            "dry_run": self.dry_run,
            "proposal_only": self.proposal_only,
            "execution_permitted": self.execution_permitted,
            "autonomous_action": self.autonomous_action,
            "login_requested": self.login_requested,
            "credential_handling_requested": self.credential_handling_requested,
            "cookie_access_requested": self.cookie_access_requested,
            "session_access_requested": self.session_access_requested,
            "form_submission_requested": self.form_submission_requested,
            "download_requested": self.download_requested,
            "file_write_requested": self.file_write_requested,
            "pdf_parse_requested": self.pdf_parse_requested,
            "zip_unpack_requested": self.zip_unpack_requested,
            "external_network_action_requested": self.external_network_action_requested,
        }
        for name, value in bool_fields.items():
            if not isinstance(value, bool):
                raise TypeError(f"{name} must be bool")
        if not self.dry_run:
            raise ValueError("Hat 004 proposals must remain dry_run=True")
        if not self.proposal_only:
            raise ValueError("Hat 004 proposals must remain proposal_only=True")
        if self.execution_permitted:
            raise ValueError("Hat 004 proposals must keep execution_permitted=False")
        if self.autonomous_action:
            raise ValueError("Hat 004 proposals must not request autonomous actions")
        if self.login_requested:
            raise ValueError("Hat 004 proposals must not request login")
        if self.credential_handling_requested:
            raise ValueError("Hat 004 proposals must not request credential handling")
        if self.cookie_access_requested:
            raise ValueError("Hat 004 proposals must not request cookie access")
        if self.session_access_requested:
            raise ValueError("Hat 004 proposals must not request session access")
        if self.form_submission_requested:
            raise ValueError("Hat 004 proposals must not request form submission")
        if self.download_requested:
            raise ValueError("Hat 004 proposals must not request download execution")
        if self.file_write_requested:
            raise ValueError("Hat 004 proposals must not request file writes")
        if self.pdf_parse_requested:
            raise ValueError("Hat 004 proposals must not request PDF parsing")
        if self.zip_unpack_requested:
            raise ValueError("Hat 004 proposals must not request ZIP unpacking")
        if self.external_network_action_requested:
            raise ValueError("Hat 004 proposals must not request external network actions")

    @property
    def domain(self) -> Hat004ActionDomain:
        prefix = self.action_type.split("_", 1)[0]
        return ACTION_DOMAINS[prefix]

    @property
    def review_state(self) -> Hat004ReviewState:
        if self.action_type in READ_ONLY_ACTIONS:
            return Hat004ReviewState.READ_ONLY_CANDIDATE
        if self.action_type in HUMAN_REVIEW_REQUIRED_ACTIONS:
            return Hat004ReviewState.REQUIRES_HUMAN_REVIEW
        return Hat004ReviewState.FORBIDDEN_NEAR_TERM

    @property
    def requires_human_review(self) -> bool:
        return self.review_state != Hat004ReviewState.READ_ONLY_CANDIDATE

    @property
    def forbidden_near_term(self) -> bool:
        return self.review_state == Hat004ReviewState.FORBIDDEN_NEAR_TERM

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "action_type": self.action_type,
            "domain": self.domain.value,
            "target": self.target,
            "reason": self.reason,
            "source": self.source,
            "created_by": self.created_by,
            "review_state": self.review_state.value,
            "requires_human_review": self.requires_human_review,
            "forbidden_near_term": self.forbidden_near_term,
            "dry_run": self.dry_run,
            "proposal_only": self.proposal_only,
            "execution_permitted": self.execution_permitted,
            "autonomous_action": self.autonomous_action,
            "login_requested": self.login_requested,
            "credential_handling_requested": self.credential_handling_requested,
            "cookie_access_requested": self.cookie_access_requested,
            "session_access_requested": self.session_access_requested,
            "form_submission_requested": self.form_submission_requested,
            "download_requested": self.download_requested,
            "file_write_requested": self.file_write_requested,
            "pdf_parse_requested": self.pdf_parse_requested,
            "zip_unpack_requested": self.zip_unpack_requested,
            "external_network_action_requested": self.external_network_action_requested,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Hat004ActionProposal":
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        allowed_keys = {
            "proposal_id",
            "action_type",
            "domain",
            "target",
            "reason",
            "source",
            "created_by",
            "review_state",
            "requires_human_review",
            "forbidden_near_term",
            "dry_run",
            "proposal_only",
            "execution_permitted",
            "autonomous_action",
            "login_requested",
            "credential_handling_requested",
            "cookie_access_requested",
            "session_access_requested",
            "form_submission_requested",
            "download_requested",
            "file_write_requested",
            "pdf_parse_requested",
            "zip_unpack_requested",
            "external_network_action_requested",
            "metadata",
        }
        unknown_keys = set(payload) - allowed_keys
        if unknown_keys:
            raise ValueError(f"Unsupported Hat 004 proposal fields: {sorted(unknown_keys)!r}")
        proposal = cls(
            proposal_id=payload.get("proposal_id"),
            action_type=payload.get("action_type", ""),
            target=payload.get("target", ""),
            reason=payload.get("reason", ""),
            source=payload.get("source", ""),
            created_by=payload.get("created_by", ""),
            dry_run=payload.get("dry_run", True),
            proposal_only=payload.get("proposal_only", True),
            execution_permitted=payload.get("execution_permitted", False),
            autonomous_action=payload.get("autonomous_action", False),
            login_requested=payload.get("login_requested", False),
            credential_handling_requested=payload.get("credential_handling_requested", False),
            cookie_access_requested=payload.get("cookie_access_requested", False),
            session_access_requested=payload.get("session_access_requested", False),
            form_submission_requested=payload.get("form_submission_requested", False),
            download_requested=payload.get("download_requested", False),
            file_write_requested=payload.get("file_write_requested", False),
            pdf_parse_requested=payload.get("pdf_parse_requested", False),
            zip_unpack_requested=payload.get("zip_unpack_requested", False),
            external_network_action_requested=payload.get("external_network_action_requested", False),
            metadata=payload.get("metadata", {}),
        )
        if (
            "domain" in payload
            and (
                not isinstance(payload["domain"], str)
                or payload["domain"] != proposal.domain.value
            )
        ):
            raise ValueError("domain does not match action_type")
        if (
            "review_state" in payload
            and (
                not isinstance(payload["review_state"], str)
                or payload["review_state"] != proposal.review_state.value
            )
        ):
            raise ValueError("review_state does not match action_type")
        if (
            "requires_human_review" in payload
            and (
                not isinstance(payload["requires_human_review"], bool)
                or payload["requires_human_review"] != proposal.requires_human_review
            )
        ):
            raise ValueError("requires_human_review does not match action_type")
        if (
            "forbidden_near_term" in payload
            and (
                not isinstance(payload["forbidden_near_term"], bool)
                or payload["forbidden_near_term"] != proposal.forbidden_near_term
            )
        ):
            raise ValueError("forbidden_near_term does not match action_type")
        return proposal
