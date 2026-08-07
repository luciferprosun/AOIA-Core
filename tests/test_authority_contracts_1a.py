from __future__ import annotations

import ast
import hashlib
import importlib
import math
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

from runtime.execution.authority_contracts import (
    AOIA_APPROVED_EXECUTION_REQUEST_V1,
    AOIA_CASE_V1,
    AOIA_EXACT_SCOPE_V1,
    AOIA_HUMAN_EXECUTION_APPROVAL_V1,
    AOIA_NORMALIZED_ARGUMENTS_V1,
    AOIA_PLAN_STEP_V1,
    AOIA_RESOURCE_IDENTITY_V1,
    AOIA_VISIBLE_PLAN_V1,
    ApprovalStatus,
    ApprovedExecutionRequest,
    AuthorityContractError,
    AuthorityBindingMismatch,
    AuthorityHashMismatch,
    Case,
    CaseStatus,
    ExactScope,
    HumanApproval,
    PlanStatus,
    PlanStep,
    VisiblePlan,
    hash_normalized_arguments,
    hash_resource_identity,
    validate_authority_bindings,
)
from runtime.execution.canonical_serialization import (
    CanonicalSerializationError,
    FrozenDict,
    canonical_json_bytes,
    domain_separated_sha256,
    freeze_json,
    hashes_equal,
    require_sha256,
    thaw_json,
)


ROOT = Path(__file__).resolve().parents[1]
SERIALIZATION_SOURCE = ROOT / "runtime/execution/canonical_serialization.py"
CONTRACT_SOURCE = ROOT / "runtime/execution/authority_contracts.py"
H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64
H4 = "4" * 64
T0 = "2026-08-07T10:00:00Z"
T1 = "2026-08-07T11:00:00Z"
T2 = "2026-08-07T12:00:00Z"
T3 = "2026-08-07T13:00:00Z"


def make_case(**changes: object) -> Case:
    values: dict[str, object] = {
        "case_id": "case-001",
        "case_version": 1,
        "created_at": T0,
        "created_by": "operator-001",
        "purpose": "Bounded local review",
        "authorization_type": "WRITTEN_MANDATE",
        "authorization_reference": "auth-ref-001",
        "authorization_subject": "subject-001",
        "authorization_valid_from": T0,
        "authorization_valid_until": T2,
        "jurisdiction": "PL",
        "data_classification": "CONFIDENTIAL",
        "scope_id": "scope-001",
        "policy_version": "policy-1",
        "status": CaseStatus.OPEN,
        "closure_reason": None,
        "previous_case_hash": None,
    }
    values.update(changes)
    return Case(**values)


def make_scope(**changes: object) -> ExactScope:
    values: dict[str, object] = {
        "scope_id": "scope-001",
        "scope_version": 1,
        "case_id": "case-001",
        "allowed_subjects": ("subject-001",),
        "allowed_resources": ("resource-001",),
        "allowed_resource_types": ("DOCUMENT",),
        "allowed_operations": ("READ",),
        "allowed_adapters": ("adapter-001",),
        "allowed_destinations": ("api.example.invalid",),
        "allowed_protocols": ("https",),
        "allowed_time_window": (T0, T2),
        "maximum_requests": 2,
        "maximum_results": 10,
        "maximum_payload_bytes": 4096,
        "maximum_runtime_seconds": 30,
        "maximum_subprocesses": 0,
        "maximum_storage_bytes": 8192,
        "maximum_retries": 0,
        "maximum_cpu": 100,
        "maximum_memory_bytes": 1_048_576,
        "maximum_concurrency": 1,
        "maximum_cost": 0,
        "write_permissions": ("READ_ONLY",),
        "network_permissions": ("HTTPS_ALLOWLIST_ONLY",),
        "retention_policy": "retain-30-days",
        "explicit_denials": ("shell",),
        "previous_scope_hash": None,
    }
    values.update(changes)
    return ExactScope(**values)


def make_step(
    step_index: int = 0,
    step_id: str = "step-001",
    **changes: object,
) -> PlanStep:
    values: dict[str, object] = {
        "step_index": step_index,
        "step_id": step_id,
        "adapter_id": "adapter-001",
        "adapter_version": "1.0.0",
        "adapter_entry_hash": H1,
        "operation": "READ",
        "normalized_arguments": {"query": "alpha", "result_limit": 2},
        "resource_identity": {"resource_id": "resource-001", "resource_type": "DOCUMENT"},
        "destination": "api.example.invalid",
        "protocol": "https",
        "limits": {"maximum_results": 2, "timeout_seconds": 10},
        "expected_output": {"media_type": "application/json"},
        "evidence_policy": "evidence-policy-1",
    }
    values.update(changes)
    return PlanStep(**values)


def make_plan(**changes: object) -> VisiblePlan:
    values: dict[str, object] = {
        "plan_id": "plan-001",
        "plan_version": 1,
        "case_id": "case-001",
        "scope_id": "scope-001",
        "ordered_steps": (make_step(),),
        "expected_outputs": ({"media_type": "application/json"},),
        "limits": {"maximum_requests": 1},
        "data_classification": "CONFIDENTIAL",
        "policy_version": "policy-1",
        "adapter_manifest_version": "manifest-1",
        "adapter_manifest_hash": H2,
        "created_by": "operator-001",
        "created_at": T0,
        "status": PlanStatus.REVIEWABLE,
        "previous_plan_hash": None,
    }
    values.update(changes)
    return VisiblePlan(**values)


def make_approval(**changes: object) -> HumanApproval:
    values: dict[str, object] = {
        "approval_schema_version": 1,
        "approval_id": "approval-001",
        "case_id": "case-001",
        "case_version": 1,
        "case_hash": H1,
        "scope_id": "scope-001",
        "scope_version": 1,
        "scope_hash": H2,
        "plan_id": "plan-001",
        "plan_version": 1,
        "plan_hash": H3,
        "policy_version": "policy-1",
        "canonical_policy_input_hash": H4,
        "adapter_manifest_version": "manifest-1",
        "adapter_manifest_hash": H1,
        "operator_identity": "operator-001",
        "operator_session_id": "session-001",
        "approved_at": T0,
        "expires_at": T2,
        "nonce": "nonce-001",
        "approved_action_identities": ("action-001",),
        "status_at_issue": ApprovalStatus.ACTIVE,
    }
    values.update(changes)
    return HumanApproval(**values)


