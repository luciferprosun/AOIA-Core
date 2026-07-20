from __future__ import annotations

from dataclasses import replace
import unittest

from runtime.epistemic_orchestra import (
    EpistemicContractError,
    OrchestrationMode,
    build_epistemic_run_contract,
    compile_revision_request,
    validate_critic_payload_against_stage,
    validate_revision_compilation,
    validate_stage_against_run,
    validate_stage_parent_binding,
    validate_stage_replay_state,
)
from tests.epistemic_orchestra_test_support_1a import (
    SOURCE_PROMPT,
    SOURCE_REVISION_HASH,
    SOURCE_REVISION_ID,
    issue,
    make_critic_stages,
    make_revision_stage,
    make_run,
    material_payload,
    no_issue_payload,
)


class EpistemicReplayRejection1ATests(unittest.TestCase):
    def test_replayed_stage_hash_rejected(self):
        run = make_run()
        _, critic1, _ = make_critic_stages(run)
        with self.assertRaises(EpistemicContractError):
            validate_stage_replay_state(
                critic1,
                consumed_stage_hashes=(critic1.stage_hash,),
            )

    def test_replayed_stage_id_rejected(self):
        run = make_run()
        _, critic1, _ = make_critic_stages(run)
        with self.assertRaises(EpistemicContractError):
            validate_stage_replay_state(
                critic1,
                consumed_stage_ids=(critic1.stage_id,),
            )

    def test_same_payload_cannot_bind_different_stage(self):
        run = make_run()
        _, critic1, critic2 = make_critic_stages(run)
        payload = material_payload(critic1)
        with self.assertRaises(EpistemicContractError):
            validate_critic_payload_against_stage(payload, critic2)

    def test_sequential_result_cannot_bind_another_parent(self):
        run = make_run()
        first, _, critic2 = make_critic_stages(run)
        with self.assertRaises(EpistemicContractError):
            validate_stage_parent_binding(
                critic2,
                first,
                parent_revision_hash=SOURCE_REVISION_HASH,
            )

    def test_stale_parent_hash_rejected(self):
        run = make_run()
        first, critic1, _ = make_critic_stages(run)
        stale = replace(critic1, parent_stage_hash="d" * 64, stage_hash="")
        with self.assertRaises(EpistemicContractError):
            validate_stage_parent_binding(
                stale,
                first,
                parent_revision_hash=SOURCE_REVISION_HASH,
            )

    def test_stale_source_revision_rejected(self):
        run = make_run()
        first, critic1, _ = make_critic_stages(run)
        stale = replace(
            critic1,
            source_revision_hash="d" * 64,
            parent_revision_hash="d" * 64,
            stage_hash="",
        )
        with self.assertRaises(EpistemicContractError):
            validate_stage_parent_binding(
                stale,
                first,
                parent_revision_hash=SOURCE_REVISION_HASH,
            )

    def test_changed_run_plan_invalidates_stage(self):
        run = make_run()
        _, critic1, _ = make_critic_stages(run)
        changed = build_epistemic_run_contract(
            run_id=run.run_id,
            orchestration_mode=run.orchestration_mode,
            source_request_hash=run.source_request_hash,
            source_prompt=SOURCE_PROMPT,
            knowledge_context_hash=run.knowledge_context_hash,
            knowledge_profile_hash=run.knowledge_profile_hash,
            planned_stage_ids=("stage-primary-0", "changed-critic", "stage-critic-2", "stage-primary-3"),
            planned_stage_roles=run.planned_stage_roles,
        )
        with self.assertRaises(EpistemicContractError):
            validate_stage_against_run(critic1, changed)

    def test_independent_panel_output_cannot_substitute_peer(self):
        run = make_run(mode=OrchestrationMode.INDEPENDENT_PANEL_V1.value)
        _, critic1, critic2 = make_critic_stages(run)
        payload = material_payload(critic1)
        with self.assertRaises(EpistemicContractError):
            validate_critic_payload_against_stage(payload, critic2)

    def test_stage_from_another_mode_rejected(self):
        sequential = make_run()
        panel = make_run(mode=OrchestrationMode.INDEPENDENT_PANEL_V1.value)
        _, critic1, _ = make_critic_stages(sequential)
        with self.assertRaises(EpistemicContractError):
            validate_stage_against_run(critic1, panel)

    def test_cross_run_critic_payload_rejected_by_revision_compiler(self):
        run = make_run()
        first, critic1, critic2 = make_critic_stages(run)
        foreign_run = replace(run, run_id="foreign-run", run_hash="")
        foreign_first, foreign_critic1, _ = make_critic_stages(foreign_run)
        foreign_payload = material_payload(foreign_critic1)
        local_payload = no_issue_payload(critic2)
        payloads = (foreign_payload, local_payload)
        stage = make_revision_stage(run, payloads, first=first, critic2=critic2)
        with self.assertRaises(EpistemicContractError):
            compile_revision_request(
                run=run,
                revision_stage=stage,
                source_prompt=SOURCE_PROMPT,
                source_revision_id=SOURCE_REVISION_ID,
                source_revision_hash=SOURCE_REVISION_HASH,
                critic_payloads=payloads,
                accepted_issue_ids=("ISSUE-1",),
            )

    def test_stale_revision_compilation_rejected(self):
        run = make_run()
        first, critic1, critic2 = make_critic_stages(run)
        payloads = (material_payload(critic1, issue("ISSUE-1")), no_issue_payload(critic2))
        stage = make_revision_stage(run, payloads, first=first, critic2=critic2)
        result = compile_revision_request(
            run=run,
            revision_stage=stage,
            source_prompt=SOURCE_PROMPT,
            source_revision_id=SOURCE_REVISION_ID,
            source_revision_hash=SOURCE_REVISION_HASH,
            critic_payloads=payloads,
            accepted_issue_ids=("ISSUE-1",),
        )
        stale = replace(result, source_revision_hash="d" * 64, compilation_hash="")
        with self.assertRaises(EpistemicContractError):
            validate_revision_compilation(
                stale,
                run=run,
                revision_stage=stage,
                critic_payloads=payloads,
                source_prompt=SOURCE_PROMPT,
            )


if __name__ == "__main__":
    unittest.main()
