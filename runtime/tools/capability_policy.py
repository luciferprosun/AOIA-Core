from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import Enum
from typing import TYPE_CHECKING, Any

from .validator import classify_shell_command, validate_shell_command

if TYPE_CHECKING:
    from trace_context import ActionContext


class CapabilityClass(str, Enum):
    """Runtime-owned capability classes for canonical executor actions."""

    READ_ONLY = "READ_ONLY"
    LOCAL_STATE_CHANGE = "LOCAL_STATE_CHANGE"
    FILESYSTEM_MUTATION = "FILESYSTEM_MUTATION"
    EXTERNAL_INTERACTION = "EXTERNAL_INTERACTION"
    CODE_EXECUTION = "CODE_EXECUTION"
    PRIVILEGED = "PRIVILEGED"


@dataclass(frozen=True)
class ActionPolicyRule:
    """Static policy assigned to one canonical executor action."""

    capability_class: CapabilityClass
    requires_confirmation: bool
    reason_code: str
    reason: str


@dataclass(frozen=True)
class ActionPolicyDecision:
    """Complete runtime authorization decision made before tool dispatch."""

    action_name: str
    capability_class: CapabilityClass
    allowed: bool
    requires_confirmation: bool
    reason_code: str
    reason: str
    runtime_requires_confirmation: bool
    model_requests_confirmation: bool
    request_id: str | None = None
    trace_id: str | None = None
    task_id: str | None = None
    action_id: str | None = None
    model_call_id: str | None = None


def _rule(
    capability_class: CapabilityClass,
    *,
    requires_confirmation: bool,
    reason_code: str,
    reason: str,
) -> ActionPolicyRule:
    return ActionPolicyRule(
        capability_class=capability_class,
        requires_confirmation=requires_confirmation,
        reason_code=reason_code,
        reason=reason,
    )


