from __future__ import annotations

from dataclasses import replace
import unittest

from runtime.cpt.transformer import transform_prompt
from runtime.epistemic_orchestra import (
    EMPTY_KNOWLEDGE_CONTEXT_HASH,
    EpistemicContractError,
    EpistemicStageContract,
    OrchestrationMode,
    build_epistemic_stage_contract,
    validate_stage_against_run,
    validate_stage_parent_binding,
    verify_epistemic_stage_chain,
)
from runtime.epistemic_orchestra.contracts import EMPTY_CPT_TRANSFORMATION_HASH, NO_CPT_TRANSFORMATION_ID
from tests.epistemic_orchestra_test_support_1a import (
    SOURCE_PROMPT,
    SOURCE_REVISION_HASH,
    SOURCE_REVISION_ID,
    make_critic_stages,
    make_revision_stage,
    make_run,
    material_payload,
    no_issue_payload,
)


class EpistemicStageHashBinding1ATests(unittest.TestCase):
    def test_valid_first_primary_stage(self):
        run = make_run()
        first, _, _ = make_critic_stages(run)
        self.assertEqual(first.stage_index, 0)
        self.assertEqual(first.stage_role, "PRIMARY")
        self.assertIsNone(first.parent_stage_hash)

    def test_valid_sequential_parent_binding(self):
        run = make_run()
        first, critic1, critic2 = make_critic_stages(run)
        validate_stage_parent_binding(
            critic1, first, parent_revision_hash=SOURCE_REVISION_HASH
        )
        validate_stage_parent_binding(
            critic2, critic1, parent_revision_hash=SOURCE_REVISION_HASH
        )

    def test_valid_independent_panel_common_source_binding(self):
        run = make_run(mode=OrchestrationMode.INDEPENDENT_PANEL_V1.value)
        first, critic1, critic2 = make_critic_stages(run)
        self.assertEqual(critic1.parent_stage_hash, first.stage_hash)
        self.assertEqual(critic2.parent_stage_hash, first.stage_hash)
        self.assertEqual(critic1.source_revision_hash, critic2.source_revision_hash)

    def test_exact_sequential_chain(self):
        run = make_run()
        first, critic1, critic2 = make_critic_stages(run)
        payloads = (material_payload(critic1), no_issue_payload(critic2))
        final = make_revision_stage(run, payloads, first=first, critic2=critic2)
        verify_epistemic_stage_chain(run, (first, critic1, critic2, final))

    def test_exact_panel_chain(self):
        run = make_run(mode=OrchestrationMode.INDEPENDENT_PANEL_V1.value)
        first, critic1, critic2 = make_critic_stages(run)
        payloads = (material_payload(critic1), no_issue_payload(critic2))
        final = make_revision_stage(run, payloads, first=first, critic2=critic2)
        verify_epistemic_stage_chain(run, (first, critic1, critic2, final))

    def test_wrong_run_hash_rejected(self):
        run = make_run()
        _, critic1, _ = make_critic_stages(run)
        stale = replace(critic1, run_hash="d" * 64, stage_hash="")
        with self.assertRaises(EpistemicContractError):
            validate_stage_against_run(stale, run)

    def test_wrong_stage_index_rejected(self):
        run = make_run()
        _, critic1, _ = make_critic_stages(run)
        wrong = replace(critic1, stage_index=2, stage_hash="")
        with self.assertRaises(EpistemicContractError):
            validate_stage_against_run(wrong, run)

    def test_wrong_stage_role_rejected(self):
        run = make_run()
        _, critic1, _ = make_critic_stages(run)
        wrong = replace(
            critic1,
            stage_role="PRIMARY",
            critic_transformation_id=NO_CPT_TRANSFORMATION_ID,
            critic_transformation_hash=EMPTY_CPT_TRANSFORMATION_HASH,
            expected_output_kind="PRIMARY_REVISION",
            bound_critic_payload_hashes=("f" * 64,),
            stage_hash="",
        )
        with self.assertRaises(EpistemicContractError):
            validate_stage_against_run(wrong, run)

    def test_wrong_source_revision_rejected(self):
        run = make_run()
        first, critic1, _ = make_critic_stages(run)
        wrong = replace(
            critic1,
            source_revision_hash="e" * 64,
            parent_revision_hash="e" * 64,
            stage_hash="",
        )
        with self.assertRaises(EpistemicContractError):
            validate_stage_parent_binding(
                wrong, first, parent_revision_hash=SOURCE_REVISION_HASH
            )

    def test_missing_parent_rejected(self):
        run = make_run()
        record = transform_prompt(SOURCE_PROMPT)
        with self.assertRaises(EpistemicContractError):
            build_epistemic_stage_contract(
                run=run,
                stage_index=1,
                source_revision_id=SOURCE_REVISION_ID,
                source_revision_hash=SOURCE_REVISION_HASH,
                critic_transformation_record=record,
            )

    def test_changed_parent_stage_hash_rejected(self):
        run = make_run()
        first, critic1, _ = make_critic_stages(run)
        wrong = replace(critic1, parent_stage_hash="e" * 64, stage_hash="")
        with self.assertRaises(EpistemicContractError):
            validate_stage_parent_binding(
                wrong, first, parent_revision_hash=SOURCE_REVISION_HASH
            )

    def test_changed_parent_revision_hash_rejected(self):
        run = make_run()
        first, critic1, _ = make_critic_stages(run)
        wrong = replace(
            critic1,
            source_revision_hash="e" * 64,
            parent_revision_hash="e" * 64,
            stage_hash="",
        )
        with self.assertRaises(EpistemicContractError):
            validate_stage_parent_binding(
                wrong,
                first,
                parent_revision_hash=SOURCE_REVISION_HASH,
            )

    def test_stage_reordering_rejected(self):
        run = make_run()
        first, critic1, critic2 = make_critic_stages(run)
        payloads = (material_payload(critic1), no_issue_payload(critic2))
        final = make_revision_stage(run, payloads, first=first, critic2=critic2)
        with self.assertRaises(EpistemicContractError):
            verify_epistemic_stage_chain(run, (first, critic2, critic1, final))

    def test_stage_hash_is_deterministic_and_round_trips(self):
        run = make_run()
        _, critic1, _ = make_critic_stages(run)
        restored = EpistemicStageContract.from_dict(critic1.to_dict())
        self.assertEqual(critic1.stage_hash, restored.stage_hash)

    def test_changed_cpt_record_changes_stage_hash(self):
        run = make_run()
        first, _, _ = make_critic_stages(run)
        record = transform_prompt(SOURCE_PROMPT)
        changed = replace(record, provenance_note=record.provenance_note + " changed")
        original = build_epistemic_stage_contract(
            run=run,
            stage_index=1,
            source_revision_id=SOURCE_REVISION_ID,
            source_revision_hash=SOURCE_REVISION_HASH,
            parent_stage=first,
            parent_revision_hash=SOURCE_REVISION_HASH,
            critic_transformation_record=record,
        )
        altered = build_epistemic_stage_contract(
            run=run,
            stage_index=1,
            source_revision_id=SOURCE_REVISION_ID,
            source_revision_hash=SOURCE_REVISION_HASH,
            parent_stage=first,
            parent_revision_hash=SOURCE_REVISION_HASH,
            critic_transformation_record=changed,
        )
        self.assertNotEqual(original.stage_hash, altered.stage_hash)

    def test_explicit_no_knowledge_sentinel_is_a_hash(self):
        self.assertEqual(len(EMPTY_KNOWLEDGE_CONTEXT_HASH), 64)


if __name__ == "__main__":
    unittest.main()
