from __future__ import annotations

import hashlib
import json
import posixpath
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable


# Policy-H0A evaluates inert read/proposal/record scopes. It grants no runtime capability.
AOIA_POLICY_PROFILE = "AOIA_POLICY_PROFILE"
AOIA_POLICY_EVALUATION = "AOIA_POLICY_EVALUATION"
POLICY_SCHEMA_VERSION = "1.0"

DEFAULT_DENY = "DEFAULT_DENY"
NO_EXECUTION = "NO_EXECUTION"
NO_ARTIFACT_WRITE = "NO_ARTIFACT_WRITE"
NO_LIVE_PROVIDER_CALL = "NO_LIVE_PROVIDER_CALL"
NO_GITHUB_ACTION = "NO_GITHUB_ACTION"
NO_CANONICAL_PROMOTION = "NO_CANONICAL_PROMOTION"
PROPOSAL_OR_RECORD_ONLY = "PROPOSAL_OR_RECORD_ONLY"

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT_HEX = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_UNSAFE_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")


class PolicyProfileError(ValueError):
    """Raised when a Policy-H0A profile or evaluation input is malformed."""


class PolicyProfileName(str, Enum):
    DENY_ALL = "DENY_ALL"
    READ_ONLY = "READ_ONLY"
    PROPOSE_ONLY = "PROPOSE_ONLY"
    PROVIDER_REVIEW_ONLY = "PROVIDER_REVIEW_ONLY"
    HUMAN_APPROVAL_RECORD_ONLY = "HUMAN_APPROVAL_RECORD_ONLY"


class PolicyActionType(str, Enum):
    READ_CONTEXT = "READ_CONTEXT"
    READ_REPO_METADATA = "READ_REPO_METADATA"
    BUILD_PROVIDER_FLOW_AUDIT_RECORD = "BUILD_PROVIDER_FLOW_AUDIT_RECORD"
    BUILD_HUMAN_APPROVAL_RECORD = "BUILD_HUMAN_APPROVAL_RECORD"
    BUILD_ACTION_PROPOSAL = "BUILD_ACTION_PROPOSAL"
    BUILD_PATCH_PROPOSAL = "BUILD_PATCH_PROPOSAL"
    CALL_LIVE_PROVIDER = "CALL_LIVE_PROVIDER"
    WRITE_FILE = "WRITE_FILE"
    WRITE_ARTIFACT = "WRITE_ARTIFACT"
    RUN_SHELL_COMMAND = "RUN_SHELL_COMMAND"
    RUN_TEST_COMMAND = "RUN_TEST_COMMAND"
    GIT_COMMIT = "GIT_COMMIT"
    GITHUB_PUSH = "GITHUB_PUSH"
    GITHUB_PR = "GITHUB_PR"
    PROMOTE_CANONICAL_KNOWLEDGE = "PROMOTE_CANONICAL_KNOWLEDGE"


class PolicyDecision(str, Enum):
    ALLOW_PROPOSAL_ONLY = "ALLOW_PROPOSAL_ONLY"
    ALLOW_RECORD_ONLY = "ALLOW_RECORD_ONLY"
    DENY = "DENY"
    REQUIRES_FUTURE_MILESTONE = "REQUIRES_FUTURE_MILESTONE"


class PolicyBoundary(str, Enum):
    DEFAULT_DENY = DEFAULT_DENY
    NO_EXECUTION = NO_EXECUTION
    NO_ARTIFACT_WRITE = NO_ARTIFACT_WRITE
    NO_LIVE_PROVIDER_CALL = NO_LIVE_PROVIDER_CALL
    NO_GITHUB_ACTION = NO_GITHUB_ACTION
    NO_CANONICAL_PROMOTION = NO_CANONICAL_PROMOTION
    PROPOSAL_OR_RECORD_ONLY = PROPOSAL_OR_RECORD_ONLY


