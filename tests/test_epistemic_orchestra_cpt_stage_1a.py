from __future__ import annotations

import builtins
from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

from runtime.cpt.transformer import transform_prompt
from runtime.epistemic_orchestra import (
    CriticStageCompilation,
    EpistemicContractError,
    bind_cpt_transformation_to_stage,
    compile_critic_stage,
    hash_critic_transformation_record,
)
from tests.epistemic_orchestra_test_support_1a import (
    SOURCE_PROMPT,
    SOURCE_REVISION_HASH,
    SOURCE_REVISION_ID,
    make_first_stage,
    make_run,
)


class EpistemicCptStageBinding1ATests(unittest.TestCase):
    def compile(self):
        run = make_run()
        first = make_first_stage(run)
        stage, compilation = compile_critic_stage(
            run=run,
            stage_index=1,
            source_prompt=SOURCE_PROMPT,
            source_revision_id=SOURCE_REVISION_ID,
            source_revision_hash=SOURCE_REVISION_HASH,
            parent_stage=first,
            parent_revision_hash=SOURCE_REVISION_HASH,
        )
        return run, stage, compilation

    def test_existing_transform_prompt_is_reused(self):
        real = transform_prompt(SOURCE_PROMPT)
        with patch(
            "runtime.epistemic_orchestra.cpt_stage.transform_prompt",
            return_value=real,
        ) as mocked:
            self.compile()
        self.assertGreaterEqual(mocked.call_count, 1)
        mocked.assert_any_call(SOURCE_PROMPT)

    def test_no_duplicate_cpt_template_is_introduced(self):
        root = Path(__file__).resolve().parents[1] / "runtime" / "epistemic_orchestra"
        source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
        self.assertNotIn("Review the untrusted user prompt below with a direct", source)

    def test_transformation_record_hash_is_deterministic(self):
        record = transform_prompt(SOURCE_PROMPT)
        self.assertEqual(
            hash_critic_transformation_record(record),
            hash_critic_transformation_record(record),
        )

    def test_exact_record_is_bound_to_run_and_stage(self):
        run, stage, compilation = self.compile()
        self.assertEqual(compilation.run_hash, run.run_hash)
        self.assertEqual(compilation.stage_hash, stage.stage_hash)
        self.assertEqual(
            compilation.critic_transformation_hash,
            stage.critic_transformation_hash,
        )
        self.assertEqual(compilation.cpt_canonical_status, "DRAFT")

    def test_compilation_round_trip_verifies_hash(self):
        _, _, compilation = self.compile()
        restored = CriticStageCompilation.from_dict(compilation.to_dict())
        self.assertEqual(restored.compilation_hash, compilation.compilation_hash)

    def test_source_prompt_hash_mismatch_rejected(self):
        run = make_run()
        first = make_first_stage(run)
        with self.assertRaises(EpistemicContractError):
            compile_critic_stage(
                run=run,
                stage_index=1,
                source_prompt=SOURCE_PROMPT + " changed",
                source_revision_id=SOURCE_REVISION_ID,
                source_revision_hash=SOURCE_REVISION_HASH,
                parent_stage=first,
                parent_revision_hash=SOURCE_REVISION_HASH,
            )

    def test_record_original_prompt_hash_mismatch_rejected(self):
        run, stage, _ = self.compile()
        record = replace(transform_prompt(SOURCE_PROMPT), original_prompt_hash="d" * 64)
        with self.assertRaises(EpistemicContractError):
            bind_cpt_transformation_to_stage(
                run=run, stage=stage, source_prompt=SOURCE_PROMPT, record=record
            )

    def test_record_transformed_prompt_hash_mismatch_rejected(self):
        run, stage, _ = self.compile()
        record = replace(transform_prompt(SOURCE_PROMPT), transformed_prompt_hash="d" * 64)
        with self.assertRaises(EpistemicContractError):
            bind_cpt_transformation_to_stage(
                run=run, stage=stage, source_prompt=SOURCE_PROMPT, record=record
            )

    def test_record_template_version_mismatch_rejected(self):
        run, stage, _ = self.compile()
        record = replace(transform_prompt(SOURCE_PROMPT), template_version="forged-template")
        with self.assertRaises(EpistemicContractError):
            bind_cpt_transformation_to_stage(
                run=run, stage=stage, source_prompt=SOURCE_PROMPT, record=record
            )

    def test_changed_transformation_record_rejected_as_stale(self):
        run, stage, _ = self.compile()
        record = replace(
            transform_prompt(SOURCE_PROMPT),
            provenance_note="changed but still non-authoritative",
        )
        with self.assertRaises(EpistemicContractError):
            bind_cpt_transformation_to_stage(
                run=run, stage=stage, source_prompt=SOURCE_PROMPT, record=record
            )

    def test_no_provider_call_occurs(self):
        with patch(
            "runtime.providers.gateway.run_provider_request",
            side_effect=AssertionError("provider call forbidden"),
        ) as provider:
            self.compile()
        provider.assert_not_called()

    def test_no_file_write_occurs(self):
        real_open = builtins.open

        def fail_write(file, mode="r", *args, **kwargs):
            if any(flag in mode for flag in ("w", "a", "x", "+")):
                raise AssertionError("runtime write forbidden")
            return real_open(file, mode, *args, **kwargs)

        with patch("builtins.open", side_effect=fail_write):
            self.compile()

    def test_no_cpt_audit_append_occurs(self):
        with patch(
            "runtime.cpt.audit.append_transformation_record",
            side_effect=AssertionError("automatic audit append forbidden"),
        ) as audit:
            self.compile()
        audit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
