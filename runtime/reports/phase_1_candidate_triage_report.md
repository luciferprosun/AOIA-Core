# PHASE 1 - CANDIDATE PROMOTION TRIAGE v1 REPORT

## 1. Files Created

Triage pipeline:

- `runtime/knowledge/tools/promote_candidates.py`

Triage outputs:

- `runtime/knowledge/candidates/reviewed_promotions.json`
- `runtime/knowledge/candidates/review_queue.json`
- `runtime/knowledge/candidates/rejected_candidates.json`

Reports:

- `runtime/knowledge/reports/promotion_triage_report.md`
- `runtime/reports/phase_1_candidate_triage_report.md`

Tests:

- `tests/test_candidate_triage.py`

## 2. Candidates Processed

Input:

- `runtime/knowledge/candidates/candidate_command_index.json`

Total candidates processed:

- `3152`

## 3. ACCEPT / REVIEW / REJECT Stats

- ACCEPT: `1267`
- REVIEW: `1788`
- REJECT: `97`

Important interpretation:

`ACCEPT` means "triage-acceptable for future manual promotion review". It does not mean canonical promotion occurred.

No canonical files were modified.

## 4. Gemini Additions Isolated

Gemini expansion additions isolated:

- `25`

Policy result:

- Gemini-derived candidates were not accepted for automatic promotion.
- Gemini-derived candidates were routed to REVIEW through `gemini_expansion_addition`.
- No Gemini-derived record was written to a canonical index.

## 5. Schema Enforcement Status

Schema source:

- `runtime/knowledge/schema/command.schema.json`

Implementation:

- Candidate records are projected into `command.schema.json` shape for validation.
- Broken records are not silently repaired.
- Schema failures cause REVIEW or REJECT.

Schema-invalid projected records:

- `68`

Reason:

The candidate input format is not identical to the canonical command schema, so the triage pipeline validates a deterministic projection while preserving the original record unchanged.

## 6. Provenance Enforcement Status

ACCEPT requires:

- non-empty `canonical_source`
- canonical source under `runtime/knowledge/source/`
- valid `source_line`
- valid `source_page`
- original quality flags preserved
- status history preserved

Unresolved or partial provenance count:

- `1021`

Policy:

- Missing canonical source: REJECT
- Corrupted provenance: REJECT
- Missing source page: REVIEW
- Partial provenance: REVIEW

## 7. Contamination Summary

Contamination-related reason counts:

- `path_not_command`: 74
- `probable_pdf_merge_artifact`: 16
- `invalid_base_command`: 2
- `likely_contamination_or_comment`: 7
- `suspicious_formatting`: 76
- `multi_command_ambiguity`: 130
- `gemini_expansion_addition`: 25

Most common rejection reasons:

- `malformed`: 76
- `suspicious_formatting`: 76
- `path_not_command`: 74
- `weak_description`: 36
- `duplicate_ambiguity`: 30
- `unresolved`: 21
- `probable_pdf_merge_artifact`: 16
- `schema_invalid`: 11
- `likely_contamination_or_comment`: 7
- `multi_command_ambiguity`: 3
- `invalid_base_command`: 2
- `missing_source_page`: 2

## 8. Canonical Index Integrity Confirmation

Verified unchanged:

- `runtime/knowledge/canonical/rhcsa_commands.json`
- `runtime/knowledge/index/command_index.json`
- `runtime/knowledge/candidates/candidate_command_index.json`

Validation command:

```bash
git diff -- runtime/knowledge/canonical/rhcsa_commands.json runtime/knowledge/index/command_index.json runtime/knowledge/candidates/candidate_command_index.json runtime/retrieval/facade.py runtime/main.py runtime/retrieval/linux/retrieval_engine.py
```

Result:

- no diff

## 9. Runtime Safety Confirmation

No runtime behavior changed in Phase 1.

Confirmed:

- runtime router unchanged
- retrieval facade unchanged
- retrieval engine unchanged
- no runtime retrieval activation
- no evidence writes added
- no vector DB
- no embeddings
- no autonomous loops
- no agent orchestration
- no candidate auto-promotion

Import scanner:

```bash
PYTHONPATH=runtime runtime/.venv/bin/python runtime/tools/check_no_direct_retrieval_imports.py
```

Result:

```text
No direct deprecated retrieval imports found.
```

## 10. Tests

Commands run:

```bash
PYTHONPATH=runtime runtime/.venv/bin/python -m unittest tests.test_candidate_triage -v
```

Result:

- PASS, 8 tests

Regression suite:

```bash
PYTHONPATH=runtime runtime/.venv/bin/python -m unittest \
  tests.test_candidate_triage \
  tests.test_linux_retrieval \
  tests.test_retrieval_facade_contract \
  tests.test_runtime_router_contract_guard \
  tests.test_memory_layer_isolation_smoke -v
```

Result:

- PASS, 35 tests
- Failed: 0

## 11. Unresolved Contamination Risks

- ACCEPT records still require manual human review before canonical promotion.
- REVIEW queue contains duplicate ambiguity and missing provenance cases.
- Gemini-derived records remain untrusted until independently verified.
- Some command-like snippets may still require manual classification even after automated triage.
- Candidate promotion remains blocked.

## 12. Recommended Next Phase

Recommended next phase:

Phase 1B - Manual Review Pack and Promotion Candidate Diff.

Technical reason:

The triage pipeline now separates ACCEPT, REVIEW, and REJECT safely. The next step should produce a human-reviewable diff pack from `reviewed_promotions.json`, compare it against canonical/index records, and require explicit approval before any canonical mutation.