# Every action accepted by tools.validator.ALLOWED_ACTIONS must have one entry.
# The completeness test deliberately compares both registries so new actions fail
# CI until their actual side effects have been classified here.
ACTION_POLICY_RULES: dict[str, ActionPolicyRule] = {
    "respond": _rule(
        CapabilityClass.READ_ONLY,
        requires_confirmation=False,
        reason_code="READ_ONLY_ALLOWED",
        reason="Returning a response does not invoke a runtime tool side effect.",
    ),
    "shell_execute": _rule(
        CapabilityClass.CODE_EXECUTION,
        requires_confirmation=False,
        reason_code="SHELL_RUNTIME_CLASSIFIER",
        reason="Shell approval is determined by the runtime shell classifier.",
    ),
    "write_file": _rule(
        CapabilityClass.FILESYSTEM_MUTATION,
        requires_confirmation=True,
        reason_code="FILESYSTEM_MUTATION_REQUIRES_CONFIRMATION",
        reason="Writing filesystem content requires runtime-owned approval.",
    ),
    "append_file": _rule(
        CapabilityClass.FILESYSTEM_MUTATION,
        requires_confirmation=True,
        reason_code="FILESYSTEM_MUTATION_REQUIRES_CONFIRMATION",
        reason="Appending filesystem content requires runtime-owned approval.",
    ),
    "read_file": _rule(
        CapabilityClass.READ_ONLY,
        requires_confirmation=False,
        reason_code="READ_ONLY_ALLOWED",
        reason="Reading a contained project file does not change runtime state.",
    ),
    "create_file": _rule(
        CapabilityClass.FILESYSTEM_MUTATION,
        requires_confirmation=True,
        reason_code="FILESYSTEM_MUTATION_REQUIRES_CONFIRMATION",
        reason="Creating filesystem content requires runtime-owned approval.",
    ),
    "create_folder": _rule(
        CapabilityClass.FILESYSTEM_MUTATION,
        requires_confirmation=True,
        reason_code="FILESYSTEM_MUTATION_REQUIRES_CONFIRMATION",
        reason="Creating a directory requires runtime-owned approval.",
    ),
    "move_file": _rule(
        CapabilityClass.FILESYSTEM_MUTATION,
        requires_confirmation=True,
        reason_code="FILESYSTEM_MUTATION_REQUIRES_CONFIRMATION",
        reason="Moving or renaming filesystem content requires runtime-owned approval.",
    ),
    "delete_file": _rule(
        CapabilityClass.FILESYSTEM_MUTATION,
        requires_confirmation=True,
        reason_code="FILESYSTEM_MUTATION_REQUIRES_CONFIRMATION",
        reason="Deleting filesystem content requires runtime-owned approval.",
    ),
    "search_in_project": _rule(
        CapabilityClass.READ_ONLY,
        requires_confirmation=False,
        reason_code="READ_ONLY_ALLOWED",
        reason="Searching contained project files does not change runtime state.",
    ),
    "change_directory": _rule(
        CapabilityClass.LOCAL_STATE_CHANGE,
        requires_confirmation=True,
        reason_code="LOCAL_STATE_CHANGE_REQUIRES_CONFIRMATION",
        reason="Changing the runtime working directory changes local state.",
    ),
    "browser_start": _rule(
        CapabilityClass.EXTERNAL_INTERACTION,
        requires_confirmation=True,
        reason_code="EXTERNAL_INTERACTION_REQUIRES_CONFIRMATION",
        reason="Starting a browser session creates an external interaction surface.",
    ),
    "browser_open": _rule(
        CapabilityClass.EXTERNAL_INTERACTION,
        requires_confirmation=True,
        reason_code="EXTERNAL_INTERACTION_REQUIRES_CONFIRMATION",
        reason="Browser navigation may interact with an external system.",
    ),
    "browser_click": _rule(
        CapabilityClass.EXTERNAL_INTERACTION,
        requires_confirmation=True,
        reason_code="EXTERNAL_INTERACTION_REQUIRES_CONFIRMATION",
        reason="Clicking a browser element may cause an external state change.",
    ),
    "browser_type": _rule(
        CapabilityClass.EXTERNAL_INTERACTION,
        requires_confirmation=True,
        reason_code="EXTERNAL_INTERACTION_REQUIRES_CONFIRMATION",
        reason="Typing into a browser page changes externally visible page state.",
    ),
    "browser_press": _rule(
        CapabilityClass.EXTERNAL_INTERACTION,
        requires_confirmation=True,
        reason_code="EXTERNAL_INTERACTION_REQUIRES_CONFIRMATION",
        reason="A browser key press may submit data or change external state.",
    ),
    "browser_read_html": _rule(
        CapabilityClass.EXTERNAL_INTERACTION,
        requires_confirmation=True,
        reason_code="EXTERNAL_INTERACTION_REQUIRES_CONFIRMATION",
        reason="Reading browser HTML may start a browser and access external content.",
    ),
    "browser_get_visible_text": _rule(
        CapabilityClass.EXTERNAL_INTERACTION,
        requires_confirmation=True,
        reason_code="EXTERNAL_INTERACTION_REQUIRES_CONFIRMATION",
        reason="Reading browser text may start a browser and access external content.",
    ),
    "browser_screenshot": _rule(
        CapabilityClass.FILESYSTEM_MUTATION,
        requires_confirmation=True,
        reason_code="FILESYSTEM_MUTATION_REQUIRES_CONFIRMATION",
        reason="Capturing a browser screenshot writes filesystem content.",
    ),
    "browser_close": _rule(
        CapabilityClass.LOCAL_STATE_CHANGE,
        requires_confirmation=True,
        reason_code="LOCAL_STATE_CHANGE_REQUIRES_CONFIRMATION",
        reason="Closing the browser changes the active local session state.",
    ),
    "browser_current_url": _rule(
        CapabilityClass.EXTERNAL_INTERACTION,
        requires_confirmation=True,
        reason_code="EXTERNAL_INTERACTION_REQUIRES_CONFIRMATION",
        reason="Reading the browser URL may start a browser session.",
    ),
    "scan_project": _rule(
        CapabilityClass.FILESYSTEM_MUTATION,
        requires_confirmation=True,
        reason_code="FILESYSTEM_MUTATION_REQUIRES_CONFIRMATION",
        reason="Project scanning writes a project_scan.json runtime artifact.",
    ),
}

