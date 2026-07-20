from __future__ import annotations

from dataclasses import replace

from runtime.epistemic_orchestra import (
    CriticIssue,
    CriticOutcome,
    EpistemicRunContract,
    EpistemicStageContract,
    OrchestrationMode,
    StageRole,
    build_critic_stage_payload,
    build_epistemic_run_contract,
    build_epistemic_stage_contract,
    build_truncation_evidence,
    compile_critic_stage,
    exact_text_sha256,
)


SOURCE_PROMPT = "Explain the bounded epistemic review design."
SOURCE_REVISION_ID = "candidate-revision-0"
SOURCE_REVISION_TEXT = "Initial candidate answer."
SOURCE_REVISION_HASH = exact_text_sha256(SOURCE_REVISION_TEXT)


def make_run(
    *,
    mode: str = OrchestrationMode.SEQUENTIAL_RING_V1.value,
    prompt: str = SOURCE_PROMPT,
    context_hash: str = "b" * 64,
) -> EpistemicRunContract:
    return build_epistemic_run_contract(
        run_id="run-contract-1",
        orchestration_mode=mode,
        source_request_hash="a" * 64,
        source_prompt=prompt,
        knowledge_context_hash=context_hash,
        knowledge_profile_hash="c" * 64,
        planned_stage_ids=("stage-primary-0", "stage-critic-1", "stage-critic-2", "stage-primary-3"),
        planned_stage_roles=(
            StageRole.PRIMARY.value,
            StageRole.CRITIC.value,
            StageRole.CRITIC.value,
            StageRole.PRIMARY.value,
        ),
    )


def make_first_stage(run: EpistemicRunContract) -> EpistemicStageContract:
    return build_epistemic_stage_contract(
        run=run,
        stage_index=0,
        source_revision_id=SOURCE_REVISION_ID,
        source_revision_hash=SOURCE_REVISION_HASH,
    )


def make_critic_stages(
    run: EpistemicRunContract,
    *,
    source_prompt: str = SOURCE_PROMPT,
) -> tuple[EpistemicStageContract, EpistemicStageContract, EpistemicStageContract]:
    first = make_first_stage(run)
    critic1, _ = compile_critic_stage(
        run=run,
        stage_index=1,
        source_prompt=source_prompt,
        source_revision_id=SOURCE_REVISION_ID,
        source_revision_hash=SOURCE_REVISION_HASH,
        parent_stage=first,
        parent_revision_hash=SOURCE_REVISION_HASH,
    )
    parent = critic1 if run.orchestration_mode == OrchestrationMode.SEQUENTIAL_RING_V1.value else first
    critic2, _ = compile_critic_stage(
        run=run,
        stage_index=2,
        source_prompt=source_prompt,
        source_revision_id=SOURCE_REVISION_ID,
        source_revision_hash=SOURCE_REVISION_HASH,
        parent_stage=parent,
        parent_revision_hash=SOURCE_REVISION_HASH,
    )
    return first, critic1, critic2


def no_truncation(component: str = "critic_output"):
    return build_truncation_evidence(
        original_content="strict-output",
        retained_content="strict-output",
        truncated_component=component,
        truncation_reason="NOT_TRUNCATED",
    )


def issue(issue_id: str = "ISSUE-1", *, summary: str = "Material omission.") -> CriticIssue:
    return CriticIssue(
        issue_id=issue_id,
        issue_code="MISSING-CONSTRAINT",
        severity="HIGH",
        summary=summary,
        evidence="The source request contains the missing requirement.",
        affected_section="section-1",
        recommended_revision="Add the missing bounded requirement.",
        source_revision_hash=SOURCE_REVISION_HASH,
    )


def material_payload(stage: EpistemicStageContract, *issues: CriticIssue):
    values = issues or (issue(),)
    return build_critic_stage_payload(
        stage=stage,
        critic_outcome=CriticOutcome.MATERIAL_ISSUES_FOUND,
        issues=values,
        truncation_evidence=no_truncation(),
    )


def no_issue_payload(stage: EpistemicStageContract):
    return build_critic_stage_payload(
        stage=stage,
        critic_outcome=CriticOutcome.NO_MATERIAL_ISSUE_FOUND,
        issues=(),
        truncation_evidence=no_truncation(),
    )


def make_revision_stage(
    run: EpistemicRunContract,
    payloads,
    *,
    first: EpistemicStageContract,
    critic2: EpistemicStageContract,
) -> EpistemicStageContract:
    parent = critic2 if run.orchestration_mode == OrchestrationMode.SEQUENTIAL_RING_V1.value else first
    return build_epistemic_stage_contract(
        run=run,
        stage_index=3,
        source_revision_id=SOURCE_REVISION_ID,
        source_revision_hash=SOURCE_REVISION_HASH,
        parent_stage=parent,
        parent_revision_hash=SOURCE_REVISION_HASH,
        bound_critic_payload_hashes=tuple(payload.payload_hash for payload in payloads),
    )


def replace_and_rehash(instance, **changes):
    hash_field = "run_hash" if isinstance(instance, EpistemicRunContract) else "stage_hash"
    return replace(instance, **changes, **{hash_field: ""})
