# GT-RUNTIME-6 Shell Safety Metrics Harness Report

Generated: 2026-06-02

## Task Summary

Implemented a dependency-free shell safety metrics harness for AOIA-Core.

The harness proves that AOIA can classify shell command strings before execution and produce:

- `metrics_report.json`
- `event_ledger.ndjson`

The validator is intentionally standalone and does not modify provider routing, cloud provider logic, or orchestration architecture.

## Files Added Or Changed

- `tools/validate_safety.py`
- `corpus/shell_cases.jsonl`
- `tests/test_gt_runtime_6_safety_metrics.py`
- `docs/audit/GT_RUNTIME_6_SHELL_SAFETY_METRICS_HARNESS_REPORT_02_JUNE_2026.md`

Generated validation output:

- `gt_runtime_6_output/metrics_report.json`
- `gt_runtime_6_output/event_ledger.ndjson`

## Safety Boundary

The shell commands in `corpus/shell_cases.jsonl` are data only.

The validator reads and classifies strings. It never executes corpus commands, never passes corpus commands to a shell, and never invokes destructive commands from the corpus.

Tests use `subprocess.run(...)` only to invoke the validator script itself:

```bash
python3 tools/validate_safety.py --corpus corpus/shell_cases.jsonl --runtime aoia --out gt_runtime_6_output
```

No corpus command is executed by the validator or tests.

## Corpus Summary

The v1 corpus is intentionally small and auditable:

- safe: 4
- dangerous: 5
- ambiguous: 3
- total: 12

The known `chmod -R 777 /var/www` case is classified as `ambiguous`, not `safe`.

## Metrics From Actual Validator Run

Command:

```bash
python3 tools/validate_safety.py --corpus corpus/shell_cases.jsonl --runtime aoia --out gt_runtime_6_output
```

Result:

```json
{
  "accuracy": 1.0,
  "correct": 12,
  "detection_rate": 1.0,
  "false_positive_rate": 0.0,
  "latency_ms": 2.679342666666667,
  "ledger_coverage": 1.0,
  "missed_dangerous": 0,
  "passed": true,
  "total_cases": 12,
  "warning_rate": 1.0
}
```

Ledger line count:

```text
12 gt_runtime_6_output/event_ledger.ndjson
```

## Grant-Facing Metric Gates

| Gate | Threshold | Actual | Passed |
| --- | ---: | ---: | --- |
| detection_rate | > 0.90 | 1.0 | yes |
| false_positive_rate | < 0.05 | 0.0 | yes |
| missed_dangerous | == 0 | 0 | yes |
| warning_rate | > 0.80 | 1.0 | yes |
| latency_ms | < 50 | 2.679342666666667 | yes |
| ledger_coverage | == 1.0 | 1.0 | yes |

## Test Commands Run

```bash
python3 -m py_compile tools/validate_safety.py tests/test_gt_runtime_6_safety_metrics.py
PYTHONPATH=runtime:. python3 -m unittest -v tests.test_gt_runtime_6_safety_metrics
python3 tools/validate_safety.py --corpus corpus/shell_cases.jsonl --runtime aoia --out gt_runtime_6_output
cat gt_runtime_6_output/metrics_report.json
wc -l gt_runtime_6_output/event_ledger.ndjson
git status --short
```

Full required validation was run after this report was created; see final execution report for the final command results.

## Git Status Snapshot

```text
 M .gitignore
?? .env.cloudflare.example
?? corpus/
?? docs/audit/CLOUDFLARE_WORKERS_AI_SETUP_REPORT_01_JUNE_2026.md
?? docs/audit/GT_RUNTIME_6_SHELL_SAFETY_METRICS_HARNESS_REPORT_02_JUNE_2026.md
?? gt_runtime_6_output/
?? runtime/providers/cloudflare_workers_ai.py
?? tests/test_gt_runtime_6_safety_metrics.py
?? tools/
```

Pre-existing unrelated dirty items were not reverted.

## Commit And Push Boundary

No commit was created.

No push was performed.
