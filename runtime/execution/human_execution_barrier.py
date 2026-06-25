from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


HUMAN_EXECUTION_BARRIER_SCHEMA_VERSION = "AOIA_HUMAN_EXECUTION_BARRIER_1A"
_MAX_SUMMARY_CHARS = 420


class HumanExecutionBarrierStatus(str, Enum):
    EXECUTION_BARRIER_PASSED = "EXECUTION_BARRIER_PASSED"
    BLOCKED_MISSING_HUMAN_DECISION = "BLOCKED_MISSING_HUMAN_DECISION"
    BLOCKED_REJECTED_BY_HUMAN = "BLOCKED_REJECTED_BY_HUMAN"
    BLOCKED_NON_HUMAN_DECISION_SOURCE = "BLOCKED_NON_HUMAN_DECISION_SOURCE"
    BLOCKED_UNTRUSTED_PROVIDER_SOURCE = "BLOCKED_UNTRUSTED_PROVIDER_SOURCE"
    BLOCKED_COMMAND_HASH_MISMATCH = "BLOCKED_COMMAND_HASH_MISMATCH"
    BLOCKED_TEST_RUNNER_HASH_MISMATCH = "BLOCKED_TEST_RUNNER_HASH_MISMATCH"
    BLOCKED_SANDBOX_HASH_MISMATCH = "BLOCKED_SANDBOX_HASH_MISMATCH"
    BLOCKED_POLICY_HASH_MISMATCH = "BLOCKED_POLICY_HASH_MISMATCH"
    BLOCKED_CONTROLLED_EXECUTION_REQUEST_HASH_MISMATCH = "BLOCKED_CONTROLLED_EXECUTION_REQUEST_HASH_MISMATCH"
    BLOCKED_INVALID_POLICY_STATUS = "BLOCKED_INVALID_POLICY_STATUS"
    BLOCKED_INVALID_TEST_RUNNER_STATUS = "BLOCKED_INVALID_TEST_RUNNER_STATUS"
    BLOCKED_INVALID_SANDBOX_STATUS = "BLOCKED_INVALID_SANDBOX_STATUS"
    BLOCKED_UNSAFE_RISK_FLAG = "BLOCKED_UNSAFE_RISK_FLAG"
    MALFORMED_REQUEST = "MALFORMED_REQUEST"
    INCONSISTENT_METADATA = "INCONSISTENT_METADATA"


class HumanExecutionBarrierFlag(str, Enum):
    HUMAN_EXECUTION_BARRIER_METADATA_ONLY = "HUMAN_EXECUTION_BARRIER_METADATA_ONLY"
    NO_EXECUTION = "NO_EXECUTION"
    NO_SUBPROCESS = "NO_SUBPROCESS"
    NO_SHELL = "NO_SHELL"
    NO_COMMAND_EXECUTION = "NO_COMMAND_EXECUTION"
    NO_BROWSER = "NO_BROWSER"
    NO_DOWNLOAD = "NO_DOWNLOAD"
    NO_FILE_READ = "NO_FILE_READ"
    NO_FILE_WRITE = "NO_FILE_WRITE"
    NO_NETWORK = "NO_NETWORK"
    NO_ENV_ACCESS = "NO_ENV_ACCESS"
    NO_API_KEY_ACCESS = "NO_API_KEY_ACCESS"
    NO_PROVIDER_CALL = "NO_PROVIDER_CALL"
    NO_APPROVAL_CREATED = "NO_APPROVAL_CREATED"
    NO_GATE_CHANGE = "NO_GATE_CHANGE"
    NO_CONTROL_WRITE_CHANGE = "NO_CONTROL_WRITE_CHANGE"
    HUMAN_DECISION_REQUIRED = "HUMAN_DECISION_REQUIRED"
    HUMAN_DECISION_PRESENT = "HUMAN_DECISION_PRESENT"
    HUMAN_DECISION_APPROVE = "HUMAN_DECISION_APPROVE"
    HUMAN_DECISION_REJECT = "HUMAN_DECISION_REJECT"
    NON_HUMAN_DECISION_SOURCE_BLOCKED = "NON_HUMAN_DECISION_SOURCE_BLOCKED"
    PROVIDER_OUTPUT_UNTRUSTED = "PROVIDER_OUTPUT_UNTRUSTED"
    COMMAND_HASH_BOUND = "COMMAND_HASH_BOUND"
    TEST_RUNNER_HASH_BOUND = "TEST_RUNNER_HASH_BOUND"
    SANDBOX_HASH_BOUND = "SANDBOX_HASH_BOUND"
    POLICY_HASH_BOUND = "POLICY_HASH_BOUND"
    CONTROLLED_EXECUTION_REQUEST_HASH_BOUND = "CONTROLLED_EXECUTION_REQUEST_HASH_BOUND"
    HASH_MISMATCH_BLOCKED = "HASH_MISMATCH_BLOCKED"
    UNSAFE_RISK_FLAG_BLOCKED = "UNSAFE_RISK_FLAG_BLOCKED"
    BARRIER_PASSED_FOR_CONTROLLED_TEST_RUNNER_ONLY = "BARRIER_PASSED_FOR_CONTROLLED_TEST_RUNNER_ONLY"
    ACTION_PROPOSAL_METADATA_ONLY = "ACTION_PROPOSAL_METADATA_ONLY"
    TOOL_CALL_PREVIEW_METADATA_ONLY = "TOOL_CALL_PREVIEW_METADATA_ONLY"
    INTENT_ROUTE_METADATA_ONLY = "INTENT_ROUTE_METADATA_ONLY"
    LOCAL_POLICY_METADATA_ONLY = "LOCAL_POLICY_METADATA_ONLY"
    TEST_RUNNER_METADATA_ONLY = "TEST_RUNNER_METADATA_ONLY"
    SANDBOX_ENVELOPE_METADATA_ONLY = "SANDBOX_ENVELOPE_METADATA_ONLY"
    CONTROLLED_EXECUTION_REQUEST_METADATA_ONLY = "CONTROLLED_EXECUTION_REQUEST_METADATA_ONLY"