POLICY_ACTIONS = frozenset(ACTION_POLICY_RULES)


def _evaluate_action_policy_semantics(action: Mapping[str, Any]) -> ActionPolicyDecision:
    """Evaluate an action without trusting the model to reduce restrictions."""
    action_name = str(action.get("action", "")).strip()
    model_requests_confirmation = bool(action.get("requires_confirmation", False))
    rule = ACTION_POLICY_RULES.get(action_name)

    if rule is None:
        return ActionPolicyDecision(
            action_name=action_name,
            capability_class=CapabilityClass.PRIVILEGED,
            allowed=False,
            requires_confirmation=False,
            reason_code="ACTION_NOT_CLASSIFIED",
            reason="Runtime capability policy blocked an unknown or unclassified action.",
            runtime_requires_confirmation=False,
            model_requests_confirmation=model_requests_confirmation,
        )

    if action_name == "shell_execute":
        return _evaluate_shell_policy(
            action_name,
            str(action.get("command", "")),
            model_requests_confirmation,
        )

    final_requires_confirmation = (
        rule.requires_confirmation or model_requests_confirmation
    )
    if model_requests_confirmation and not rule.requires_confirmation:
        reason_code = "MODEL_ESCALATION_REQUIRES_CONFIRMATION"
        reason = "The model requested additional human confirmation."
    else:
        reason_code = rule.reason_code
        reason = rule.reason

    return ActionPolicyDecision(
        action_name=action_name,
        capability_class=rule.capability_class,
        allowed=True,
        requires_confirmation=final_requires_confirmation,
        reason_code=reason_code,
        reason=reason,
        runtime_requires_confirmation=rule.requires_confirmation,
        model_requests_confirmation=model_requests_confirmation,
    )


def _evaluate_shell_policy(
    action_name: str,
    command: str,
    model_requests_confirmation: bool,
) -> ActionPolicyDecision:
    allowed, validation_reason = validate_shell_command(command)
    if not allowed:
        return ActionPolicyDecision(
            action_name=action_name,
            capability_class=CapabilityClass.CODE_EXECUTION,
            allowed=False,
            requires_confirmation=False,
            reason_code="SHELL_COMMAND_BLOCKED",
            reason=f"Runtime shell policy blocked the command: {validation_reason}",
            runtime_requires_confirmation=False,
            model_requests_confirmation=model_requests_confirmation,
        )

    shell_decision = classify_shell_command(command)
    runtime_requires_confirmation = shell_decision.requires_confirmation
    final_requires_confirmation = (
        runtime_requires_confirmation or model_requests_confirmation
    )
    if runtime_requires_confirmation:
        reason_code = "SHELL_RUNTIME_CONFIRMATION_REQUIRED"
        reason = shell_decision.reason
    elif model_requests_confirmation:
        reason_code = "MODEL_ESCALATION_REQUIRES_CONFIRMATION"
        reason = "The model requested additional human confirmation."
    else:
        reason_code = "SHELL_RUNTIME_POLICY_ALLOWED"
        reason = shell_decision.reason

    return ActionPolicyDecision(
        action_name=action_name,
        capability_class=CapabilityClass.CODE_EXECUTION,
        allowed=True,
        requires_confirmation=final_requires_confirmation,
        reason_code=reason_code,
        reason=reason,
        runtime_requires_confirmation=runtime_requires_confirmation,
        model_requests_confirmation=model_requests_confirmation,
    )


def evaluate_action_policy(
    action: Mapping[str, Any],
    action_context: "ActionContext | None" = None,
) -> ActionPolicyDecision:
    """Evaluate policy semantics and attach authoritative action correlation."""

    decision = _evaluate_action_policy_semantics(action)
    if action_context is None:
        return decision
    return replace(
        decision,
        request_id=action_context.request_id,
        trace_id=action_context.trace_id,
        task_id=action_context.task_id,
        action_id=action_context.action_id,
        model_call_id=action_context.model_call_id,
    )