_READ_ACTIONS = frozenset(
    {
        PolicyActionType.READ_CONTEXT,
        PolicyActionType.READ_REPO_METADATA,
    }
)
_PROPOSAL_ACTIONS = frozenset(
    {
        PolicyActionType.BUILD_ACTION_PROPOSAL,
        PolicyActionType.BUILD_PATCH_PROPOSAL,
    }
)
_RECORD_ACTIONS = frozenset(
    {
        PolicyActionType.BUILD_PROVIDER_FLOW_AUDIT_RECORD,
        PolicyActionType.BUILD_HUMAN_APPROVAL_RECORD,
    }
)
_FUTURE_CAPABILITY_ACTIONS = frozenset(
    {
        PolicyActionType.CALL_LIVE_PROVIDER,
        PolicyActionType.WRITE_FILE,
        PolicyActionType.WRITE_ARTIFACT,
        PolicyActionType.RUN_SHELL_COMMAND,
        PolicyActionType.RUN_TEST_COMMAND,
        PolicyActionType.GIT_COMMIT,
        PolicyActionType.GITHUB_PUSH,
        PolicyActionType.GITHUB_PR,
        PolicyActionType.PROMOTE_CANONICAL_KNOWLEDGE,
    }
)
_PROFILE_ALLOWED_ACTIONS = {
    PolicyProfileName.DENY_ALL: frozenset(),
    PolicyProfileName.READ_ONLY: _READ_ACTIONS,
    PolicyProfileName.PROPOSE_ONLY: _READ_ACTIONS | _PROPOSAL_ACTIONS,
    PolicyProfileName.PROVIDER_REVIEW_ONLY: frozenset(
        {PolicyActionType.BUILD_PROVIDER_FLOW_AUDIT_RECORD}
    ),
    PolicyProfileName.HUMAN_APPROVAL_RECORD_ONLY: frozenset(
        {PolicyActionType.BUILD_HUMAN_APPROVAL_RECORD}
    ),
}


@dataclass(frozen=True)
class PolicyProfile:
    label: str
    schema_version: str
    profile_name: PolicyProfileName
    created_at_utc: str | None
    default_decision: PolicyDecision
    allowed_action_types: tuple[PolicyActionType, ...]
    denied_action_types: tuple[PolicyActionType, ...]
    allowed_scope: tuple[str, ...]
    forbidden_scope: tuple[str, ...]
    policy_boundaries: tuple[PolicyBoundary, ...]
    policy_hash: str
    execution_authority: bool
    artifact_write_authority: bool
    provider_live_call_authority: bool
    github_authority: bool
    canonical_promotion_authority: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "schema_version": self.schema_version,
            "profile_name": self.profile_name.value,
            "created_at_utc": self.created_at_utc,
            "default_decision": self.default_decision.value,
            "allowed_action_types": [item.value for item in self.allowed_action_types],
            "denied_action_types": [item.value for item in self.denied_action_types],
            "allowed_scope": list(self.allowed_scope),
            "forbidden_scope": list(self.forbidden_scope),
            "policy_boundaries": [item.value for item in self.policy_boundaries],
            "policy_hash": self.policy_hash,
            "execution_authority": self.execution_authority,
            "artifact_write_authority": self.artifact_write_authority,
            "provider_live_call_authority": self.provider_live_call_authority,
            "github_authority": self.github_authority,
            "canonical_promotion_authority": self.canonical_promotion_authority,
        }


@dataclass(frozen=True)
class PolicyEvaluationResult:
    label: str
    schema_version: str
    profile_name: str
    action_type: str
    decision: PolicyDecision
    allowed: bool
    reason: str
    policy_hash: str
    repo_path: str
    branch: str
    head_commit: str
    target_paths: tuple[str, ...]
    target_hash: str | None
    approval_binding_hash: str | None
    provider_flow_audit_hash: str | None
    allowed_scope_match: bool
    forbidden_scope_match: bool
    proposal_only: bool
    record_only: bool
    future_milestone_required: bool
    default_deny: bool
    execution_authority: bool
    artifact_write_authority: bool
    provider_live_call_authority: bool
    github_authority: bool
    canonical_promotion_authority: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "schema_version": self.schema_version,
            "profile_name": self.profile_name,
            "action_type": self.action_type,
            "decision": self.decision.value,
            "allowed": self.allowed,
            "reason": self.reason,
            "policy_hash": self.policy_hash,
            "repo_path": self.repo_path,
            "branch": self.branch,
            "head_commit": self.head_commit,
            "target_paths": list(self.target_paths),
            "target_hash": self.target_hash,
            "approval_binding_hash": self.approval_binding_hash,
            "provider_flow_audit_hash": self.provider_flow_audit_hash,
            "allowed_scope_match": self.allowed_scope_match,
            "forbidden_scope_match": self.forbidden_scope_match,
            "proposal_only": self.proposal_only,
            "record_only": self.record_only,
            "future_milestone_required": self.future_milestone_required,
            "default_deny": self.default_deny,
            "execution_authority": self.execution_authority,
            "artifact_write_authority": self.artifact_write_authority,
            "provider_live_call_authority": self.provider_live_call_authority,
            "github_authority": self.github_authority,
            "canonical_promotion_authority": self.canonical_promotion_authority,
        }