class HumanDecisionVerdict(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    NEEDS_CHANGES = "NEEDS_CHANGES"
    UNKNOWN = "UNKNOWN"


class HumanDecisionSource(str, Enum):
    HUMAN_OPERATOR = "HUMAN_OPERATOR"
    LOCAL_OPERATOR = "LOCAL_OPERATOR"
    HUMAN_REVIEWER = "HUMAN_REVIEWER"
    PROVIDER_MODEL = "PROVIDER_MODEL"
    SYSTEM_POLICY = "SYSTEM_POLICY"
    UNKNOWN = "UNKNOWN"


class HumanExecutionSourceTrust(str, Enum):
    USER_SUPPLIED = "USER_SUPPLIED"
    HUMAN_OPERATOR = "HUMAN_OPERATOR"
    SYSTEM_METADATA = "SYSTEM_METADATA"
    CRITIC_METADATA = "CRITIC_METADATA"
    UNTRUSTED_PROVIDER_OUTPUT = "UNTRUSTED_PROVIDER_OUTPUT"
    PROVIDER_UNTRUSTED = "PROVIDER_UNTRUSTED"
    MODEL_UNTRUSTED = "MODEL_UNTRUSTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class HumanExecutionBarrierRequest:
    requested_execution_kind: str
    requested_command: str
    requested_command_hash: str
    source_trust: HumanExecutionSourceTrust | str
    human_decision_id: str | None
    human_decision_hash: str | None
    human_decision_verdict: HumanDecisionVerdict | str
    human_decision_source: HumanDecisionSource | str
    human_decision_binds_to_command_hash: str | None
    human_decision_binds_to_test_runner_control_hash: str | None
    human_decision_binds_to_sandbox_envelope_hash: str | None
    human_decision_binds_to_policy_check_hash: str | None = None
    human_decision_binds_to_controlled_execution_request_hash: str | None = None
    source_action_proposal_id: str | None = None
    source_action_proposal_hash: str | None = None
    source_tool_call_preview_id: str | None = None
    source_tool_call_preview_hash: str | None = None
    source_intent_route_id: str | None = None
    source_intent_route_hash: str | None = None
    source_policy_check_id: str | None = None
    source_policy_check_hash: str | None = None
    source_policy_check_status: str | None = None
    source_test_runner_control_id: str | None = None
    source_test_runner_control_hash: str | None = None
    source_test_runner_control_status: str | None = None
    source_sandbox_envelope_id: str | None = None
    source_sandbox_envelope_hash: str | None = None
    source_sandbox_envelope_status: str | None = None
    source_controlled_execution_request_hash: str | None = None
    human_review_required: bool = True
    risk_flags: tuple[str, ...] | list[str] = ()
    authority_claims: dict[str, Any] | None = None
    schema_version: str = HUMAN_EXECUTION_BARRIER_SCHEMA_VERSION


@dataclass(frozen=True)
class HumanExecutionBarrierResult:
    schema_version: str
    execution_barrier_id: str
    execution_barrier_hash: str
    status: HumanExecutionBarrierStatus
    requested_execution_kind: str
    requested_command: str
    requested_command_hash: str | None
    human_decision_id: str | None
    human_decision_hash: str | None
    human_decision_verdict: HumanDecisionVerdict
    human_decision_source: HumanDecisionSource
    execution_barrier_passed: bool
    source_action_proposal_id: str | None
    source_action_proposal_hash: str | None
    source_tool_call_preview_id: str | None
    source_tool_call_preview_hash: str | None
    source_intent_route_id: str | None
    source_intent_route_hash: str | None
    source_policy_check_id: str | None
    source_policy_check_hash: str | None
    source_test_runner_control_id: str | None
    source_test_runner_control_hash: str | None
    source_sandbox_envelope_id: str | None
    source_sandbox_envelope_hash: str | None
    source_controlled_execution_request_hash: str | None
    flags: tuple[HumanExecutionBarrierFlag, ...]
    risk_notes: tuple[str, ...]
    display_summary: str
    execution_performed: bool = False
    subprocess_started: bool = False
    shell_invoked: bool = False
    command_executed: bool = False
    test_command_executed: bool = False
    browser_opened: bool = False
    download_performed: bool = False
    file_read: bool = False
    file_written: bool = False
    directory_created: bool = False
    network_called: bool = False
    env_read: bool = False
    api_key_loaded: bool = False
    provider_called: bool = False
    approval_created: bool = False
    gate_changed: bool = False
    control_write_changed: bool = False
    tool_called: bool = False
    can_call_tool: bool = False
    can_execute_arbitrary_command: bool = False
    can_write: bool = False
    can_commit: bool = False
    can_change_approval_gate: bool = False
    can_change_policy: bool = False
    can_access_network: bool = False
    can_read_env: bool = False
    can_load_api_key: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _text("schema_version", self.schema_version))
        object.__setattr__(self, "execution_barrier_id", _text("execution_barrier_id", self.execution_barrier_id))
        object.__setattr__(self, "execution_barrier_hash", _text("execution_barrier_hash", self.execution_barrier_hash))
        object.__setattr__(self, "status", HumanExecutionBarrierStatus(self.status))
        object.__setattr__(self, "requested_execution_kind", _text("requested_execution_kind", self.requested_execution_kind))
        object.__setattr__(self, "requested_command", _text("requested_command", self.requested_command))
        object.__setattr__(self, "requested_command_hash", _optional_text(self.requested_command_hash))
        object.__setattr__(self, "human_decision_id", _optional_text(self.human_decision_id))
        object.__setattr__(self, "human_decision_hash", _optional_text(self.human_decision_hash))
        object.__setattr__(self, "human_decision_verdict", HumanDecisionVerdict(self.human_decision_verdict))
        object.__setattr__(self, "human_decision_source", HumanDecisionSource(self.human_decision_source))
        object.__setattr__(self, "execution_barrier_passed", self.status is HumanExecutionBarrierStatus.EXECUTION_BARRIER_PASSED)
        object.__setattr__(self, "source_action_proposal_id", _optional_text(self.source_action_proposal_id))
        object.__setattr__(self, "source_action_proposal_hash", _optional_text(self.source_action_proposal_hash))
        object.__setattr__(self, "source_tool_call_preview_id", _optional_text(self.source_tool_call_preview_id))
        object.__setattr__(self, "source_tool_call_preview_hash", _optional_text(self.source_tool_call_preview_hash))
        object.__setattr__(self, "source_intent_route_id", _optional_text(self.source_intent_route_id))
        object.__setattr__(self, "source_intent_route_hash", _optional_text(self.source_intent_route_hash))
        object.__setattr__(self, "source_policy_check_id", _optional_text(self.source_policy_check_id))
        object.__setattr__(self, "source_policy_check_hash", _optional_text(self.source_policy_check_hash))
        object.__setattr__(self, "source_test_runner_control_id", _optional_text(self.source_test_runner_control_id))
        object.__setattr__(self, "source_test_runner_control_hash", _optional_text(self.source_test_runner_control_hash))
        object.__setattr__(self, "source_sandbox_envelope_id", _optional_text(self.source_sandbox_envelope_id))
        object.__setattr__(self, "source_sandbox_envelope_hash", _optional_text(self.source_sandbox_envelope_hash))
        object.__setattr__(self, "source_controlled_execution_request_hash", _optional_text(self.source_controlled_execution_request_hash))
        object.__setattr__(self, "flags", _flag_tuple(self.flags))
        object.__setattr__(self, "risk_notes", _text_tuple("risk_notes", self.risk_notes))
        object.__setattr__(self, "display_summary", _bounded_text(_text("display_summary", self.display_summary)))
        for field_name in (
            "execution_performed",
            "subprocess_started",
            "shell_invoked",
            "command_executed",
            "test_command_executed",
            "browser_opened",
            "download_performed",
            "file_read",
            "file_written",
            "directory_created",
            "network_called",
            "env_read",
            "api_key_loaded",
            "provider_called",
            "approval_created",
            "gate_changed",
            "control_write_changed",
            "tool_called",
            "can_call_tool",
            "can_execute_arbitrary_command",
            "can_write",
            "can_commit",
            "can_change_approval_gate",
            "can_change_policy",
            "can_access_network",
            "can_read_env",
            "can_load_api_key",
        ):
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "execution_barrier_id": self.execution_barrier_id,
            "execution_barrier_hash": self.execution_barrier_hash,
            "status": self.status.value,
            "requested_execution_kind": self.requested_execution_kind,
            "requested_command": self.requested_command,
            "requested_command_hash": self.requested_command_hash,
            "human_decision_id": self.human_decision_id,
            "human_decision_hash": self.human_decision_hash,
            "human_decision_verdict": self.human_decision_verdict.value,
            "human_decision_source": self.human_decision_source.value,
            "execution_barrier_passed": self.execution_barrier_passed,
            "source_action_proposal_id": self.source_action_proposal_id,
            "source_action_proposal_hash": self.source_action_proposal_hash,
            "source_tool_call_preview_id": self.source_tool_call_preview_id,
            "source_tool_call_preview_hash": self.source_tool_call_preview_hash,
            "source_intent_route_id": self.source_intent_route_id,
            "source_intent_route_hash": self.source_intent_route_hash,
            "source_policy_check_id": self.source_policy_check_id,
            "source_policy_check_hash": self.source_policy_check_hash,
            "source_test_runner_control_id": self.source_test_runner_control_id,
            "source_test_runner_control_hash": self.source_test_runner_control_hash,
            "source_sandbox_envelope_id": self.source_sandbox_envelope_id,
            "source_sandbox_envelope_hash": self.source_sandbox_envelope_hash,
            "source_controlled_execution_request_hash": self.source_controlled_execution_request_hash,
            "flags": [flag.value for flag in self.flags],
            "risk_notes": list(self.risk_notes),
            "display_summary": self.display_summary,
            "execution_performed": self.execution_performed,
            "subprocess_started": self.subprocess_started,
            "shell_invoked": self.shell_invoked,
            "command_executed": self.command_executed,
            "test_command_executed": self.test_command_executed,
            "browser_opened": self.browser_opened,
            "download_performed": self.download_performed,
            "file_read": self.file_read,
            "file_written": self.file_written,
            "directory_created": self.directory_created,
            "network_called": self.network_called,
            "env_read": self.env_read,
            "api_key_loaded": self.api_key_loaded,
            "provider_called": self.provider_called,
            "approval_created": self.approval_created,
            "gate_changed": self.gate_changed,
            "control_write_changed": self.control_write_changed,
            "tool_called": self.tool_called,
            "can_call_tool": self.can_call_tool,
            "can_execute_arbitrary_command": self.can_execute_arbitrary_command,
            "can_write": self.can_write,
            "can_commit": self.can_commit,
            "can_change_approval_gate": self.can_change_approval_gate,
            "can_change_policy": self.can_change_policy,
            "can_access_network": self.can_access_network,
            "can_read_env": self.can_read_env,
            "can_load_api_key": self.can_load_api_key,
        }


