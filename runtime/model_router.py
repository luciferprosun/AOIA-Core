from __future__ import annotations

from dataclasses import asdict
from uuid import uuid4

try:
    from runtime.model_catalog import get_static_model_catalog
    from runtime.provider_audit import make_provider_audit_event
    from runtime.provider_clients import call_selected_provider_once
    from runtime.provider_registry import provider_live_call_allowed
    from runtime.sensitive_redaction import build_current_runtime_redactor
    from runtime.schemas.model_router import (
        ModelRoutingDecision,
        ModelSelectionProposal,
        ModelTaskContext,
        ProviderClass,
        RoutingDecisionStatus,
        TaskSensitivity,
        TrustLevel,
    )
except ModuleNotFoundError:  # pragma: no cover - script launch path
    from model_catalog import get_static_model_catalog
    from provider_audit import make_provider_audit_event
    from provider_clients import call_selected_provider_once
    from provider_registry import provider_live_call_allowed
    from sensitive_redaction import build_current_runtime_redactor
    from schemas.model_router import (
        ModelRoutingDecision,
        ModelSelectionProposal,
        ModelTaskContext,
        ProviderClass,
        RoutingDecisionStatus,
        TaskSensitivity,
        TrustLevel,
    )


_BLOCKED_SENSITIVITIES_FOR_FREE = {
    TaskSensitivity.SENSITIVE,
    TaskSensitivity.CANONICAL,
    TaskSensitivity.SECRET_ADJACENT,
}
_UNTRUSTED_TRUE_APPROVAL_FIELDS = {
    "approved",
    "human_approved",
    "provider_call_permitted",
    "execution_permitted",
    "canonical",
    "canonical_promotion_permitted",
    "canonical_promotion_triggered",
    "provider_output_trusted",
    "automatic_fallback_permitted",
}


def create_model_selection_proposal(
    *,
    provider_id: str,
    model_id: str,
    task_sensitivity: str,
    user_prompt: str,
    requester: str = "local-human",
) -> dict[str, object]:
    sensitivity = _parse_task_sensitivity(task_sensitivity)
    entry = _find_catalog_entry(provider_id, model_id)
    provider_class = entry.provider_class if entry else ProviderClass.UNKNOWN
    trust_level = entry.trust_level if entry else TrustLevel.UNKNOWN
    secret_bearing = sensitivity is TaskSensitivity.SECRET_ADJACENT
    canonical_task = sensitivity is TaskSensitivity.CANONICAL
    status = RoutingDecisionStatus.REJECTED_BY_POLICY if secret_bearing else RoutingDecisionStatus.PROPOSED
    context = ModelTaskContext(
        task_id=f"task-{uuid4().hex}",
        sensitivity=sensitivity,
        prompt_summary_redacted=_redacted_prompt_summary(user_prompt),
        requester=requester,
        secret_bearing=secret_bearing,
        canonical_task=canonical_task,
    )
    proposal_id = f"proposal-{uuid4().hex}"
    try:
        proposal = ModelSelectionProposal(
            proposal_id=proposal_id,
            task_context=context,
            requested_model_id=model_id,
            requested_provider_id=provider_id,
            provider_class=provider_class,
            trust_level=trust_level,
            rationale="Human approval required before one selected provider call.",
            status=status,
        )
    except ValueError:
        return {
            "proposal_id": proposal_id,
            "task_context": _task_context_to_dict(context),
            "requested_model_id": model_id,
            "requested_provider_id": provider_id,
            "provider_class": provider_class.value,
            "trust_level": trust_level.value,
            "rationale": "Policy review required before one selected provider call.",
            "status": RoutingDecisionStatus.REJECTED_BY_POLICY.value,
            "fallback_model_ids": [],
            "human_review_required": True,
            "provider_call_permitted": False,
            "automatic_fallback_permitted": False,
            "execution_permitted": False,
            "canonical_promotion_permitted": False,
        }
    return _proposal_to_dict(proposal)