def build_policy_profile(
    profile_name: PolicyProfileName | str,
    *,
    allowed_action_types: Iterable[PolicyActionType | str] | None = None,
    denied_action_types: Iterable[PolicyActionType | str] | None = None,
    allowed_scope: Iterable[str] = (),
    forbidden_scope: Iterable[str] = (),
    created_at_utc: str | None = None,
) -> PolicyProfile:
    name = _profile_name_or_default(profile_name)
    maximum_allowed = _PROFILE_ALLOWED_ACTIONS[name]
    allowed = (
        maximum_allowed
        if allowed_action_types is None
        else _action_values(allowed_action_types, "allowed_action_types")
    )
    if not allowed.issubset(maximum_allowed):
        raise PolicyProfileError(
            "H0A profile cannot allow actions outside its inert profile contract"
        )
    denied = (
        frozenset(PolicyActionType) - allowed
        if denied_action_types is None
        else _action_values(denied_action_types, "denied_action_types")
        | _FUTURE_CAPABILITY_ACTIONS
    )
    if allowed & denied:
        raise PolicyProfileError("allowed and denied action types must not overlap")
    scopes = _scope_values(allowed_scope, "allowed_scope")
    blocked_scopes = _scope_values(forbidden_scope, "forbidden_scope")
    timestamp = _optional_safe_text(created_at_utc, "created_at_utc", 128)
    boundaries = _required_boundaries()
    semantic = _semantic_policy(
        profile_name=name,
        allowed_action_types=allowed,
        denied_action_types=denied,
        allowed_scope=scopes,
        forbidden_scope=blocked_scopes,
        policy_boundaries=boundaries,
    )
    policy_hash = _stable_hash(semantic)
    profile = PolicyProfile(
        label=AOIA_POLICY_PROFILE,
        schema_version=POLICY_SCHEMA_VERSION,
        profile_name=name,
        created_at_utc=timestamp,
        default_decision=PolicyDecision.DENY,
        allowed_action_types=_sorted_actions(allowed),
        denied_action_types=_sorted_actions(denied),
        allowed_scope=scopes,
        forbidden_scope=blocked_scopes,
        policy_boundaries=boundaries,
        policy_hash=policy_hash,
        execution_authority=False,
        artifact_write_authority=False,
        provider_live_call_authority=False,
        github_authority=False,
        canonical_promotion_authority=False,
    )
    _validate_profile(profile)
    return profile