def evaluate_human_execution_barrier(request: HumanExecutionBarrierRequest) -> HumanExecutionBarrierResult:
    if not isinstance(request, HumanExecutionBarrierRequest):
        return _build_result(
            request_data=_empty_request_data(),
            status=HumanExecutionBarrierStatus.MALFORMED_REQUEST,
            flags={HumanExecutionBarrierFlag.HUMAN_DECISION_REQUIRED},
            risk_notes=("Malformed HumanExecutionBarrierRequest input.",),
        )

    try:
        request_data = _request_data(request)
    except (TypeError, ValueError):
        return _build_result(
            request_data=_empty_request_data(),
            status=HumanExecutionBarrierStatus.MALFORMED_REQUEST,
            flags={HumanExecutionBarrierFlag.HUMAN_DECISION_REQUIRED},
            risk_notes=("Request metadata was malformed or non-deterministic.",),
        )

    flags: set[HumanExecutionBarrierFlag] = set()
    risk_notes: list[str] = []
    status = _status_for(request_data, flags, risk_notes)
    return _build_result(
        request_data=request_data,
        status=status,
        flags=flags,
        risk_notes=tuple(risk_notes),
    )


def _status_for(
    request_data: dict[str, Any],
    flags: set[HumanExecutionBarrierFlag],
    risk_notes: list[str],
) -> HumanExecutionBarrierStatus:
    if not request_data["human_decision_id"] or not request_data["human_decision_hash"]:
        flags.add(HumanExecutionBarrierFlag.HUMAN_DECISION_REQUIRED)
        risk_notes.append("Human decision id and hash are required.")
        return HumanExecutionBarrierStatus.BLOCKED_MISSING_HUMAN_DECISION
    flags.add(HumanExecutionBarrierFlag.HUMAN_DECISION_PRESENT)

    if _provider_untrusted(request_data["source_trust"]):
        flags.add(HumanExecutionBarrierFlag.PROVIDER_OUTPUT_UNTRUSTED)
        risk_notes.append("Provider or model output cannot pass the execution barrier.")
        return HumanExecutionBarrierStatus.BLOCKED_UNTRUSTED_PROVIDER_SOURCE

    if request_data["human_decision_source"] not in {
        HumanDecisionSource.HUMAN_OPERATOR.value,
        HumanDecisionSource.LOCAL_OPERATOR.value,
        HumanDecisionSource.HUMAN_REVIEWER.value,
    }:
        flags.add(HumanExecutionBarrierFlag.NON_HUMAN_DECISION_SOURCE_BLOCKED)
        risk_notes.append("Decision source is not a local human/operator source.")
        return HumanExecutionBarrierStatus.BLOCKED_NON_HUMAN_DECISION_SOURCE

    if request_data["human_decision_verdict"] != HumanDecisionVerdict.APPROVE.value:
        flags.add(HumanExecutionBarrierFlag.HUMAN_DECISION_REJECT)
        risk_notes.append("Human decision verdict is not APPROVE.")
        return HumanExecutionBarrierStatus.BLOCKED_REJECTED_BY_HUMAN
    flags.add(HumanExecutionBarrierFlag.HUMAN_DECISION_APPROVE)

    if not _looks_like_sha256(request_data["requested_command_hash"]):
        risk_notes.append("Requested command hash is missing or malformed.")
        return HumanExecutionBarrierStatus.BLOCKED_COMMAND_HASH_MISMATCH
    if not _looks_like_sha256(request_data["source_test_runner_control_hash"]):
        risk_notes.append("Test-runner controller hash is missing or malformed.")
        return HumanExecutionBarrierStatus.BLOCKED_TEST_RUNNER_HASH_MISMATCH
    if not _looks_like_sha256(request_data["source_sandbox_envelope_hash"]):
        risk_notes.append("Sandbox envelope hash is missing or malformed.")
        return HumanExecutionBarrierStatus.BLOCKED_SANDBOX_HASH_MISMATCH

    if _blocking_status(request_data["source_test_runner_control_status"]):
        risk_notes.append("Test-runner controller status is blocking.")
        return HumanExecutionBarrierStatus.BLOCKED_INVALID_TEST_RUNNER_STATUS
    if _blocking_status(request_data["source_sandbox_envelope_status"]):
        risk_notes.append("Sandbox envelope status is blocking.")
        return HumanExecutionBarrierStatus.BLOCKED_INVALID_SANDBOX_STATUS
    if request_data["source_policy_check_status"] and _blocking_status(request_data["source_policy_check_status"]):
        risk_notes.append("Local policy status is blocking.")
        return HumanExecutionBarrierStatus.BLOCKED_INVALID_POLICY_STATUS

    if _unsafe_risk_flags(request_data["risk_flags"]):
        flags.add(HumanExecutionBarrierFlag.UNSAFE_RISK_FLAG_BLOCKED)
        risk_notes.append("Risk flags contain hard-block execution indicators.")
        return HumanExecutionBarrierStatus.BLOCKED_UNSAFE_RISK_FLAG

    if request_data["human_decision_binds_to_command_hash"] != request_data["requested_command_hash"]:
        flags.add(HumanExecutionBarrierFlag.HASH_MISMATCH_BLOCKED)
        risk_notes.append("Human decision does not bind to the requested command hash.")
        return HumanExecutionBarrierStatus.BLOCKED_COMMAND_HASH_MISMATCH
    flags.add(HumanExecutionBarrierFlag.COMMAND_HASH_BOUND)

    if request_data["human_decision_binds_to_test_runner_control_hash"] != request_data["source_test_runner_control_hash"]:
        flags.add(HumanExecutionBarrierFlag.HASH_MISMATCH_BLOCKED)
        risk_notes.append("Human decision does not bind to the test-runner controller hash.")
        return HumanExecutionBarrierStatus.BLOCKED_TEST_RUNNER_HASH_MISMATCH
    flags.add(HumanExecutionBarrierFlag.TEST_RUNNER_HASH_BOUND)

    if request_data["human_decision_binds_to_sandbox_envelope_hash"] != request_data["source_sandbox_envelope_hash"]:
        flags.add(HumanExecutionBarrierFlag.HASH_MISMATCH_BLOCKED)
        risk_notes.append("Human decision does not bind to the sandbox envelope hash.")
        return HumanExecutionBarrierStatus.BLOCKED_SANDBOX_HASH_MISMATCH
    flags.add(HumanExecutionBarrierFlag.SANDBOX_HASH_BOUND)

    policy_hash = request_data["source_policy_check_hash"]
    if policy_hash:
        if not _looks_like_sha256(policy_hash) or request_data["human_decision_binds_to_policy_check_hash"] != policy_hash:
            flags.add(HumanExecutionBarrierFlag.HASH_MISMATCH_BLOCKED)
            risk_notes.append("Human decision does not bind to the local policy hash.")
            return HumanExecutionBarrierStatus.BLOCKED_POLICY_HASH_MISMATCH
        flags.add(HumanExecutionBarrierFlag.POLICY_HASH_BOUND)

    request_hash = request_data["source_controlled_execution_request_hash"]
    if request_hash:
        if (
            not _looks_like_sha256(request_hash)
            or request_data["human_decision_binds_to_controlled_execution_request_hash"] != request_hash
        ):
            flags.add(HumanExecutionBarrierFlag.HASH_MISMATCH_BLOCKED)
            risk_notes.append("Human decision does not bind to the controlled execution request hash.")
            return HumanExecutionBarrierStatus.BLOCKED_CONTROLLED_EXECUTION_REQUEST_HASH_MISMATCH
        flags.add(HumanExecutionBarrierFlag.CONTROLLED_EXECUTION_REQUEST_HASH_BOUND)

    flags.add(HumanExecutionBarrierFlag.BARRIER_PASSED_FOR_CONTROLLED_TEST_RUNNER_ONLY)
    risk_notes.append("Hash-bound human barrier passed for controlled test-runner metadata only; no execution occurred.")
    return HumanExecutionBarrierStatus.EXECUTION_BARRIER_PASSED


