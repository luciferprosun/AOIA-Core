from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping

from runtime.git_ops.git_read import GIT_READ_BLOCKED, GIT_READ_ERROR, GIT_READ_READY, GitReadResult


GIT_GOVERNANCE_PASS = "PASS"
GIT_GOVERNANCE_NEEDS_REVIEW = "NEEDS_REVIEW"
GIT_GOVERNANCE_BLOCK = "BLOCK"

FINDING_SEVERITY_BLOCK = "BLOCK"
FINDING_SEVERITY_REVIEW = "NEEDS_REVIEW"

GIT_GOVERNANCE_POLICY_NAME = "AOIA_GIT_READ_ONLY_GOVERNANCE"
GIT_GOVERNANCE_POLICY_VERSION = "1A"

GIT_GOVERNANCE_BLOCKED_MISSING_INPUT = "GIT_GOVERNANCE_BLOCKED_MISSING_INPUT"
GIT_GOVERNANCE_BLOCKED_MALFORMED_INPUT = "GIT_GOVERNANCE_BLOCKED_MALFORMED_INPUT"
GIT_GOVERNANCE_BLOCKED_GIT_READ_STATUS = "GIT_GOVERNANCE_BLOCKED_GIT_READ_STATUS"
GIT_GOVERNANCE_BLOCKED_MISSING_HASH = "GIT_GOVERNANCE_BLOCKED_MISSING_HASH"
GIT_GOVERNANCE_BLOCKED_MISSING_REPO_ROOT = "GIT_GOVERNANCE_BLOCKED_MISSING_REPO_ROOT"
GIT_GOVERNANCE_BLOCKED_MISSING_HEAD = "GIT_GOVERNANCE_BLOCKED_MISSING_HEAD"
GIT_GOVERNANCE_BLOCKED_DETACHED_HEAD = "GIT_GOVERNANCE_BLOCKED_DETACHED_HEAD"
GIT_GOVERNANCE_BLOCKED_MISSING_BRANCH = "GIT_GOVERNANCE_BLOCKED_MISSING_BRANCH"
GIT_GOVERNANCE_BLOCKED_BRANCH_MISMATCH = "GIT_GOVERNANCE_BLOCKED_BRANCH_MISMATCH"
GIT_GOVERNANCE_BLOCKED_BRANCH_NOT_ALLOWED = "GIT_GOVERNANCE_BLOCKED_BRANCH_NOT_ALLOWED"
GIT_GOVERNANCE_BLOCKED_UNSAFE_REPO_ROOT = "GIT_GOVERNANCE_BLOCKED_UNSAFE_REPO_ROOT"
GIT_GOVERNANCE_BLOCKED_AUTHORITY_CLAIM = "GIT_GOVERNANCE_BLOCKED_AUTHORITY_CLAIM"
GIT_GOVERNANCE_BLOCKED_COMMAND_EVIDENCE = "GIT_GOVERNANCE_BLOCKED_COMMAND_EVIDENCE"
GIT_GOVERNANCE_BLOCKED_OUTPUT_BOUND = "GIT_GOVERNANCE_BLOCKED_OUTPUT_BOUND"
GIT_GOVERNANCE_BLOCKED_TIMEOUT = "GIT_GOVERNANCE_BLOCKED_TIMEOUT"
GIT_GOVERNANCE_BLOCKED_SANITIZER = "GIT_GOVERNANCE_BLOCKED_SANITIZER"
GIT_GOVERNANCE_BLOCKED_RAW_COMMAND_TEXT = "GIT_GOVERNANCE_BLOCKED_RAW_COMMAND_TEXT"
GIT_GOVERNANCE_BLOCKED_DIRTY_WORKTREE = "GIT_GOVERNANCE_BLOCKED_DIRTY_WORKTREE"
GIT_GOVERNANCE_BLOCKED_PROTECTED_PATH = "GIT_GOVERNANCE_BLOCKED_PROTECTED_PATH"
GIT_GOVERNANCE_BLOCKED_UNSAFE_PATH = "GIT_GOVERNANCE_BLOCKED_UNSAFE_PATH"
GIT_GOVERNANCE_REVIEW_DIRTY_WORKTREE = "GIT_GOVERNANCE_REVIEW_DIRTY_WORKTREE"
GIT_GOVERNANCE_REVIEW_STAGED_PATHS = "GIT_GOVERNANCE_REVIEW_STAGED_PATHS"
GIT_GOVERNANCE_REVIEW_UNSTAGED_PATHS = "GIT_GOVERNANCE_REVIEW_UNSTAGED_PATHS"
GIT_GOVERNANCE_REVIEW_UNTRACKED_PATHS = "GIT_GOVERNANCE_REVIEW_UNTRACKED_PATHS"
GIT_GOVERNANCE_REVIEW_GIT_ATTRIBUTE_RISK = "GIT_GOVERNANCE_REVIEW_GIT_ATTRIBUTE_RISK"
GIT_GOVERNANCE_REVIEW_BRANCH_NOT_ALLOWED = "GIT_GOVERNANCE_REVIEW_BRANCH_NOT_ALLOWED"
GIT_GOVERNANCE_REVIEW_LARGE_PATH_LIST = "GIT_GOVERNANCE_REVIEW_LARGE_PATH_LIST"
GIT_GOVERNANCE_PASS_METADATA_ONLY = "GIT_GOVERNANCE_PASS_METADATA_ONLY"