def evaluate_policy_action(
    *,
    profile_name: PolicyProfile | PolicyProfileName | str,
    action_type: PolicyActionType | str,
    repo_path: str,
    branch: str,
    head_commit: str,
    target_paths: Iterable[str] = (),
    target_hash: str | None = None,
    approval_binding_hash: str | None = None,
    provider_flow_audit_hash: str | None = None,
) -> PolicyEvaluationResult:
    repo = _absolute_path(repo_path, "repo_path")
    branch_value = _required_safe_text(branch, "branch", 512)
    head = _git_commit_hash(head_commit)
    paths = _target_paths(target_paths, repo)
    target_digest = _optional_sha256(target_hash, "target_hash")
    approval_digest = _optional_sha256(
        approval_binding_hash,
        "approval_binding_hash",
    )
    audit_digest = _optional_sha256(
        provider_flow_audit_hash,
        "provider_flow_audit_hash",
    )
    profile, requested_profile = _resolve_profile(profile_name)
    action, requested_action = _resolve_action(action_type)

    if profile is None:
        fallback = build_policy_profile(PolicyProfileName.DENY_ALL)
        return _evaluation_result(
            profile=fallback,
            profile_name=requested_profile,
            action_type=requested_action,
            decision=PolicyDecision.DENY,
            reason="unknown policy profile defaults to deny",
            repo_path=repo,
            branch=branch_value,
            head_commit=head,
            target_paths=paths,
            target_hash=target_digest,
            approval_binding_hash=approval_digest,
            provider_flow_audit_hash=audit_digest,
            allowed_scope_match=False,
            forbidden_scope_match=False,
        )
    _validate_profile(profile)
    if action is None:
        return _evaluation_result(
            profile=profile,
            profile_name=profile.profile_name.value,
            action_type=requested_action,
            decision=PolicyDecision.DENY,
            reason="unknown action type defaults to deny",
            repo_path=repo,
            branch=branch_value,
            head_commit=head,
            target_paths=paths,
            target_hash=target_digest,
            approval_binding_hash=approval_digest,
            provider_flow_audit_hash=audit_digest,
            allowed_scope_match=False,
            forbidden_scope_match=False,
        )

    allowed_match = _all_paths_allowed(paths, profile.allowed_scope)
    forbidden_match = _any_path_forbidden(paths, profile.forbidden_scope)
    if forbidden_match:
        decision = PolicyDecision.DENY
        reason = "target path matches forbidden scope"
    elif not allowed_match:
        decision = PolicyDecision.DENY
        reason = "target path is outside allowed scope"
    elif action in profile.allowed_action_types:
        decision = _allowed_decision(action)
        reason = "action is explicitly allowed only as inert read/proposal/record data"
    elif (
        action in _FUTURE_CAPABILITY_ACTIONS
        and profile.profile_name is not PolicyProfileName.DENY_ALL
    ):
        decision = PolicyDecision.REQUIRES_FUTURE_MILESTONE
        reason = "no execution-capable policy exists in H0A"
    else:
        decision = PolicyDecision.DENY
        reason = "action is not explicitly allowed by the default-deny profile"
    return _evaluation_result(
        profile=profile,
        profile_name=profile.profile_name.value,
        action_type=action.value,
        decision=decision,
        reason=reason,
        repo_path=repo,
        branch=branch_value,
        head_commit=head,
        target_paths=paths,
        target_hash=target_digest,
        approval_binding_hash=approval_digest,
        provider_flow_audit_hash=audit_digest,
        allowed_scope_match=allowed_match,
        forbidden_scope_match=forbidden_match,
    )


def _evaluation_result(
    *,
    profile: PolicyProfile,
    profile_name: str,
    action_type: str,
    decision: PolicyDecision,
    reason: str,
    repo_path: str,
    branch: str,
    head_commit: str,
    target_paths: tuple[str, ...],
    target_hash: str | None,
    approval_binding_hash: str | None,
    provider_flow_audit_hash: str | None,
    allowed_scope_match: bool,
    forbidden_scope_match: bool,
) -> PolicyEvaluationResult:
    allowed = decision in {
        PolicyDecision.ALLOW_PROPOSAL_ONLY,
        PolicyDecision.ALLOW_RECORD_ONLY,
    }
    return PolicyEvaluationResult(
        label=AOIA_POLICY_EVALUATION,
        schema_version=POLICY_SCHEMA_VERSION,
        profile_name=profile_name,
        action_type=action_type,
        decision=decision,
        allowed=allowed,
        reason=reason,
        policy_hash=profile.policy_hash,
        repo_path=repo_path,
        branch=branch,
        head_commit=head_commit,
        target_paths=target_paths,
        target_hash=target_hash,
        approval_binding_hash=approval_binding_hash,
        provider_flow_audit_hash=provider_flow_audit_hash,
        allowed_scope_match=allowed_scope_match,
        forbidden_scope_match=forbidden_scope_match,
        proposal_only=decision is PolicyDecision.ALLOW_PROPOSAL_ONLY,
        record_only=decision is PolicyDecision.ALLOW_RECORD_ONLY,
        future_milestone_required=(
            decision is PolicyDecision.REQUIRES_FUTURE_MILESTONE
        ),
        default_deny=not allowed,
        execution_authority=False,
        artifact_write_authority=False,
        provider_live_call_authority=False,
        github_authority=False,
        canonical_promotion_authority=False,
    )