def evaluate_model_selection_policy(
    *,
    proposal: dict[str, object] | None = None,
    provider_id: str | None = None,
    model_id: str | None = None,
    task_sensitivity: str | None = None,
) -> dict[str, object]:
    if proposal is not None:
        _reject_untrusted_approval_payload_fields(proposal, "proposal")
    provider = provider_id or str(proposal.get("requested_provider_id", "") if proposal else "")
    model = model_id or str(proposal.get("requested_model_id", "") if proposal else "")
    sensitivity_value = task_sensitivity or _proposal_sensitivity(proposal)
    sensitivity = _parse_task_sensitivity(sensitivity_value)
    entry = _find_catalog_entry(provider, model)

    status = RoutingDecisionStatus.REQUIRES_HUMAN_APPROVAL
    reason = "Human approval required before one selected provider call."

    if entry is None:
        status = RoutingDecisionStatus.DISABLED
        reason = "Provider or model is not in the static catalog."
    elif entry.provider_class in {ProviderClass.DISABLED, ProviderClass.UNKNOWN}:
        status = RoutingDecisionStatus.DISABLED
        reason = "Disabled or unknown providers cannot be called."
    elif sensitivity is TaskSensitivity.SECRET_ADJACENT:
        status = RoutingDecisionStatus.REJECTED_BY_POLICY
        reason = "Secret-adjacent prompts are not allowed for provider calls."
    elif entry.provider_class is ProviderClass.OPENROUTER_FREE and model == "openrouter/free":
        status = RoutingDecisionStatus.REJECTED_BY_POLICY
        reason = "Generic OpenRouter free routes cannot be called; exact model IDs are required."
    elif entry.provider_class is ProviderClass.OPENROUTER_FREE and sensitivity in _BLOCKED_SENSITIVITIES_FOR_FREE:
        status = RoutingDecisionStatus.REJECTED_BY_POLICY
        reason = "OpenRouter free models are blocked for sensitive, canonical, and secret-adjacent tasks."
    elif entry.free_tier and sensitivity in _BLOCKED_SENSITIVITIES_FOR_FREE:
        status = RoutingDecisionStatus.REJECTED_BY_POLICY
        reason = "Free model routes are blocked for sensitive, canonical, and secret-adjacent tasks."

    decision = ModelRoutingDecision(
        decision_id=f"decision-{uuid4().hex}",
        proposal_id=str(proposal.get("proposal_id", "")) if proposal else f"proposal-{uuid4().hex}",
        provider_id=provider,
        model_id=model,
        reason=reason,
        status=status,
    )
    return _decision_to_dict(decision)


def approve_model_selection(
    *,
    proposal: dict[str, object],
    decision: dict[str, object],
    human_approved: bool,
) -> dict[str, object]:
    _reject_untrusted_approval_payload_fields(proposal, "proposal")
    _reject_untrusted_approval_payload_fields(decision, "decision")
    permitted = (
        human_approved is True
        and decision.get("status") == RoutingDecisionStatus.REQUIRES_HUMAN_APPROVAL.value
    )
    return {
        "approval_id": f"m1-approval-{uuid4().hex}",
        "proposal_id": proposal.get("proposal_id", ""),
        "human_approved": human_approved is True,
        "provider_call_permitted": permitted,
        "automatic_fallback_permitted": False,
        "execution_permitted": False,
        "canonical_promotion_permitted": False,
        "approval_scope": "one selected provider call only",
    }