_SCHEMA_VERSION = "AOIA_GIT_READ_ONLY_GOVERNANCE_1A"
_DEFAULT_PROTECTED_PATH_PREFIXES = (
    "runtime/safety/",
    "runtime/control_write.py",
    "runtime/human_decision_gated_artifact_write.py",
    "runtime/patches/controlled_patch_apply.py",
    "runtime/patches/post_patch_controlled_test_integration.py",
    "runtime/git_ops/",
    "tests/test_static_capability_boundary_1a.py",
)
_AUTHORITY_FIELDS = (
    "can_approve",
    "can_write",
    "can_execute",
    "can_commit",
    "can_push",
    "can_call_provider",
    "can_change_gate",
    "git_write_authority_granted",
    "git_commit_authority_granted",
    "git_push_authority_granted",
    "provider_authority_granted",
    "execution_authority_granted",
)
_GIT_READ_AUTHORITY_FIELDS = (
    "can_approve",
    "can_write",
    "can_execute",
    "can_commit",
    "can_push",
    "can_call_provider",
    "can_change_gate",
    "git_write_authority_granted",
    "git_commit_authority_granted",
    "git_push_authority_granted",
    "provider_authority_granted",
    "execution_authority_granted",
    "write_authority_granted",
)
_RAW_COMMAND_KEYS = ("command_text", "raw_command", "raw_args", "argv", "command")
_HEX = frozenset("0123456789abcdef")


@dataclass(frozen=True)
class GitGovernancePolicy:
    policy_name: str = GIT_GOVERNANCE_POLICY_NAME
    policy_version: str = GIT_GOVERNANCE_POLICY_VERSION
    expected_branch: str | None = None
    allowed_branches: tuple[str, ...] = ()
    review_branch_not_allowed: bool = False
    require_clean_worktree: bool = True
    block_detached_head: bool = True
    block_protected_path_changes: bool = True
    protected_path_prefixes: tuple[str, ...] = _DEFAULT_PROTECTED_PATH_PREFIXES
    review_untracked: bool = True
    review_staged: bool = True
    review_unstaged: bool = True
    large_path_list_threshold: int = 200

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed_branches", tuple(sorted(set(self.allowed_branches))))
        object.__setattr__(self, "protected_path_prefixes", tuple(sorted(set(self.protected_path_prefixes))))

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_name": self.policy_name,
            "policy_version": self.policy_version,
            "expected_branch": self.expected_branch,
            "allowed_branches": self.allowed_branches,
            "review_branch_not_allowed": self.review_branch_not_allowed,
            "require_clean_worktree": self.require_clean_worktree,
            "block_detached_head": self.block_detached_head,
            "block_protected_path_changes": self.block_protected_path_changes,
            "protected_path_prefixes": self.protected_path_prefixes,
            "review_untracked": self.review_untracked,
            "review_staged": self.review_staged,
            "review_unstaged": self.review_unstaged,
            "large_path_list_threshold": self.large_path_list_threshold,
        }


@dataclass(frozen=True)
class GitGovernanceFinding:
    severity: str
    reason_code: str
    message: str
    paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "paths", tuple(sorted(set(self.paths))))

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "reason_code": self.reason_code,
            "message": self.message,
            "paths": self.paths,
        }