def _build_result(
    *,
    request_data: dict[str, Any],
    status: HumanExecutionBarrierStatus,
    flags: set[HumanExecutionBarrierFlag],
    risk_notes: tuple[str, ...],
) -> HumanExecutionBarrierResult:
    base_flags = {
        HumanExecutionBarrierFlag.HUMAN_EXECUTION_BARRIER_METADATA_ONLY,
        HumanExecutionBarrierFlag.NO_EXECUTION,
        HumanExecutionBarrierFlag.NO_SUBPROCESS,
        HumanExecutionBarrierFlag.NO_SHELL,
        HumanExecutionBarrierFlag.NO_COMMAND_EXECUTION,
        HumanExecutionBarrierFlag.NO_BROWSER,
        HumanExecutionBarrierFlag.NO_DOWNLOAD,
        HumanExecutionBarrierFlag.NO_FILE_READ,
        HumanExecutionBarrierFlag.NO_FILE_WRITE,
        HumanExecutionBarrierFlag.NO_NETWORK,
        HumanExecutionBarrierFlag.NO_ENV_ACCESS,
        HumanExecutionBarrierFlag.NO_API_KEY_ACCESS,
        HumanExecutionBarrierFlag.NO_PROVIDER_CALL,
        HumanExecutionBarrierFlag.NO_APPROVAL_CREATED,
        HumanExecutionBarrierFlag.NO_GATE_CHANGE,
        HumanExecutionBarrierFlag.NO_CONTROL_WRITE_CHANGE,
        HumanExecutionBarrierFlag.ACTION_PROPOSAL_METADATA_ONLY,
        HumanExecutionBarrierFlag.TOOL_CALL_PREVIEW_METADATA_ONLY,
        HumanExecutionBarrierFlag.INTENT_ROUTE_METADATA_ONLY,
        HumanExecutionBarrierFlag.LOCAL_POLICY_METADATA_ONLY,
        HumanExecutionBarrierFlag.TEST_RUNNER_METADATA_ONLY,
        HumanExecutionBarrierFlag.SANDBOX_ENVELOPE_METADATA_ONLY,
        HumanExecutionBarrierFlag.CONTROLLED_EXECUTION_REQUEST_METADATA_ONLY,
    }
    all_flags = base_flags | set(flags)
    ordered_flags = tuple(sorted(all_flags, key=lambda flag: flag.value))
    ordered_notes = tuple(sorted(set(risk_notes)))
    stable_payload = {
        "schema_version": HUMAN_EXECUTION_BARRIER_SCHEMA_VERSION,
        "status": status.value,
        "requested_execution_kind": request_data["requested_execution_kind"],
        "requested_command": request_data["requested_command"],
        "requested_command_hash": request_data["requested_command_hash"],
        "human_decision_id": request_data["human_decision_id"],
        "human_decision_hash": request_data["human_decision_hash"],
        "human_decision_verdict": request_data["human_decision_verdict"],
        "human_decision_source": request_data["human_decision_source"],
        "execution_barrier_passed": status is HumanExecutionBarrierStatus.EXECUTION_BARRIER_PASSED,
        "source_action_proposal_id": request_data["source_action_proposal_id"],
        "source_action_proposal_hash": request_data["source_action_proposal_hash"],
        "source_tool_call_preview_id": request_data["source_tool_call_preview_id"],
        "source_tool_call_preview_hash": request_data["source_tool_call_preview_hash"],
        "source_intent_route_id": request_data["source_intent_route_id"],
        "source_intent_route_hash": request_data["source_intent_route_hash"],
        "source_policy_check_id": request_data["source_policy_check_id"],
        "source_policy_check_hash": request_data["source_policy_check_hash"],
        "source_test_runner_control_id": request_data["source_test_runner_control_id"],
        "source_test_runner_control_hash": request_data["source_test_runner_control_hash"],
        "source_sandbox_envelope_id": request_data["source_sandbox_envelope_id"],
        "source_sandbox_envelope_hash": request_data["source_sandbox_envelope_hash"],
        "source_controlled_execution_request_hash": request_data["source_controlled_execution_request_hash"],
        "flags": [flag.value for flag in ordered_flags],
        "risk_notes": list(ordered_notes),
    }
    barrier_hash = _hash_json(stable_payload)
    return HumanExecutionBarrierResult(
        schema_version=HUMAN_EXECUTION_BARRIER_SCHEMA_VERSION,
        execution_barrier_id=f"human-exec-barrier-{barrier_hash[:24]}",
        execution_barrier_hash=barrier_hash,
        status=status,
        requested_execution_kind=request_data["requested_execution_kind"],
        requested_command=request_data["requested_command"],
        requested_command_hash=request_data["requested_command_hash"],
        human_decision_id=request_data["human_decision_id"],
        human_decision_hash=request_data["human_decision_hash"],
        human_decision_verdict=HumanDecisionVerdict(request_data["human_decision_verdict"]),
        human_decision_source=HumanDecisionSource(request_data["human_decision_source"]),
        execution_barrier_passed=status is HumanExecutionBarrierStatus.EXECUTION_BARRIER_PASSED,
        source_action_proposal_id=request_data["source_action_proposal_id"],
        source_action_proposal_hash=request_data["source_action_proposal_hash"],
        source_tool_call_preview_id=request_data["source_tool_call_preview_id"],
        source_tool_call_preview_hash=request_data["source_tool_call_preview_hash"],
        source_intent_route_id=request_data["source_intent_route_id"],
        source_intent_route_hash=request_data["source_intent_route_hash"],
        source_policy_check_id=request_data["source_policy_check_id"],
        source_policy_check_hash=request_data["source_policy_check_hash"],
        source_test_runner_control_id=request_data["source_test_runner_control_id"],
        source_test_runner_control_hash=request_data["source_test_runner_control_hash"],
        source_sandbox_envelope_id=request_data["source_sandbox_envelope_id"],
        source_sandbox_envelope_hash=request_data["source_sandbox_envelope_hash"],
        source_controlled_execution_request_hash=request_data["source_controlled_execution_request_hash"],
        flags=ordered_flags,
        risk_notes=ordered_notes,
        display_summary=_summary(status),
    )