def make_request(**changes: object) -> ApprovedExecutionRequest:
    arguments = changes.pop("normalized_arguments", {"query": "alpha", "result_limit": 2})
    resource = changes.pop(
        "resource_identity",
        {"resource_id": "resource-001", "resource_type": "DOCUMENT"},
    )
    values: dict[str, object] = {
        "schema_version": 1,
        "execution_id": "execution-001",
        "case_id": "case-001",
        "case_hash": H1,
        "scope_id": "scope-001",
        "scope_hash": H2,
        "plan_id": "plan-001",
        "plan_hash": H3,
        "approval_id": "approval-001",
        "approval_hash": H4,
        "approval_nonce": "nonce-001",
        "operator_session_id": "session-001",
        "action_id": "action-001",
        "step_id": "step-001",
        "policy_version": "policy-1",
        "policy_decision_id": "policy-decision-001",
        "policy_decision_hash": H1,
        "adapter_id": "adapter-001",
        "adapter_version": "1.0.0",
        "adapter_manifest_version": "manifest-1",
        "adapter_manifest_hash": H2,
        "adapter_entry_hash": H3,
        "normalized_arguments": arguments,
        "arguments_hash": hash_normalized_arguments(arguments),
        "resource_identity": resource,
        "resource_hash": hash_resource_identity(resource),
        "resource_limits": {"maximum_results": 2, "timeout_seconds": 10},
        "resource_reservation_id": "reservation-001",
        "resource_reservation_hash": H4,
        "exact_destination": "api.example.invalid",
        "protocol": "https",
        "evidence_policy_id": "evidence-policy-1",
        "evidence_policy_hash": H1,
        "redaction_policy_id": "redaction-policy-1",
        "redaction_policy_hash": H2,
        "audit_policy_id": "audit-policy-1",
        "audit_policy_hash": H3,
        "kill_switch_snapshot": {"generation": 7, "writes_enabled": False},
        "created_at": T0,
        "expires_at": T1,
    }
    values.update(changes)
    return ApprovedExecutionRequest(**values)


def make_bound_contracts() -> tuple[Case, ExactScope, VisiblePlan, HumanApproval, ApprovedExecutionRequest]:
    case = make_case()
    scope = make_scope(case_id=case.case_id, scope_id=case.scope_id)
    plan = make_plan(case_id=case.case_id, scope_id=scope.scope_id, policy_version=case.policy_version)
    approval = make_approval(
        case_id=case.case_id,
        case_version=case.case_version,
        case_hash=case.case_hash,
        scope_id=scope.scope_id,
        scope_version=scope.scope_version,
        scope_hash=scope.scope_hash,
        plan_id=plan.plan_id,
        plan_version=plan.plan_version,
        plan_hash=plan.plan_hash,
        policy_version=plan.policy_version,
        adapter_manifest_version=plan.adapter_manifest_version,
        adapter_manifest_hash=plan.adapter_manifest_hash,
    )
    step = plan.ordered_steps[0]
    request = make_request(
        case_id=case.case_id,
        case_hash=case.case_hash,
        scope_id=scope.scope_id,
        scope_hash=scope.scope_hash,
        plan_id=plan.plan_id,
        plan_hash=plan.plan_hash,
        approval_id=approval.approval_id,
        approval_hash=approval.approval_hash,
        approval_nonce=approval.nonce,
        operator_session_id=approval.operator_session_id,
        action_id=approval.approved_action_identities[0],
        step_id=step.step_id,
        policy_version=plan.policy_version,
        adapter_id=step.adapter_id,
        adapter_version=step.adapter_version,
        adapter_manifest_version=plan.adapter_manifest_version,
        adapter_manifest_hash=plan.adapter_manifest_hash,
        adapter_entry_hash=step.adapter_entry_hash,
        normalized_arguments=step.to_dict()["normalized_arguments"],
        resource_identity=step.to_dict()["resource_identity"],
        resource_limits=step.to_dict()["limits"],
        exact_destination=step.destination,
        protocol=step.protocol,
        evidence_policy_id=step.evidence_policy,
    )
    return case, scope, plan, approval, request