@dataclass(frozen=True)
class GitGovernanceResult:
    status: str
    governance_hash: str
    input_git_read_hash: str | None
    policy_name: str
    policy_version: str
    findings: tuple[GitGovernanceFinding, ...]
    reason_codes: tuple[str, ...]
    risk_flags: tuple[str, ...]
    can_approve: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    git_write_authority_granted: bool = False
    git_commit_authority_granted: bool = False
    git_push_authority_granted: bool = False
    provider_authority_granted: bool = False
    execution_authority_granted: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "findings", _sorted_findings(self.findings))
        object.__setattr__(self, "reason_codes", tuple(sorted(set(self.reason_codes))))
        object.__setattr__(self, "risk_flags", tuple(sorted(set(self.risk_flags))))
        for field_name in _AUTHORITY_FIELDS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "governance_hash": self.governance_hash,
            "input_git_read_hash": self.input_git_read_hash,
            "policy_name": self.policy_name,
            "policy_version": self.policy_version,
            "findings": tuple(finding.to_dict() for finding in self.findings),
            "reason_codes": self.reason_codes,
            "risk_flags": self.risk_flags,
            "can_approve": self.can_approve,
            "can_write": self.can_write,
            "can_execute": self.can_execute,
            "can_commit": self.can_commit,
            "can_push": self.can_push,
            "can_call_provider": self.can_call_provider,
            "can_change_gate": self.can_change_gate,
            "git_write_authority_granted": self.git_write_authority_granted,
            "git_commit_authority_granted": self.git_commit_authority_granted,
            "git_push_authority_granted": self.git_push_authority_granted,
            "provider_authority_granted": self.provider_authority_granted,
            "execution_authority_granted": self.execution_authority_granted,
        }


def evaluate_git_read_governance(
    git_read_result: GitReadResult | Mapping[str, Any] | Any,
    policy: GitGovernancePolicy | None = None,
) -> GitGovernanceResult:
    active_policy = policy or GitGovernancePolicy()
    mapping, malformed_reason = _coerce_git_read_mapping(git_read_result)
    if malformed_reason:
        return _governance_result(active_policy, None, (malformed_reason,), (malformed_reason,), ())

    findings: list[GitGovernanceFinding] = []
    input_hash = _text(mapping.get("git_read_hash"))
    status = _text(mapping.get("status"))
    repo_root = _text(mapping.get("repo_root"))
    head_sha = _text(mapping.get("head_sha"))
    branch_name = _text(mapping.get("branch_name"))
    detached_head = mapping.get("detached_head")
    clean = mapping.get("clean")
    staged_paths = _safe_paths(mapping.get("staged_paths"))
    unstaged_paths = _safe_paths(mapping.get("unstaged_paths"))
    untracked_paths = _safe_paths(mapping.get("untracked_paths"))
    all_paths = tuple(sorted(set((*staged_paths, *unstaged_paths, *untracked_paths))))

    if status in (GIT_READ_BLOCKED, GIT_READ_ERROR):
        findings.append(_finding(FINDING_SEVERITY_BLOCK, GIT_GOVERNANCE_BLOCKED_GIT_READ_STATUS, "Git read result status is not ready."))
    elif status != GIT_READ_READY:
        findings.append(_finding(FINDING_SEVERITY_BLOCK, GIT_GOVERNANCE_BLOCKED_MALFORMED_INPUT, "Git read result has an unknown status."))
    if not _hash_like(input_hash):
        findings.append(_finding(FINDING_SEVERITY_BLOCK, GIT_GOVERNANCE_BLOCKED_MISSING_HASH, "Git read hash is missing or malformed."))
    if not repo_root:
        findings.append(_finding(FINDING_SEVERITY_BLOCK, GIT_GOVERNANCE_BLOCKED_MISSING_REPO_ROOT, "Repository root evidence is missing."))
    elif _unsafe_repo_root(repo_root):
        findings.append(_finding(FINDING_SEVERITY_BLOCK, GIT_GOVERNANCE_BLOCKED_UNSAFE_REPO_ROOT, "Repository root evidence is unsafe."))
    if not _hash_like(head_sha, allow_sha1=True):
        findings.append(_finding(FINDING_SEVERITY_BLOCK, GIT_GOVERNANCE_BLOCKED_MISSING_HEAD, "HEAD SHA evidence is missing or malformed."))
    if detached_head is True and active_policy.block_detached_head:
        findings.append(_finding(FINDING_SEVERITY_BLOCK, GIT_GOVERNANCE_BLOCKED_DETACHED_HEAD, "Detached HEAD is blocked by policy."))
    if detached_head is not True and not branch_name:
        findings.append(_finding(FINDING_SEVERITY_BLOCK, GIT_GOVERNANCE_BLOCKED_MISSING_BRANCH, "Branch name is required for non-detached HEAD."))
    if active_policy.expected_branch is not None and branch_name != active_policy.expected_branch:
        findings.append(_finding(FINDING_SEVERITY_BLOCK, GIT_GOVERNANCE_BLOCKED_BRANCH_MISMATCH, "Branch does not match expected branch."))
    if active_policy.allowed_branches and branch_name not in active_policy.allowed_branches:
        severity = FINDING_SEVERITY_REVIEW if active_policy.review_branch_not_allowed else FINDING_SEVERITY_BLOCK
        code = GIT_GOVERNANCE_REVIEW_BRANCH_NOT_ALLOWED if active_policy.review_branch_not_allowed else GIT_GOVERNANCE_BLOCKED_BRANCH_NOT_ALLOWED
        findings.append(_finding(severity, code, "Branch is outside the configured allowed branch list."))
    if _authority_claim_present(mapping):
        findings.append(_finding(FINDING_SEVERITY_BLOCK, GIT_GOVERNANCE_BLOCKED_AUTHORITY_CLAIM, "Git read evidence contains authority-like claims."))
    findings.extend(_command_evidence_findings(mapping.get("command_evidence")))
    findings.extend(_path_findings(all_paths, active_policy))
    findings.extend(_worktree_findings(clean, staged_paths, unstaged_paths, untracked_paths, active_policy))

    sorted_findings = _sorted_findings(findings)
    block_findings = tuple(finding for finding in sorted_findings if finding.severity == FINDING_SEVERITY_BLOCK)
    review_findings = tuple(finding for finding in sorted_findings if finding.severity == FINDING_SEVERITY_REVIEW)
    if block_findings:
        status_out = GIT_GOVERNANCE_BLOCK
    elif review_findings:
        status_out = GIT_GOVERNANCE_NEEDS_REVIEW
    else:
        status_out = GIT_GOVERNANCE_PASS
        sorted_findings = ()
    reason_codes = tuple(finding.reason_code for finding in sorted_findings) or (GIT_GOVERNANCE_PASS_METADATA_ONLY,)
    risk_flags = tuple(finding.reason_code for finding in sorted_findings)
    return _result(
        status=status_out,
        input_git_read_hash=input_hash,
        policy=active_policy,
        findings=sorted_findings,
        reason_codes=reason_codes,
        risk_flags=risk_flags,
    )