def _request_data(request: HumanExecutionBarrierRequest) -> dict[str, Any]:
    return {
        "schema_version": _text("schema_version", request.schema_version),
        "requested_execution_kind": _text("requested_execution_kind", request.requested_execution_kind).strip(),
        "requested_command": _text("requested_command", request.requested_command),
        "requested_command_hash": _optional_text(request.requested_command_hash),
        "source_trust": _normalize_source_trust(request.source_trust).value,
        "human_decision_id": _optional_text(request.human_decision_id),
        "human_decision_hash": _optional_text(request.human_decision_hash),
        "human_decision_verdict": _normalize_verdict(request.human_decision_verdict).value,
        "human_decision_source": _normalize_decision_source(request.human_decision_source).value,
        "human_decision_binds_to_command_hash": _optional_text(request.human_decision_binds_to_command_hash),
        "human_decision_binds_to_test_runner_control_hash": _optional_text(
            request.human_decision_binds_to_test_runner_control_hash
        ),
        "human_decision_binds_to_sandbox_envelope_hash": _optional_text(request.human_decision_binds_to_sandbox_envelope_hash),
        "human_decision_binds_to_policy_check_hash": _optional_text(request.human_decision_binds_to_policy_check_hash),
        "human_decision_binds_to_controlled_execution_request_hash": _optional_text(
            request.human_decision_binds_to_controlled_execution_request_hash
        ),
        "source_action_proposal_id": _optional_text(request.source_action_proposal_id),
        "source_action_proposal_hash": _optional_text(request.source_action_proposal_hash),
        "source_tool_call_preview_id": _optional_text(request.source_tool_call_preview_id),
        "source_tool_call_preview_hash": _optional_text(request.source_tool_call_preview_hash),
        "source_intent_route_id": _optional_text(request.source_intent_route_id),
        "source_intent_route_hash": _optional_text(request.source_intent_route_hash),
        "source_policy_check_id": _optional_text(request.source_policy_check_id),
        "source_policy_check_hash": _optional_text(request.source_policy_check_hash),
        "source_policy_check_status": _optional_text(request.source_policy_check_status),
        "source_test_runner_control_id": _optional_text(request.source_test_runner_control_id),
        "source_test_runner_control_hash": _optional_text(request.source_test_runner_control_hash),
        "source_test_runner_control_status": _optional_text(request.source_test_runner_control_status),
        "source_sandbox_envelope_id": _optional_text(request.source_sandbox_envelope_id),
        "source_sandbox_envelope_hash": _optional_text(request.source_sandbox_envelope_hash),
        "source_sandbox_envelope_status": _optional_text(request.source_sandbox_envelope_status),
        "source_controlled_execution_request_hash": _optional_text(request.source_controlled_execution_request_hash),
        "human_review_required": bool(request.human_review_required),
        "risk_flags": tuple(value.upper() for value in _text_tuple("risk_flags", request.risk_flags)),
        "authority_claims": _stable_json_mapping(request.authority_claims),
    }