class CanonicalSerializationTests(TestCase):
    def test_identical_semantic_object_has_identical_bytes(self) -> None:
        self.assertEqual(canonical_json_bytes({"a": 1}), canonical_json_bytes({"a": 1}))

    def test_dictionary_key_order_does_not_change_bytes(self) -> None:
        self.assertEqual(canonical_json_bytes({"b": 2, "a": 1}), canonical_json_bytes({"a": 1, "b": 2}))

    def test_array_order_remains_significant(self) -> None:
        self.assertNotEqual(canonical_json_bytes([1, 2]), canonical_json_bytes([2, 1]))

    def test_float_is_rejected(self) -> None:
        with self.assertRaises(CanonicalSerializationError):
            canonical_json_bytes({"value": 1.25})

    def test_nan_is_rejected(self) -> None:
        with self.assertRaises(CanonicalSerializationError):
            canonical_json_bytes(float("nan"))

    def test_positive_infinity_is_rejected(self) -> None:
        with self.assertRaises(CanonicalSerializationError):
            canonical_json_bytes(float("inf"))

    def test_negative_infinity_is_rejected(self) -> None:
        with self.assertRaises(CanonicalSerializationError):
            canonical_json_bytes(float("-inf"))

    def test_unsupported_object_is_rejected(self) -> None:
        with self.assertRaises(CanonicalSerializationError):
            canonical_json_bytes(object())

    def test_bytes_are_not_implicitly_decoded(self) -> None:
        with self.assertRaises(CanonicalSerializationError):
            canonical_json_bytes(b"alpha")

    def test_set_is_not_implicitly_sorted(self) -> None:
        with self.assertRaises(CanonicalSerializationError):
            canonical_json_bytes({"alpha", "beta"})

    def test_callable_is_rejected(self) -> None:
        with self.assertRaises(CanonicalSerializationError):
            canonical_json_bytes(lambda: None)

    def test_non_string_object_key_is_rejected(self) -> None:
        with self.assertRaises(CanonicalSerializationError):
            canonical_json_bytes({1: "alpha"})

    def test_utf8_is_deterministic_and_not_ascii_escaped(self) -> None:
        value = canonical_json_bytes({"city": "Łódź"})
        self.assertEqual('{"city":"Łódź"}'.encode(), value)

    def test_domain_separation_changes_hash_for_same_payload(self) -> None:
        payload = {"id": "one"}
        self.assertNotEqual(domain_separated_sha256(AOIA_CASE_V1, payload), domain_separated_sha256(AOIA_EXACT_SCOPE_V1, payload))

    def test_canonical_hash_is_stable_across_repeated_calls(self) -> None:
        hashes = {domain_separated_sha256(AOIA_CASE_V1, {"b": 2, "a": 1}) for _ in range(10)}
        self.assertEqual(1, len(hashes))

    def test_domain_is_part_of_exact_preimage(self) -> None:
        payload = {"a": 1}
        expected = hashlib.sha256(AOIA_CASE_V1.encode("ascii") + b"\0" + canonical_json_bytes(payload)).hexdigest()
        self.assertEqual(expected, domain_separated_sha256(AOIA_CASE_V1, payload))

    def test_malformed_domain_is_rejected(self) -> None:
        with self.assertRaises(CanonicalSerializationError):
            domain_separated_sha256("bad domain", {})

    def test_cyclic_value_is_rejected(self) -> None:
        value: list[object] = []
        value.append(value)
        with self.assertRaises(CanonicalSerializationError):
            canonical_json_bytes(value)

    def test_freeze_json_is_deeply_immutable(self) -> None:
        frozen = freeze_json({"outer": {"values": [1, 2]}})
        self.assertIsInstance(frozen, FrozenDict)
        with self.assertRaises(TypeError):
            frozen["outer"] = {}  # type: ignore[index]
        with self.assertRaises(TypeError):
            frozen["outer"]["values"][0] = 9  # type: ignore[index]

    def test_thaw_json_returns_defensive_copies(self) -> None:
        frozen = freeze_json({"values": [1, 2]})
        first = thaw_json(frozen)
        second = thaw_json(frozen)
        first["values"].append(3)
        self.assertEqual([1, 2], second["values"])

    def test_manually_forged_frozen_mapping_with_duplicate_keys_is_rejected(self) -> None:
        with self.assertRaises(CanonicalSerializationError):
            FrozenDict((("same", 1), ("same", 2)))

    def test_frozen_mapping_defensively_copies_mutable_constructor_values(self) -> None:
        source = [1, 2]
        frozen = FrozenDict((("values", source),))
        source.append(3)
        self.assertEqual([1, 2], thaw_json(frozen)["values"])

    def test_frozen_mapping_constructor_enforces_container_bound(self) -> None:
        entries = tuple((f"key-{index:05d}", index) for index in range(10_001))
        with self.assertRaises(CanonicalSerializationError):
            FrozenDict(entries)

    def test_frozen_mapping_constructor_validates_key_utf8(self) -> None:
        with self.assertRaises(CanonicalSerializationError):
            FrozenDict((("\ud800", 1),))

    def test_frozen_mapping_subclass_is_not_a_canonical_value(self) -> None:
        class FrozenDictSubclass(FrozenDict):
            pass

        with self.assertRaises(CanonicalSerializationError):
            canonical_json_bytes(FrozenDictSubclass((("key", "value"),)))

    def test_sha256_validator_requires_lowercase_hex(self) -> None:
        self.assertEqual(H1, require_sha256(H1, field_name="digest"))
        with self.assertRaises(CanonicalSerializationError):
            require_sha256("A" * 64, field_name="digest")

    def test_hash_compare_rejects_malformed_claims(self) -> None:
        self.assertTrue(hashes_equal(H1, H1))
        self.assertFalse(hashes_equal(H1, H2))
        self.assertFalse(hashes_equal("bad", "bad"))