def _validate_profile(profile: PolicyProfile) -> None:
    if not isinstance(profile, PolicyProfile):
        raise PolicyProfileError("profile must be a PolicyProfile")
    if (
        not isinstance(profile.profile_name, PolicyProfileName)
        or any(
            not isinstance(item, PolicyBoundary)
            for item in profile.policy_boundaries
        )
        or profile.label != AOIA_POLICY_PROFILE
        or profile.schema_version != POLICY_SCHEMA_VERSION
        or profile.default_decision is not PolicyDecision.DENY
        or tuple(profile.policy_boundaries) != _required_boundaries()
        or profile.execution_authority is not False
        or profile.artifact_write_authority is not False
        or profile.provider_live_call_authority is not False
        or profile.github_authority is not False
        or profile.canonical_promotion_authority is not False
    ):
        raise PolicyProfileError("policy profile violates the H0A no-authority boundary")
    if (
        profile.created_at_utc is not None
        and _optional_safe_text(profile.created_at_utc, "created_at_utc", 128)
        != profile.created_at_utc
    ):
        raise PolicyProfileError("profile timestamp metadata is not canonical")
    allowed = frozenset(profile.allowed_action_types)
    denied = frozenset(profile.denied_action_types)
    if (
        any(not isinstance(item, PolicyActionType) for item in allowed | denied)
        or not allowed.issubset(_PROFILE_ALLOWED_ACTIONS[profile.profile_name])
        or allowed & denied
        or not _FUTURE_CAPABILITY_ACTIONS.issubset(denied)
    ):
        raise PolicyProfileError("policy profile action sets violate default deny")
    if profile.allowed_scope != _scope_values(profile.allowed_scope, "allowed_scope"):
        raise PolicyProfileError("allowed scope is not canonical")
    if profile.forbidden_scope != _scope_values(
        profile.forbidden_scope,
        "forbidden_scope",
    ):
        raise PolicyProfileError("forbidden scope is not canonical")
    semantic = _semantic_policy(
        profile_name=profile.profile_name,
        allowed_action_types=allowed,
        denied_action_types=denied,
        allowed_scope=profile.allowed_scope,
        forbidden_scope=profile.forbidden_scope,
        policy_boundaries=profile.policy_boundaries,
    )
    if profile.policy_hash != _stable_hash(semantic):
        raise PolicyProfileError("policy hash mismatch")


def _semantic_policy(
    *,
    profile_name: PolicyProfileName,
    allowed_action_types: Iterable[PolicyActionType],
    denied_action_types: Iterable[PolicyActionType],
    allowed_scope: Iterable[str],
    forbidden_scope: Iterable[str],
    policy_boundaries: Iterable[PolicyBoundary],
) -> dict[str, Any]:
    return {
        "label": AOIA_POLICY_PROFILE,
        "schema_version": POLICY_SCHEMA_VERSION,
        "profile_name": profile_name.value,
        "default_decision": PolicyDecision.DENY.value,
        "allowed_action_types": [
            item.value for item in _sorted_actions(allowed_action_types)
        ],
        "denied_action_types": [
            item.value for item in _sorted_actions(denied_action_types)
        ],
        "allowed_scope": list(allowed_scope),
        "forbidden_scope": list(forbidden_scope),
        "policy_boundaries": [item.value for item in policy_boundaries],
    }


def _profile_name_or_default(value: PolicyProfileName | str) -> PolicyProfileName:
    if isinstance(value, PolicyProfileName):
        return value
    if not isinstance(value, str) or not value.strip():
        raise PolicyProfileError("profile_name must be a non-empty string")
    try:
        return PolicyProfileName(value)
    except ValueError:
        return PolicyProfileName.DENY_ALL


def _resolve_profile(
    value: PolicyProfile | PolicyProfileName | str,
) -> tuple[PolicyProfile | None, str]:
    if isinstance(value, PolicyProfile):
        _validate_profile(value)
        return value, value.profile_name.value
    requested = _required_safe_text(value, "profile_name", 128)
    try:
        name = PolicyProfileName(requested)
    except ValueError:
        return None, requested
    return build_policy_profile(name), requested


def _resolve_action(
    value: PolicyActionType | str,
) -> tuple[PolicyActionType | None, str]:
    if isinstance(value, PolicyActionType):
        return value, value.value
    requested = _required_safe_text(value, "action_type", 128)
    try:
        return PolicyActionType(requested), requested
    except ValueError:
        return None, requested