def _empty_request_data() -> dict[str, Any]:
    return {
        "schema_version": HUMAN_EXECUTION_BARRIER_SCHEMA_VERSION,
        "requested_execution_kind": "",
        "requested_command": "",
        "requested_command_hash": None,
        "source_trust": HumanExecutionSourceTrust.UNKNOWN.value,
        "human_decision_id": None,
        "human_decision_hash": None,
        "human_decision_verdict": HumanDecisionVerdict.UNKNOWN.value,
        "human_decision_source": HumanDecisionSource.UNKNOWN.value,
        "human_decision_binds_to_command_hash": None,
        "human_decision_binds_to_test_runner_control_hash": None,
        "human_decision_binds_to_sandbox_envelope_hash": None,
        "human_decision_binds_to_policy_check_hash": None,
        "human_decision_binds_to_controlled_execution_request_hash": None,
        "source_action_proposal_id": None,
        "source_action_proposal_hash": None,
        "source_tool_call_preview_id": None,
        "source_tool_call_preview_hash": None,
        "source_intent_route_id": None,
        "source_intent_route_hash": None,
        "source_policy_check_id": None,
        "source_policy_check_hash": None,
        "source_policy_check_status": None,
        "source_test_runner_control_id": None,
        "source_test_runner_control_hash": None,
        "source_test_runner_control_status": None,
        "source_sandbox_envelope_id": None,
        "source_sandbox_envelope_hash": None,
        "source_sandbox_envelope_status": None,
        "source_controlled_execution_request_hash": None,
        "human_review_required": True,
        "risk_flags": (),
        "authority_claims": {},
    }