def execute_approved_model_call_once(
    *,
    provider_id: str,
    model_id: str,
    task_sensitivity: str,
    user_prompt: str,
    human_approved: bool,
    provider_call_func=call_selected_provider_once,
) -> dict[str, object]:
    output_redactor = build_current_runtime_redactor()
    proposal = create_model_selection_proposal(
        provider_id=provider_id,
        model_id=model_id,
        task_sensitivity=task_sensitivity,
        user_prompt=user_prompt,
    )
    decision = evaluate_model_selection_policy(proposal=proposal)
    approval = approve_model_selection(
        proposal=proposal,
        decision=decision,
        human_approved=human_approved,
    )
    policy_rejected = decision["status"] in {
        RoutingDecisionStatus.REJECTED_BY_POLICY.value,
        RoutingDecisionStatus.DISABLED.value,
    }

    legacy_live_call = provider_call_func is call_selected_provider_once
    registry_allowed = provider_live_call_allowed(provider_id)
    if (
        approval["provider_call_permitted"] is not True
        or (legacy_live_call and registry_allowed is not True)
    ):
        result = {
            "provider_id": provider_id,
            "model_id": model_id,
            "call_made": False,
            "output_text": "",
            "output_trusted": False,
            "error": (
                _blocked_call_reason(human_approved, decision)
                if approval["provider_call_permitted"] is not True
                else "Provider registry does not allow this live provider call."
            ),
        }
    else:
        call_result = provider_call_func(
            provider_id=provider_id,
            model_id=output_redactor.redact_text(model_id),
            user_prompt=output_redactor.redact_text(user_prompt),
            human_approved=human_approved,
            provider_call_permitted=bool(approval["provider_call_permitted"]),
            policy_rejected=policy_rejected,
        )
        result = call_result.to_dict() if hasattr(call_result, "to_dict") else dict(call_result)

    safe_result = output_redactor.redact(result)
    if not isinstance(safe_result, dict):
        raise TypeError("provider result must project to a dictionary")
    result = safe_result

    audit_event = make_provider_audit_event(
        provider_id=provider_id,
        model_id=model_id,
        status="CALL_MADE" if result["call_made"] else "CALL_BLOCKED",
        reason=str(result.get("error") or decision["reason"]),
        call_made=bool(result["call_made"]),
        human_approved=human_approved is True,
        provider_call_permitted=bool(approval["provider_call_permitted"]),
    )

    response = {
        "ok": not bool(result.get("error")),
        "proposal": proposal,
        "decision": decision,
        "approval": approval,
        "call_made": bool(result["call_made"]),
        "output_text": str(result.get("output_text", "")),
        "output_trusted": False,
        "error": str(result.get("error", "")),
        "audit_event": audit_event.to_dict(),
        "automatic_fallback_used": False,
        "execution_triggered": False,
        "canonical_promotion_triggered": False,
    }
    safe_response = output_redactor.redact(response)
    if not isinstance(safe_response, dict):
        raise TypeError("model router response must project to a dictionary")
    return safe_response


def _find_catalog_entry(provider_id: str, model_id: str):
    for entry in get_static_model_catalog():
        if entry.provider_id == provider_id and entry.model_id == model_id:
            return entry
    return None


def _parse_task_sensitivity(value: str) -> TaskSensitivity:
    try:
        return TaskSensitivity(str(value))
    except ValueError as error:
        raise ValueError("task_sensitivity must be a known TaskSensitivity value") from error


def _redacted_prompt_summary(user_prompt: str) -> str:
    return f"redacted prompt; length={len(user_prompt)}"


def _proposal_sensitivity(proposal: dict[str, object] | None) -> str:
    if not proposal:
        return TaskSensitivity.PUBLIC_DEV.value
    task_context = proposal.get("task_context", {})
    if isinstance(task_context, dict):
        return str(task_context.get("sensitivity", TaskSensitivity.PUBLIC_DEV.value))
    return TaskSensitivity.PUBLIC_DEV.value


def _blocked_call_reason(human_approved: bool, decision: dict[str, object]) -> str:
    if human_approved is not True:
        return "human approval is required"
    return str(decision.get("reason", "provider call is not permitted"))


def _reject_untrusted_approval_payload_fields(payload: dict[str, object], label: str) -> None:
    for field in _UNTRUSTED_TRUE_APPROVAL_FIELDS:
        if payload.get(field) is True:
            raise ValueError(f"{label} cannot self-authorize via {field}")
    if str(payload.get("approval_state", "")).strip().lower() == "approved":
        raise ValueError(f"{label} cannot self-authorize via approval_state")
    if payload.get("require_approval") is False:
        raise ValueError(f"{label} cannot disable approval via require_approval")


def _proposal_to_dict(proposal: ModelSelectionProposal) -> dict[str, object]:
    payload = asdict(proposal)
    payload["task_context"] = _task_context_to_dict(proposal.task_context)
    payload["provider_class"] = proposal.provider_class.value
    payload["trust_level"] = proposal.trust_level.value
    payload["status"] = proposal.status.value
    return payload


def _task_context_to_dict(context: ModelTaskContext) -> dict[str, object]:
    payload = asdict(context)
    payload["sensitivity"] = context.sensitivity.value
    return payload


def _decision_to_dict(decision: ModelRoutingDecision) -> dict[str, object]:
    payload = asdict(decision)
    payload["status"] = decision.status.value
    return payload