def canonical_git_governance_json(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_git_governance_hash(value: Any) -> str:
    return hashlib.sha256(canonical_git_governance_json(value).encode("utf-8")).hexdigest()


def _governance_result(
    policy: GitGovernancePolicy,
    input_hash: str | None,
    reason_codes: tuple[str, ...],
    risk_flags: tuple[str, ...],
    findings: tuple[GitGovernanceFinding, ...],
) -> GitGovernanceResult:
    return _result(
        status=GIT_GOVERNANCE_BLOCK,
        input_git_read_hash=input_hash,
        policy=policy,
        findings=findings or tuple(_finding(FINDING_SEVERITY_BLOCK, code, "Git governance input is blocked.") for code in reason_codes),
        reason_codes=reason_codes,
        risk_flags=risk_flags,
    )


def _result(
    *,
    status: str,
    input_git_read_hash: str | None,
    policy: GitGovernancePolicy,
    findings: tuple[GitGovernanceFinding, ...],
    reason_codes: tuple[str, ...],
    risk_flags: tuple[str, ...],
) -> GitGovernanceResult:
    material = {
        "schema_version": _SCHEMA_VERSION,
        "status": status,
        "input_git_read_hash": input_git_read_hash,
        "policy": policy.to_dict(),
        "findings": tuple(finding.to_dict() for finding in _sorted_findings(findings)),
        "reason_codes": tuple(sorted(set(reason_codes))),
        "risk_flags": tuple(sorted(set(risk_flags))),
        "authority": {field_name: False for field_name in _AUTHORITY_FIELDS},
    }
    return GitGovernanceResult(
        status=status,
        governance_hash=compute_git_governance_hash(material),
        input_git_read_hash=input_git_read_hash,
        policy_name=policy.policy_name,
        policy_version=policy.policy_version,
        findings=findings,
        reason_codes=reason_codes,
        risk_flags=risk_flags,
    )


def _coerce_git_read_mapping(value: GitReadResult | Mapping[str, Any] | Any) -> tuple[dict[str, Any], str | None]:
    if value is None:
        return {}, GIT_GOVERNANCE_BLOCKED_MISSING_INPUT
    if isinstance(value, Mapping):
        candidate = dict(value)
    elif hasattr(value, "to_dict"):
        data = value.to_dict()
        candidate = dict(data) if isinstance(data, Mapping) else {}
    else:
        return {}, GIT_GOVERNANCE_BLOCKED_MALFORMED_INPUT
    required = {"status", "git_read_hash", "repo_root", "head_sha", "detached_head", "clean", "reason_codes"}
    if not required.issubset(candidate):
        return {}, GIT_GOVERNANCE_BLOCKED_MALFORMED_INPUT
    return candidate, None


def _command_evidence_findings(value: Any) -> tuple[GitGovernanceFinding, ...]:
    if value is None:
        return ()
    if not isinstance(value, (tuple, list)):
        return (_finding(FINDING_SEVERITY_BLOCK, GIT_GOVERNANCE_BLOCKED_COMMAND_EVIDENCE, "Command evidence is malformed."),)
    findings: list[GitGovernanceFinding] = []
    for item in value:
        evidence = _mapping(item)
        if evidence is None:
            findings.append(_finding(FINDING_SEVERITY_BLOCK, GIT_GOVERNANCE_BLOCKED_COMMAND_EVIDENCE, "Command evidence item is malformed."))
            continue
        if evidence.get("status") not in (None, "PASS"):
            findings.append(_finding(FINDING_SEVERITY_BLOCK, GIT_GOVERNANCE_BLOCKED_COMMAND_EVIDENCE, "Git read command evidence did not pass."))
        if evidence.get("timeout_expired") is True:
            findings.append(_finding(FINDING_SEVERITY_BLOCK, GIT_GOVERNANCE_BLOCKED_TIMEOUT, "Git read command timed out."))
        if evidence.get("stdout_truncated") is True or evidence.get("stderr_truncated") is True:
            findings.append(_finding(FINDING_SEVERITY_BLOCK, GIT_GOVERNANCE_BLOCKED_OUTPUT_BOUND, "Git read command output exceeded configured bounds."))
        if any(_text(evidence.get(key)) for key in _RAW_COMMAND_KEYS):
            findings.append(_finding(FINDING_SEVERITY_BLOCK, GIT_GOVERNANCE_BLOCKED_RAW_COMMAND_TEXT, "Raw command text is exposed in Git read evidence."))
        if _authority_claim_present(evidence):
            findings.append(_finding(FINDING_SEVERITY_BLOCK, GIT_GOVERNANCE_BLOCKED_AUTHORITY_CLAIM, "Command evidence contains authority-like claims."))
        output = " ".join(_text(evidence.get(key)) or "" for key in ("stdout_preview", "stderr_preview"))
        if _looks_unsanitized(output) or evidence.get("sanitizer_failed") is True:
            findings.append(_finding(FINDING_SEVERITY_BLOCK, GIT_GOVERNANCE_BLOCKED_SANITIZER, "Git read command evidence appears unsanitized."))
    return tuple(findings)


def _path_findings(paths: tuple[str, ...], policy: GitGovernancePolicy) -> tuple[GitGovernanceFinding, ...]:
    findings: list[GitGovernanceFinding] = []
    unsafe = tuple(path for path in paths if _unsafe_path(path))
    if unsafe:
        findings.append(_finding(FINDING_SEVERITY_BLOCK, GIT_GOVERNANCE_BLOCKED_UNSAFE_PATH, "Git path evidence contains traversal or pathspec magic.", unsafe))
    if policy.block_protected_path_changes:
        protected = tuple(path for path in paths if _matches_protected_path(path, policy.protected_path_prefixes))
        if protected:
            findings.append(_finding(FINDING_SEVERITY_BLOCK, GIT_GOVERNANCE_BLOCKED_PROTECTED_PATH, "Protected control path changed.", protected))
    attribute_risk = tuple(path for path in paths if path in (".gitmodules", ".gitattributes") or path.endswith("/.gitmodules") or path.endswith("/.gitattributes"))
    if attribute_risk:
        findings.append(_finding(FINDING_SEVERITY_REVIEW, GIT_GOVERNANCE_REVIEW_GIT_ATTRIBUTE_RISK, "Git attribute/module metadata path requires review.", attribute_risk))
    if len(paths) > max(0, policy.large_path_list_threshold):
        findings.append(_finding(FINDING_SEVERITY_REVIEW, GIT_GOVERNANCE_REVIEW_LARGE_PATH_LIST, "Path list is unusually large."))
    return tuple(findings)


def _worktree_findings(
    clean: Any,
    staged_paths: tuple[str, ...],
    unstaged_paths: tuple[str, ...],
    untracked_paths: tuple[str, ...],
    policy: GitGovernancePolicy,
) -> tuple[GitGovernanceFinding, ...]:
    dirty = clean is False or staged_paths or unstaged_paths or untracked_paths
    if not dirty:
        return ()
    if policy.require_clean_worktree:
        return (_finding(FINDING_SEVERITY_BLOCK, GIT_GOVERNANCE_BLOCKED_DIRTY_WORKTREE, "Git working tree is not clean."),)
    findings: list[GitGovernanceFinding] = [_finding(FINDING_SEVERITY_REVIEW, GIT_GOVERNANCE_REVIEW_DIRTY_WORKTREE, "Dirty Git state is review-only evidence.")]
    if staged_paths and policy.review_staged:
        findings.append(_finding(FINDING_SEVERITY_REVIEW, GIT_GOVERNANCE_REVIEW_STAGED_PATHS, "Staged paths require review.", staged_paths))
    if unstaged_paths and policy.review_unstaged:
        findings.append(_finding(FINDING_SEVERITY_REVIEW, GIT_GOVERNANCE_REVIEW_UNSTAGED_PATHS, "Unstaged paths require review.", unstaged_paths))
    if untracked_paths and policy.review_untracked:
        findings.append(_finding(FINDING_SEVERITY_REVIEW, GIT_GOVERNANCE_REVIEW_UNTRACKED_PATHS, "Untracked paths require review.", untracked_paths))
    return tuple(findings)


def _finding(severity: str, reason_code: str, message: str, paths: tuple[str, ...] = ()) -> GitGovernanceFinding:
    return GitGovernanceFinding(severity=severity, reason_code=reason_code, message=message, paths=paths)


def _sorted_findings(findings: tuple[GitGovernanceFinding, ...] | list[GitGovernanceFinding]) -> tuple[GitGovernanceFinding, ...]:
    unique = {canonical_git_governance_json(finding.to_dict()): finding for finding in findings}
    return tuple(unique[key] for key in sorted(unique))


def _safe_paths(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (tuple, list)):
        return ()
    return tuple(sorted(set(str(item).strip() for item in value if isinstance(item, str) and item.strip())))


def _unsafe_path(path: str) -> bool:
    if "\x00" in path or "\\" in path:
        return True
    parts = PurePosixPath(path).parts
    if path.startswith("/") or any(part == ".." for part in parts):
        return True
    return any(marker in path for marker in (":(glob)", ":(attr)", ":(top)", ":/"))


def _matches_protected_path(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes)


def _unsafe_repo_root(repo_root: str) -> bool:
    if "\x00" in repo_root or not repo_root.startswith("/"):
        return True
    return any(part == ".." for part in PurePosixPath(repo_root).parts)


def _mapping(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        data = value.to_dict()
        if isinstance(data, Mapping):
            return dict(data)
    return None


def _authority_claim_present(mapping: Mapping[str, Any]) -> bool:
    return any(mapping.get(field_name) is True for field_name in _GIT_READ_AUTHORITY_FIELDS)


def _looks_unsanitized(value: str) -> bool:
    if "\x1b" in value or any(ord(char) < 32 and char not in "\n\t" for char in value):
        return True
    lowered = value.lower()
    if "ghp_" in value and "ghp_[REDACTED]" not in value:
        return True
    if "github_pat_" in value and "github_pat_[REDACTED]" not in value:
        return True
    if "access_token=" in lowered and "access_token=[redacted]" not in lowered:
        return True
    if "token=" in lowered and "token=[redacted]" not in lowered:
        return True
    return False


def _hash_like(value: str | None, allow_sha1: bool = False) -> bool:
    if value is None:
        return False
    lengths = (40, 64) if allow_sha1 else (64,)
    return len(value) in lengths and all(char in _HEX for char in value.lower())


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value