def _blocking_status(value: str | None) -> bool:
    if not value:
        return True
    text = value.upper()
    blockers = ("BLOCKED", "REJECTED", "UNSAFE", "MALFORMED", "INCONSISTENT", "DENIED", "FORBIDDEN")
    return any(blocker in text for blocker in blockers)


def _unsafe_risk_flags(values: tuple[str, ...]) -> bool:
    blockers = (
        "UNSAFE",
        "BLOCKED",
        "SHELL",
        "ARBITRARY_COMMAND",
        "NETWORK_ACCESS",
        "ENV_ACCESS",
        "API_KEY",
        "SECRET",
        "TOKEN",
        "BROWSER",
        "DOWNLOAD",
        "GITHUB_WRITE",
        "PROVIDER_CALL",
        "APPROVAL_MUTATION",
        "GATE_CHANGE",
        "CONTROL_WRITE_CHANGE",
    )
    for value in values:
        if value.startswith("NO_"):
            continue
        if any(blocker in value for blocker in blockers):
            return True
    return False


def _provider_untrusted(source_trust: str) -> bool:
    return source_trust in {
        HumanExecutionSourceTrust.UNTRUSTED_PROVIDER_OUTPUT.value,
        HumanExecutionSourceTrust.PROVIDER_UNTRUSTED.value,
        HumanExecutionSourceTrust.MODEL_UNTRUSTED.value,
    }