def _action_values(
    values: Iterable[PolicyActionType | str],
    name: str,
) -> frozenset[PolicyActionType]:
    if isinstance(values, (str, bytes)):
        raise PolicyProfileError(f"{name} must be an iterable of action types")
    try:
        candidates = tuple(values)
    except TypeError as error:
        raise PolicyProfileError(f"{name} must be iterable") from error
    result: set[PolicyActionType] = set()
    for value in candidates:
        try:
            result.add(PolicyActionType(value))
        except (TypeError, ValueError) as error:
            raise PolicyProfileError(f"{name} contains an unknown action") from error
    return frozenset(result)


def _scope_values(values: Iterable[str], name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise PolicyProfileError(f"{name} must be an iterable of paths")
    try:
        candidates = tuple(values)
    except TypeError as error:
        raise PolicyProfileError(f"{name} must be iterable") from error
    normalized: set[str] = set()
    for value in candidates:
        if value == "*":
            normalized.add(value)
            continue
        normalized.add(_absolute_path(value, name))
    return tuple(sorted(normalized))


def _target_paths(values: Iterable[str], repo_path: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise PolicyProfileError("target_paths must be an iterable of paths")
    try:
        candidates = tuple(values)
    except TypeError as error:
        raise PolicyProfileError("target_paths must be iterable") from error
    paths = []
    for value in candidates:
        text = _required_safe_text(value, "target_path", 4096)
        path = text if text.startswith("/") else posixpath.join(repo_path, text)
        paths.append(posixpath.normpath(path))
    return tuple(paths)


def _all_paths_allowed(paths: tuple[str, ...], scopes: tuple[str, ...]) -> bool:
    if not paths:
        return True
    return all(any(_path_matches(path, scope) for scope in scopes) for path in paths)


def _any_path_forbidden(paths: tuple[str, ...], scopes: tuple[str, ...]) -> bool:
    return any(_path_matches(path, scope) for path in paths for scope in scopes)


def _path_matches(path: str, scope: str) -> bool:
    if scope == "*":
        return True
    return path == scope or path.startswith(scope.rstrip("/") + "/")


def _allowed_decision(action: PolicyActionType) -> PolicyDecision:
    if action in _PROPOSAL_ACTIONS:
        return PolicyDecision.ALLOW_PROPOSAL_ONLY
    return PolicyDecision.ALLOW_RECORD_ONLY


def _required_boundaries() -> tuple[PolicyBoundary, ...]:
    return (
        PolicyBoundary.DEFAULT_DENY,
        PolicyBoundary.NO_EXECUTION,
        PolicyBoundary.NO_ARTIFACT_WRITE,
        PolicyBoundary.NO_LIVE_PROVIDER_CALL,
        PolicyBoundary.NO_GITHUB_ACTION,
        PolicyBoundary.NO_CANONICAL_PROMOTION,
        PolicyBoundary.PROPOSAL_OR_RECORD_ONLY,
    )


def _sorted_actions(
    values: Iterable[PolicyActionType],
) -> tuple[PolicyActionType, ...]:
    return tuple(sorted(values, key=lambda item: item.value))


def _absolute_path(value: str, name: str) -> str:
    text = _required_safe_text(value, name, 4096)
    if not text.startswith("/"):
        raise PolicyProfileError(f"{name} must be an absolute path")
    return posixpath.normpath(text)


def _required_safe_text(value: Any, name: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise PolicyProfileError(f"{name} must be a string")
    text = value.strip()
    if not text or len(text) > max_length or _UNSAFE_CONTROL.search(text):
        raise PolicyProfileError(f"{name} is malformed")
    return text


def _optional_safe_text(value: str | None, name: str, max_length: int) -> str | None:
    if value is None:
        return None
    return _required_safe_text(value, name, max_length)


def _git_commit_hash(value: str) -> str:
    if not isinstance(value, str) or not _GIT_COMMIT_HEX.fullmatch(value):
        raise PolicyProfileError("head_commit must be a lowercase Git commit hash")
    return value


def _optional_sha256(value: str | None, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _SHA256_HEX.fullmatch(value):
        raise PolicyProfileError(f"{name} must be a lowercase SHA-256 hash")
    return value


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
