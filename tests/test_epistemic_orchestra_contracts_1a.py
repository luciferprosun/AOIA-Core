from __future__ import annotations

from dataclasses import replace
import unittest

from runtime.epistemic_orchestra import (
    EpistemicContractError,
    EpistemicRunContract,
    OrchestrationMode,
    StageRole,
    build_epistemic_run_contract,
    canonical_json_bytes,
)
from tests.epistemic_orchestra_test_support_1a import SOURCE_PROMPT, make_run


class EpistemicRunContract1ATests(unittest.TestCase):
    def test_valid_sequential_ring(self):
        self.assertEqual(make_run().orchestration_mode, "SEQUENTIAL_RING_V1")

    def test_valid_independent_panel(self):
        self.assertEqual(
            make_run(mode=OrchestrationMode.INDEPENDENT_PANEL_V1.value).orchestration_mode,
            "INDEPENDENT_PANEL_V1",
        )

    def test_canonical_json_is_deterministic_utf8_and_compact(self):
        left = canonical_json_bytes({"z": "zażółć", "a": [2, 1]})
        right = canonical_json_bytes({"a": [2, 1], "z": "zażółć"})
        self.assertEqual(left, right)
        self.assertEqual(left, b'{"a":[2,1],"z":"za\xc5\xbc\xc3\xb3\xc5\x82\xc4\x87"}')

    def test_run_hash_is_deterministic(self):
        self.assertEqual(make_run().run_hash, make_run().run_hash)

    def test_changed_prompt_changes_run_hash(self):
        self.assertNotEqual(make_run().run_hash, make_run(prompt=SOURCE_PROMPT + " Extra").run_hash)

    def test_changed_knowledge_context_changes_run_hash(self):
        self.assertNotEqual(make_run().run_hash, make_run(context_hash="d" * 64).run_hash)

    def test_changed_stage_plan_changes_run_hash(self):
        changed = build_epistemic_run_contract(
            run_id="run-contract-1",
            orchestration_mode="SEQUENTIAL_RING_V1",
            source_request_hash="a" * 64,
            source_prompt=SOURCE_PROMPT,
            knowledge_context_hash="b" * 64,
            knowledge_profile_hash="c" * 64,
            planned_stage_ids=("stage-primary-0", "stage-critic-X", "stage-primary-2"),
            planned_stage_roles=("PRIMARY", "CRITIC", "PRIMARY"),
        )
        self.assertNotEqual(make_run().run_hash, changed.run_hash)

    def test_duplicate_stage_ids_rejected(self):
        with self.assertRaises(EpistemicContractError):
            build_epistemic_run_contract(
                run_id="run-contract-1",
                orchestration_mode="SEQUENTIAL_RING_V1",
                source_request_hash="a" * 64,
                source_prompt=SOURCE_PROMPT,
                planned_stage_ids=("same", "same"),
                planned_stage_roles=("PRIMARY", "CRITIC"),
            )

    def test_unsupported_mode_rejected(self):
        with self.assertRaises(EpistemicContractError):
            make_run(mode="AUTO_ORCHESTRA")

    def test_unsupported_role_rejected(self):
        with self.assertRaises(EpistemicContractError):
            build_epistemic_run_contract(
                run_id="run-contract-1",
                orchestration_mode="SEQUENTIAL_RING_V1",
                source_request_hash="a" * 64,
                source_prompt=SOURCE_PROMPT,
                planned_stage_ids=("stage-0",),
                planned_stage_roles=("ROUTER",),
            )

    def test_maximum_stage_count_enforced(self):
        with self.assertRaises(EpistemicContractError):
            build_epistemic_run_contract(
                run_id="run-contract-1",
                orchestration_mode="SEQUENTIAL_RING_V1",
                source_request_hash="a" * 64,
                source_prompt=SOURCE_PROMPT,
                planned_stage_ids=("stage-0", "stage-1"),
                planned_stage_roles=("PRIMARY", "CRITIC"),
                maximum_stage_count=1,
            )

    def test_unknown_fields_rejected(self):
        payload = make_run().to_dict()
        payload["provider_id"] = "forged"
        with self.assertRaises(EpistemicContractError):
            EpistemicRunContract.from_dict(payload)

    def test_malformed_hash_rejected(self):
        payload = make_run().to_dict()
        payload["run_hash"] = "bad"
        with self.assertRaises(EpistemicContractError):
            EpistemicRunContract.from_dict(payload)

    def test_forged_authority_field_rejected(self):
        with self.assertRaises(EpistemicContractError):
            replace(make_run(), approval_permitted=True, run_hash="")

    def test_all_authority_flags_remain_false(self):
        run = make_run()
        for name in (
            "provider_output_is_authority",
            "critic_output_is_authority",
            "cpt_output_is_authority",
            "revision_output_is_authority",
            "multi_model_agreement_is_authority",
            "execution_permitted",
            "write_permitted",
            "dispatch_permitted",
            "provider_call_permitted",
            "approval_permitted",
            "gate_mutation_permitted",
            "human_barrier_satisfied",
        ):
            self.assertIs(getattr(run, name), False)
        self.assertIs(run.human_review_required, True)


if __name__ == "__main__":
    unittest.main()