def _normalize_source_trust(value: HumanExecutionSourceTrust | str) -> HumanExecutionSourceTrust:
    if isinstance(value, HumanExecutionSourceTrust):
        return value
    normalized = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "USER": HumanExecutionSourceTrust.USER_SUPPLIED,
        "USER_SUPPLIED": HumanExecutionSourceTrust.USER_SUPPLIED,
        "HUMAN_OPERATOR": HumanExecutionSourceTrust.HUMAN_OPERATOR,
        "SYSTEM_METADATA": HumanExecutionSourceTrust.SYSTEM_METADATA,
        "CRITIC_METADATA": HumanExecutionSourceTrust.CRITIC_METADATA,
        "UNTRUSTED": HumanExecutionSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        "UNTRUSTED_PROVIDER_OUTPUT": HumanExecutionSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        "PROVIDER_UNTRUSTED": HumanExecutionSourceTrust.PROVIDER_UNTRUSTED,
        "MODEL_UNTRUSTED": HumanExecutionSourceTrust.MODEL_UNTRUSTED,
    }
    return aliases.get(normalized, HumanExecutionSourceTrust.UNKNOWN)


def _normalize_verdict(value: HumanDecisionVerdict | str) -> HumanDecisionVerdict:
    if isinstance(value, HumanDecisionVerdict):
        return value
    normalized = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "APPROVE": HumanDecisionVerdict.APPROVE,
        "APPROVED": HumanDecisionVerdict.APPROVE,
        "REJECT": HumanDecisionVerdict.REJECT,
        "REJECTED": HumanDecisionVerdict.REJECT,
        "NEEDS_CHANGES": HumanDecisionVerdict.NEEDS_CHANGES,
    }
    return aliases.get(normalized, HumanDecisionVerdict.UNKNOWN)


def _normalize_decision_source(value: HumanDecisionSource | str) -> HumanDecisionSource:
    if isinstance(value, HumanDecisionSource):
        return value
    normalized = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "HUMAN": HumanDecisionSource.HUMAN_OPERATOR,
        "HUMAN_OPERATOR": HumanDecisionSource.HUMAN_OPERATOR,
        "LOCAL_OPERATOR": HumanDecisionSource.LOCAL_OPERATOR,
        "HUMAN_REVIEWER": HumanDecisionSource.HUMAN_REVIEWER,
        "PROVIDER": HumanDecisionSource.PROVIDER_MODEL,
        "PROVIDER_MODEL": HumanDecisionSource.PROVIDER_MODEL,
        "MODEL": HumanDecisionSource.PROVIDER_MODEL,
        "SYSTEM_POLICY": HumanDecisionSource.SYSTEM_POLICY,
    }
    return aliases.get(normalized, HumanDecisionSource.UNKNOWN)


def _looks_like_sha256(value: str | None) -> bool:
    if value is None:
        return False
    return len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)


def _text(field_name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if "\x00" in value:
        raise ValueError(f"{field_name} cannot contain null bytes")
    return value


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = _text("optional_text", value).strip()
    return text or None


def _text_tuple(field_name: str, values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{field_name} must be a tuple or list")
    return tuple(_text(field_name, value).strip() for value in values)


def _flag_tuple(values: tuple[HumanExecutionBarrierFlag, ...]) -> tuple[HumanExecutionBarrierFlag, ...]:
    if not isinstance(values, tuple):
        raise TypeError("flags must be a tuple")
    return tuple(HumanExecutionBarrierFlag(value) for value in values)


def _stable_json_mapping(value: dict[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError("authority_claims must be a dict")
    return json.loads(_canonical_json(value))


def _hash_json(value: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _bounded_text(value: str) -> str:
    if len(value) <= _MAX_SUMMARY_CHARS:
        return value
    return value[: _MAX_SUMMARY_CHARS - 3] + "..."


def _summary(status: HumanExecutionBarrierStatus) -> str:
    passed = "passed" if status is HumanExecutionBarrierStatus.EXECUTION_BARRIER_PASSED else "blocked"
    return _bounded_text(
        f"Human execution barrier {passed} with status {status.value}; this result performs no execution and grants no general authority."
    )