class CaseContractTests(TestCase):
    def test_valid_case_passes(self) -> None:
        self.assertTrue(make_case().verify_hash())

    def test_case_is_frozen(self) -> None:
        case = make_case()
        with self.assertRaises(FrozenInstanceError):
            case.purpose = "changed"  # type: ignore[misc]

    def test_empty_case_id_is_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_case(case_id="")

    def test_case_version_zero_is_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_case(case_version=0)

    def test_non_utc_timestamp_is_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_case(created_at="2026-08-07T10:00:00+00:00")

    def test_noncanonical_fraction_is_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_case(created_at="2026-08-07T10:00:00.000Z")

    def test_invalid_authorization_window_is_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_case(authorization_valid_until=T0)

    def test_terminal_status_requires_closure_reason(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_case(status=CaseStatus.CLOSED)

    def test_open_status_rejects_closure_reason(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_case(closure_reason="not closed")

    def test_suspended_case_is_not_terminal(self) -> None:
        self.assertEqual(CaseStatus.SUSPENDED, make_case(status=CaseStatus.SUSPENDED).status)

    def test_version_after_one_requires_previous_hash(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_case(case_version=2)

    def test_version_one_rejects_previous_hash(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_case(previous_case_hash=H1)

    def test_case_hash_recomputes_exactly(self) -> None:
        case = make_case()
        self.assertEqual(case.case_hash, case.compute_hash())

    def test_semantic_copy_changes_case_hash(self) -> None:
        case = make_case()
        changed = replace(case, purpose="Different bounded purpose")
        self.assertNotEqual(case.case_hash, changed.case_hash)

    def test_stale_claimed_case_hash_is_rejected(self) -> None:
        payload = make_case().to_dict()
        payload["purpose"] = "Changed after hashing"
        with self.assertRaises(AuthorityHashMismatch):
            Case.from_dict(payload)

    def test_case_from_dict_round_trip(self) -> None:
        case = make_case()
        self.assertEqual(case, Case.from_dict(case.to_dict()))

    def test_case_from_dict_rejects_unknown_field(self) -> None:
        payload = make_case().to_dict()
        payload["authority"] = True
        with self.assertRaises(AuthorityContractError):
            Case.from_dict(payload)

    def test_case_from_dict_rejects_missing_hash(self) -> None:
        payload = make_case().to_dict()
        payload.pop("case_hash")
        with self.assertRaises(AuthorityContractError):
            Case.from_dict(payload)

    def test_case_carries_no_execution_authority_field(self) -> None:
        self.assertNotIn("execution_authority", make_case().to_dict())


class ExactScopeContractTests(TestCase):
    def test_valid_scope_passes(self) -> None:
        self.assertTrue(make_scope().verify_hash())

    def test_scope_is_frozen(self) -> None:
        scope = make_scope()
        with self.assertRaises(FrozenInstanceError):
            scope.maximum_requests = 99  # type: ignore[misc]

    def test_duplicate_subjects_are_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_scope(allowed_subjects=("subject-001", "subject-001"))

    def test_duplicate_resources_are_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_scope(allowed_resources=("resource-001", "resource-001"))

    def test_duplicate_operations_are_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_scope(allowed_operations=("READ", "READ"))

    def test_negative_resource_limit_is_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_scope(maximum_storage_bytes=-1)

    def test_float_resource_limit_is_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_scope(maximum_cost=math.nan)

    def test_boolean_resource_limit_is_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_scope(maximum_requests=True)

    def test_noncanonical_set_order_is_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_scope(allowed_operations=("WRITE", "READ"))

    def test_mutable_set_like_list_is_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_scope(allowed_operations=["READ"])

    def test_wildcard_allow_is_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_scope(allowed_destinations=("*.example.invalid",))

    def test_version_after_one_requires_previous_hash(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_scope(scope_version=2)

    def test_scope_hash_is_stable(self) -> None:
        self.assertEqual(make_scope().scope_hash, make_scope().scope_hash)

    def test_semantic_scope_change_changes_hash(self) -> None:
        scope = make_scope()
        changed = replace(scope, maximum_requests=scope.maximum_requests + 1)
        self.assertNotEqual(scope.scope_hash, changed.scope_hash)

    def test_stale_scope_hash_is_rejected(self) -> None:
        payload = make_scope().to_dict()
        payload["maximum_requests"] += 1
        with self.assertRaises(AuthorityHashMismatch):
            ExactScope.from_dict(payload)

    def test_scope_from_dict_round_trip(self) -> None:
        scope = make_scope()
        self.assertEqual(scope, ExactScope.from_dict(scope.to_dict()))

    def test_invalid_time_window_is_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_scope(allowed_time_window=(T1, T0))

    def test_explicit_denials_are_preserved(self) -> None:
        self.assertEqual(("network-write", "shell"), make_scope(explicit_denials=("network-write", "shell")).explicit_denials)

    def test_duplicate_network_permission_is_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_scope(network_permissions=("HTTPS_ALLOWLIST_ONLY", "HTTPS_ALLOWLIST_ONLY"))

    def test_scope_has_no_expansion_method(self) -> None:
        self.assertFalse(hasattr(make_scope(), "expand"))


class PlanContractTests(TestCase):
    def test_valid_plan_step_passes(self) -> None:
        self.assertTrue(make_step().verify_hash())

    def test_plan_step_arguments_are_deeply_immutable(self) -> None:
        step = make_step(normalized_arguments={"nested": {"values": [1, 2]}})
        with self.assertRaises(TypeError):
            step.normalized_arguments["nested"]["values"][0] = 9

    def test_plan_step_defensively_copies_arguments(self) -> None:
        source = {"nested": {"values": [1, 2]}}
        step = make_step(normalized_arguments=source)
        original_hash = step.step_hash
        source["nested"]["values"].append(3)
        self.assertEqual(original_hash, step.step_hash)
        self.assertEqual([1, 2], step.to_dict()["normalized_arguments"]["nested"]["values"])

    def test_argument_hash_mismatch_is_rejected(self) -> None:
        payload = make_step().to_dict()
        payload["arguments_hash"] = H4
        with self.assertRaises(AuthorityHashMismatch):
            PlanStep.from_dict(payload)

    def test_resource_hash_mismatch_is_rejected(self) -> None:
        payload = make_step().to_dict()
        payload["resource_hash"] = H4
        with self.assertRaises(AuthorityHashMismatch):
            PlanStep.from_dict(payload)

    def test_stale_step_hash_is_rejected(self) -> None:
        payload = make_step().to_dict()
        payload["operation"] = "INSPECT"
        with self.assertRaises(AuthorityHashMismatch):
            PlanStep.from_dict(payload)

    def test_step_index_must_be_nonnegative(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_step(step_index=-1)

    def test_expected_output_rejects_float(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_step(expected_output={"score": 0.5})

    def test_arguments_reject_callable(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_step(normalized_arguments={"callback": lambda: None})

    def test_valid_visible_plan_passes(self) -> None:
        self.assertTrue(make_plan().verify_hash())

    def test_duplicate_step_ids_are_rejected(self) -> None:
        steps = (make_step(0, "same"), make_step(1, "same"))
        with self.assertRaises(AuthorityContractError):
            make_plan(ordered_steps=steps)

    def test_plan_step_subclass_is_rejected_without_dispatch(self) -> None:
        class HostilePlanStep(PlanStep):
            def verify_hash(self) -> bool:
                raise AssertionError("subclass method must not be called")

        payload = make_step().to_dict()
        for field_name in ("arguments_hash", "resource_hash", "step_hash"):
            payload.pop(field_name)
        hostile = HostilePlanStep(**payload)
        with self.assertRaises(AuthorityContractError):
            make_plan(ordered_steps=(hostile,))

    def test_duplicate_step_indexes_are_rejected(self) -> None:
        steps = (make_step(0, "one"), make_step(0, "two"))
        with self.assertRaises(AuthorityContractError):
            make_plan(ordered_steps=steps)

    def test_noncontiguous_step_indexes_are_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_plan(ordered_steps=(make_step(1),))

    def test_plan_step_order_changes_plan_hash(self) -> None:
        first = make_step(0, "one", normalized_arguments={"value": 1})
        second = make_step(1, "two", normalized_arguments={"value": 2})
        original = make_plan(ordered_steps=(first, second))
        reordered = make_plan(
            ordered_steps=(replace(second, step_index=0), replace(first, step_index=1))
        )
        self.assertNotEqual(original.plan_hash, reordered.plan_hash)

    def test_manifest_hash_participates_in_plan_hash(self) -> None:
        self.assertNotEqual(make_plan().plan_hash, make_plan(adapter_manifest_hash=H3).plan_hash)

    def test_policy_version_participates_in_plan_hash(self) -> None:
        self.assertNotEqual(make_plan().plan_hash, make_plan(policy_version="policy-2").plan_hash)

    def test_plan_is_frozen(self) -> None:
        plan = make_plan()
        with self.assertRaises(FrozenInstanceError):
            plan.status = PlanStatus.APPROVED  # type: ignore[misc]

    def test_stale_plan_hash_is_rejected(self) -> None:
        payload = make_plan().to_dict()
        payload["policy_version"] = "policy-2"
        with self.assertRaises(AuthorityHashMismatch):
            VisiblePlan.from_dict(payload)

    def test_plan_from_dict_round_trip(self) -> None:
        plan = make_plan()
        self.assertEqual(plan, VisiblePlan.from_dict(plan.to_dict()))

    def test_plan_version_after_one_requires_previous_hash(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_plan(plan_version=2)

    def test_plan_to_dict_is_defensive(self) -> None:
        plan = make_plan()
        payload = plan.to_dict()
        payload["ordered_steps"][0]["normalized_arguments"]["query"] = "changed"
        self.assertEqual("alpha", plan.to_dict()["ordered_steps"][0]["normalized_arguments"]["query"])


class HumanApprovalContractTests(TestCase):
    def test_valid_approval_issuance_passes(self) -> None:
        self.assertTrue(make_approval().verify_hash())

    def test_status_other_than_active_is_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_approval(status_at_issue=ApprovalStatus.REVOKED)

    def test_maximum_uses_below_one_is_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_approval(maximum_uses=0)

    def test_default_semantic_maximum_uses_is_one(self) -> None:
        self.assertEqual(1, make_approval().maximum_uses)

    def test_unknown_approval_schema_version_is_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_approval(approval_schema_version=2)

    def test_duplicate_action_identities_are_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_approval(approved_action_identities=("action-001", "action-001"))

    def test_empty_action_identities_are_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_approval(approved_action_identities=())

    def test_expiry_before_approval_is_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_approval(expires_at=T0)

    def test_nonce_is_required(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_approval(nonce="")

    def test_changing_action_identity_changes_hash(self) -> None:
        self.assertNotEqual(make_approval().approval_hash, make_approval(approved_action_identities=("action-002",)).approval_hash)

    def test_stale_approval_hash_is_rejected(self) -> None:
        payload = make_approval().to_dict()
        payload["maximum_uses"] = 2
        with self.assertRaises(AuthorityHashMismatch):
            HumanApproval.from_dict(payload)

    def test_approval_from_dict_round_trip(self) -> None:
        approval = make_approval()
        self.assertEqual(approval, HumanApproval.from_dict(approval.to_dict()))

    def test_approval_is_frozen(self) -> None:
        approval = make_approval()
        with self.assertRaises(FrozenInstanceError):
            approval.maximum_uses = 2  # type: ignore[misc]

    def test_approval_has_no_consume_method(self) -> None:
        self.assertFalse(hasattr(make_approval(), "consume"))


def _approval_hash_binding_test(field_name: str, replacement: object):
    def test(self: HumanApprovalContractTests) -> None:
        original = make_approval()
        changed = replace(original, **{field_name: replacement})
        self.assertNotEqual(original.approval_hash, changed.approval_hash)

    return test


for _field_name, _replacement in (
    ("scope_hash", H3),
    ("plan_hash", H4),
    ("case_hash", H2),
    ("adapter_manifest_hash", H2),
    ("adapter_manifest_version", "manifest-2"),
    ("canonical_policy_input_hash", H1),
    ("operator_session_id", "session-002"),
    ("policy_version", "policy-2"),
):
    setattr(
        HumanApprovalContractTests,
        f"test_{_field_name}_participates_in_approval_hash",
        _approval_hash_binding_test(_field_name, _replacement),
    )


class ApprovedExecutionRequestTests(TestCase):
    def test_valid_inert_request_passes(self) -> None:
        self.assertTrue(make_request().verify_hash())

    def test_unknown_request_schema_version_is_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_request(schema_version=2)

    def test_request_is_deeply_immutable(self) -> None:
        request = make_request(normalized_arguments={"nested": {"items": [1]}})
        with self.assertRaises(TypeError):
            request.normalized_arguments["nested"]["items"][0] = 2

    def test_stale_execution_request_hash_is_rejected(self) -> None:
        payload = make_request().to_dict()
        payload["exact_destination"] = "other.example.invalid"
        with self.assertRaises(AuthorityHashMismatch):
            ApprovedExecutionRequest.from_dict(payload)

    def test_request_from_dict_round_trip(self) -> None:
        request = make_request()
        self.assertEqual(request, ApprovedExecutionRequest.from_dict(request.to_dict()))

    def test_callable_cannot_enter_request(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_request(normalized_arguments={"callable": lambda: None})

    def test_float_cannot_enter_request(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_request(resource_limits={"quota": 1.5})

    def test_request_resource_identity_requires_resource_id(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_request(resource_identity={"resource_type": "DOCUMENT"})

    def test_request_resource_identity_requires_resource_type(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_request(resource_identity={"resource_id": "resource-001"})

    def test_request_resource_identity_fields_are_text(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_request(
                resource_identity={"resource_id": "resource-001", "resource_type": 7}
            )

    def test_arguments_hash_mismatch_is_rejected(self) -> None:
        with self.assertRaises(AuthorityHashMismatch):
            make_request(arguments_hash=H1)

    def test_resource_hash_mismatch_is_rejected(self) -> None:
        with self.assertRaises(AuthorityHashMismatch):
            make_request(resource_hash=H1)

    def test_expiry_must_follow_creation(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_request(expires_at=T0)

    def test_unknown_external_field_is_rejected(self) -> None:
        payload = make_request().to_dict()
        payload["environment"] = {"PATH": "/tmp"}
        with self.assertRaises(AuthorityContractError):
            ApprovedExecutionRequest.from_dict(payload)

    def test_request_is_frozen(self) -> None:
        request = make_request()
        with self.assertRaises(FrozenInstanceError):
            request.adapter_id = "other"  # type: ignore[misc]

    def test_request_to_dict_is_defensive(self) -> None:
        request = make_request()
        payload = request.to_dict()
        payload["kill_switch_snapshot"]["generation"] = 99
        self.assertEqual(7, request.to_dict()["kill_switch_snapshot"]["generation"])

    def test_request_has_no_execute_method(self) -> None:
        self.assertFalse(hasattr(make_request(), "execute"))

    def test_argument_material_and_hash_participate_in_request_hash(self) -> None:
        self.assertNotEqual(
            make_request().execution_request_hash,
            make_request(normalized_arguments={"query": "beta", "result_limit": 2}).execution_request_hash,
        )

    def test_resource_material_and_hash_participate_in_request_hash(self) -> None:
        self.assertNotEqual(
            make_request().execution_request_hash,
            make_request(resource_identity={"resource_id": "resource-002", "resource_type": "DOCUMENT"}).execution_request_hash,
        )


def _request_hash_binding_test(field_name: str, replacement: object):
    def test(self: ApprovedExecutionRequestTests) -> None:
        original = make_request()
        changed = replace(original, **{field_name: replacement})
        self.assertNotEqual(original.execution_request_hash, changed.execution_request_hash)

    return test


for _field_name, _replacement in (
    ("approval_hash", H1),
    ("adapter_entry_hash", H4),
    ("policy_decision_hash", H2),
    ("resource_reservation_hash", H1),
    ("evidence_policy_hash", H4),
    ("redaction_policy_hash", H4),
    ("audit_policy_hash", H4),
    ("kill_switch_snapshot", {"generation": 8, "writes_enabled": False}),
    ("adapter_manifest_hash", H3),
):
    setattr(
        ApprovedExecutionRequestTests,
        f"test_{_field_name}_participates_in_request_hash",
        _request_hash_binding_test(_field_name, _replacement),
    )


class AuthorityBindingTests(TestCase):
    @staticmethod
    def _approval_for_plan(approval: HumanApproval, plan: VisiblePlan) -> HumanApproval:
        return replace(approval, plan_hash=plan.plan_hash)

    def _assert_step_outside_scope(self, **step_changes: object) -> None:
        case, scope, plan, approval, _request = make_bound_contracts()
        step = replace(plan.ordered_steps[0], **step_changes)
        changed_plan = replace(plan, ordered_steps=(step,))
        changed_approval = self._approval_for_plan(approval, changed_plan)
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(
                case=case,
                scope=scope,
                plan=changed_plan,
                approval=changed_approval,
            )

    def test_exact_contract_chain_passes(self) -> None:
        case, scope, plan, approval, request = make_bound_contracts()
        self.assertIsNone(
            validate_authority_bindings(
                case=case,
                scope=scope,
                plan=plan,
                approval=approval,
                request=request,
            )
        )

    def test_contract_subclass_is_rejected_without_dynamic_dispatch(self) -> None:
        class HostileCase(Case):
            def verify_hash(self) -> bool:
                raise AssertionError("subclass method must not be called")

        case, scope, plan, approval, request = make_bound_contracts()
        payload = case.to_dict()
        payload.pop("case_hash")
        hostile = HostileCase(**payload)
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(
                case=hostile,
                scope=scope,
                plan=plan,
                approval=approval,
                request=request,
            )

    def test_issuance_chain_can_be_checked_before_request_exists(self) -> None:
        case, scope, plan, approval, _request = make_bound_contracts()
        self.assertIsNone(
            validate_authority_bindings(
                case=case,
                scope=scope,
                plan=plan,
                approval=approval,
            )
        )

    def test_scope_mutation_breaks_approval_binding(self) -> None:
        case, scope, plan, approval, request = make_bound_contracts()
        mutated_scope = replace(scope, maximum_requests=scope.maximum_requests + 1)
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(case=case, scope=mutated_scope, plan=plan, approval=approval, request=request)

    def test_plan_mutation_breaks_approval_binding(self) -> None:
        case, scope, plan, approval, request = make_bound_contracts()
        mutated_plan = replace(plan, policy_version="policy-2")
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(case=case, scope=scope, plan=mutated_plan, approval=approval, request=request)

    def test_unapproved_action_is_rejected(self) -> None:
        case, scope, plan, approval, request = make_bound_contracts()
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(case=case, scope=scope, plan=plan, approval=approval, request=replace(request, action_id="action-002"))

    def test_cross_session_request_is_rejected(self) -> None:
        case, scope, plan, approval, request = make_bound_contracts()
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(case=case, scope=scope, plan=plan, approval=approval, request=replace(request, operator_session_id="session-002"))

    def test_request_outside_approval_expiry_is_rejected(self) -> None:
        case, scope, plan, approval, request = make_bound_contracts()
        short_approval = replace(approval, expires_at=T1)
        long_request = replace(request, expires_at=T2)
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(case=case, scope=scope, plan=plan, approval=short_approval, request=long_request)

    def test_adapter_substitution_is_rejected(self) -> None:
        case, scope, plan, approval, request = make_bound_contracts()
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(case=case, scope=scope, plan=plan, approval=approval, request=replace(request, adapter_id="adapter-002"))

    def test_argument_substitution_is_rejected(self) -> None:
        case, scope, plan, approval, request = make_bound_contracts()
        arguments = {"query": "substituted", "result_limit": 2}
        substituted = replace(
            request,
            normalized_arguments=arguments,
            arguments_hash=hash_normalized_arguments(arguments),
        )
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(case=case, scope=scope, plan=plan, approval=approval, request=substituted)

    def test_resource_limit_substitution_is_rejected(self) -> None:
        case, scope, plan, approval, request = make_bound_contracts()
        substituted = replace(request, resource_limits={"maximum_results": 3, "timeout_seconds": 10})
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(case=case, scope=scope, plan=plan, approval=approval, request=substituted)

    def test_destination_substitution_is_rejected(self) -> None:
        case, scope, plan, approval, request = make_bound_contracts()
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(case=case, scope=scope, plan=plan, approval=approval, request=replace(request, exact_destination="other.example.invalid"))

    def test_closed_case_is_rejected_by_structural_chain(self) -> None:
        case, scope, plan, approval, request = make_bound_contracts()
        closed = replace(case, status=CaseStatus.CLOSED, closure_reason="completed")
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(case=closed, scope=scope, plan=plan, approval=approval, request=request)

    def test_authorization_subject_outside_scope_is_rejected(self) -> None:
        case, scope, plan, approval, _request = make_bound_contracts()
        changed_scope = replace(scope, allowed_subjects=("subject-002",))
        changed_approval = replace(approval, scope_hash=changed_scope.scope_hash)
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(
                case=case,
                scope=changed_scope,
                plan=plan,
                approval=changed_approval,
            )

    def test_scope_window_cannot_exceed_case_authorization(self) -> None:
        case, scope, plan, approval, _request = make_bound_contracts()
        changed_scope = replace(scope, allowed_time_window=(T0, T3))
        changed_approval = replace(approval, scope_hash=changed_scope.scope_hash)
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(
                case=case,
                scope=changed_scope,
                plan=plan,
                approval=changed_approval,
            )

    def test_plan_classification_must_match_case(self) -> None:
        case, scope, plan, approval, _request = make_bound_contracts()
        changed_plan = replace(plan, data_classification="PUBLIC")
        changed_approval = self._approval_for_plan(approval, changed_plan)
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(
                case=case,
                scope=scope,
                plan=changed_plan,
                approval=changed_approval,
            )

    def test_adapter_outside_scope_is_rejected(self) -> None:
        self._assert_step_outside_scope(adapter_id="adapter-002")

    def test_operation_outside_scope_is_rejected(self) -> None:
        self._assert_step_outside_scope(operation="WRITE")

    def test_resource_outside_scope_is_rejected(self) -> None:
        self._assert_step_outside_scope(
            resource_identity={"resource_id": "resource-002", "resource_type": "DOCUMENT"}
        )

    def test_resource_type_outside_scope_is_rejected(self) -> None:
        self._assert_step_outside_scope(
            resource_identity={"resource_id": "resource-001", "resource_type": "IMAGE"}
        )

    def test_destination_outside_scope_is_rejected(self) -> None:
        self._assert_step_outside_scope(destination="other.example.invalid")

    def test_protocol_outside_scope_is_rejected(self) -> None:
        self._assert_step_outside_scope(protocol="http")

    def test_step_limits_cannot_exceed_scope(self) -> None:
        self._assert_step_outside_scope(
            limits={"maximum_results": 11, "timeout_seconds": 10}
        )

    def test_unknown_step_limit_fails_closed(self) -> None:
        self._assert_step_outside_scope(limits={"unbound_limit": 1})

    def test_plan_limits_cannot_exceed_scope(self) -> None:
        case, scope, plan, approval, _request = make_bound_contracts()
        changed_plan = replace(plan, limits={"maximum_requests": 3})
        changed_approval = self._approval_for_plan(approval, changed_plan)
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(
                case=case,
                scope=scope,
                plan=changed_plan,
                approval=changed_approval,
            )

    def test_step_limits_cannot_exceed_stricter_visible_plan(self) -> None:
        case, scope, plan, approval, _request = make_bound_contracts()
        changed_plan = replace(plan, limits={"maximum_results": 1})
        changed_approval = self._approval_for_plan(approval, changed_plan)
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(
                case=case,
                scope=scope,
                plan=changed_plan,
                approval=changed_approval,
            )

    def test_limit_alias_cannot_bypass_stricter_visible_plan(self) -> None:
        case, scope, plan, approval, _request = make_bound_contracts()
        changed_plan = replace(plan, limits={"maximum_runtime_seconds": 5})
        changed_approval = self._approval_for_plan(approval, changed_plan)
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(
                case=case,
                scope=scope,
                plan=changed_plan,
                approval=changed_approval,
            )

    def test_duplicate_limit_aliases_fail_closed(self) -> None:
        case, scope, plan, approval, _request = make_bound_contracts()
        changed_plan = replace(
            plan,
            limits={"maximum_runtime_seconds": 5, "timeout_seconds": 5},
        )
        changed_approval = self._approval_for_plan(approval, changed_plan)
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(
                case=case,
                scope=scope,
                plan=changed_plan,
                approval=changed_approval,
            )

    def test_approval_must_be_contained_in_scope_window(self) -> None:
        case, scope, plan, approval, _request = make_bound_contracts()
        changed_scope = replace(scope, allowed_time_window=(T0, T1))
        changed_approval = replace(approval, scope_hash=changed_scope.scope_hash)
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(
                case=case,
                scope=changed_scope,
                plan=plan,
                approval=changed_approval,
            )

    def test_approval_cannot_predate_visible_plan(self) -> None:
        case, scope, plan, approval, _request = make_bound_contracts()
        changed_plan = replace(plan, created_at=T1)
        changed_approval = self._approval_for_plan(approval, changed_plan)
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(
                case=case,
                scope=scope,
                plan=changed_plan,
                approval=changed_approval,
            )

    def test_visible_plan_cannot_predate_case_creation(self) -> None:
        case, scope, plan, approval, _request = make_bound_contracts()
        changed_case = replace(case, created_at=T1)
        changed_approval = replace(approval, case_hash=changed_case.case_hash)
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(
                case=changed_case,
                scope=scope,
                plan=plan,
                approval=changed_approval,
            )

    def test_negative_nested_limit_is_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_step(limits={"maximum_results": -1})

    def test_non_integer_nested_limit_is_rejected(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_step(limits={"maximum_results": "two"})

    def test_resource_identity_requires_stable_id_and_type(self) -> None:
        with self.assertRaises(AuthorityContractError):
            make_step(resource_identity={"resource_id": "resource-001"})


class InertnessBoundaryTests(TestCase):
    def test_authority_contract_module_imports_no_executor(self) -> None:
        source = CONTRACT_SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("CanonicalExecutor", source)
        self.assertNotIn("ExecutionEngine", source)

    def test_modules_have_exact_inert_import_surfaces(self) -> None:
        expected = {
            SERIALIZATION_SOURCE: {
                ("from", 0, "__future__", ("annotations",)),
                ("import", 0, "hashlib", ()),
                ("import", 0, "hmac", ()),
                ("import", 0, "json", ()),
                ("import", 0, "re", ()),
                ("from", 0, "collections.abc", ("Iterator", "Mapping")),
                ("from", 0, "dataclasses", ("dataclass",)),
                ("from", 0, "typing", ("Any", "Final")),
            },
            CONTRACT_SOURCE: {
                ("from", 0, "__future__", ("annotations",)),
                ("import", 0, "re", ()),
                ("from", 0, "dataclasses", ("dataclass", "field")),
                ("from", 0, "datetime", ("datetime",)),
                ("from", 0, "enum", ("Enum",)),
                ("from", 0, "typing", ("Any", "ClassVar")),
                (
                    "from",
                    1,
                    "canonical_serialization",
                    (
                        "CanonicalSerializationError",
                        "FrozenDict",
                        "domain_separated_sha256",
                        "freeze_json",
                        "hashes_equal",
                        "require_sha256",
                        "thaw_json",
                    ),
                ),
            },
        }
        for path, allowed in expected.items():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            self.assertEqual(allowed, self._import_specs(tree), path)

    def test_modules_contain_no_effectful_or_dynamic_calls(self) -> None:
        for path in (SERIALIZATION_SOURCE, CONTRACT_SOURCE):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            self.assertEqual(set(), self._effectful_calls(tree), path)

    def test_import_scanner_rejects_internal_and_effectful_imports(self) -> None:
        tree = ast.parse(
            "from runtime.execution.controlled_test_runner import run\n"
            "from runtime.providers.gateway import call\n"
            "from tempfile import NamedTemporaryFile\n"
            "import http.client\n"
        )
        self.assertEqual(4, len(self._import_specs(tree)))
        self.assertTrue(
            all(spec not in self._import_specs(ast.parse(SERIALIZATION_SOURCE.read_text(encoding="utf-8"))) for spec in self._import_specs(tree))
        )

    def test_call_scanner_rejects_dynamic_execution_builtins(self) -> None:
        tree = ast.parse("__import__('subprocess')\neval('1')\nexec('pass')\n")
        self.assertEqual({"__import__", "eval", "exec"}, self._call_names(tree))
        self.assertEqual({"__import__", "eval", "exec"}, self._effectful_calls(tree))

    def test_contracts_expose_no_execution_method(self) -> None:
        for contract in (Case, ExactScope, PlanStep, VisiblePlan, HumanApproval, ApprovedExecutionRequest):
            with self.subTest(contract=contract.__name__):
                self.assertFalse(hasattr(contract, "execute"))
                self.assertFalse(hasattr(contract, "dispatch"))
                self.assertFalse(hasattr(contract, "invoke"))

    def test_construction_and_hashing_do_not_open_files(self) -> None:
        with patch("builtins.open", side_effect=AssertionError("unexpected I/O")):
            self.assertTrue(make_case().verify_hash())
            self.assertTrue(make_scope().verify_hash())
            self.assertTrue(make_plan().verify_hash())
            self.assertTrue(make_approval().verify_hash())
            self.assertTrue(make_request().verify_hash())

    def test_required_hash_domains_are_unique(self) -> None:
        domains = {
            AOIA_CASE_V1,
            AOIA_EXACT_SCOPE_V1,
            AOIA_PLAN_STEP_V1,
            AOIA_VISIBLE_PLAN_V1,
            AOIA_HUMAN_EXECUTION_APPROVAL_V1,
            AOIA_APPROVED_EXECUTION_REQUEST_V1,
            AOIA_NORMALIZED_ARGUMENTS_V1,
            AOIA_RESOURCE_IDENTITY_V1,
        }
        self.assertEqual(8, len(domains))

    def test_contracts_use_only_canonical_runtime_namespace(self) -> None:
        for contract in (Case, ExactScope, PlanStep, VisiblePlan, HumanApproval, ApprovedExecutionRequest):
            self.assertEqual("runtime.execution.authority_contracts", contract.__module__)

    def test_compatibility_namespace_imports_fail_closed(self) -> None:
        for module_name in (
            "execution.canonical_serialization",
            "execution.authority_contracts",
        ):
            with self.subTest(module_name=module_name), self.assertRaises(ImportError):
                importlib.import_module(module_name)

    @staticmethod
    def _import_specs(
        tree: ast.AST,
    ) -> set[tuple[str, int, str, tuple[str, ...]]]:
        specs: set[tuple[str, int, str, tuple[str, ...]]] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    specs.add(("import", 0, alias.name, ()))
            elif isinstance(node, ast.ImportFrom):
                specs.add(
                    (
                        "from",
                        node.level,
                        node.module or "",
                        tuple(alias.name for alias in node.names),
                    )
                )
        return specs

    @staticmethod
    def _call_names(tree: ast.AST) -> set[str]:
        calls: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
        return calls

    @staticmethod
    def _effectful_calls(tree: ast.AST) -> set[str]:
        blocked_names = {"Popen", "__import__", "compile", "eval", "exec", "open"}
        blocked_attributes = {
            "Popen", "connect", "mkdir", "open", "rename", "replace", "request",
            "run", "system", "unlink", "urlopen", "write", "write_bytes", "write_text",
        }
        violations: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id in blocked_names:
                violations.add(node.func.id)
            elif isinstance(node.func, ast.Attribute) and node.func.attr in blocked_attributes:
                violations.add(node.func.attr)
        return violations


if __name__ == "__main__":
    main()
