# AOIA-Core Reviewer Quickstart

## 1. What AOIA-Core Is

AOIA-Core is a local-first, non-executing inspection and audit layer for
AI-proposed shell commands.

The current public reviewer scope is Bash Safety / GT-RUNTIME inspection work:
rule-based command parsing, classification, dry-run safety decisions, approval
metadata, audit records, and explicit provenance/evidence-boundary context.

`allowed=True` means a proposed command passed the current inspection rules. It
does not authorize execution.

## 2. What AOIA-Core Is Not

- It is not a sandbox.
- It is not a replacement for OS-level containment.
- It is not a claim of validated safety.
- It does not prove complete real-world shell safety.
- It is not a production-ready terminal execution security layer.
- It is not an autonomous agent.
- It does not execute proposed commands in the current public reviewer scope.

## 3. What To Read First

- `README.md`
- `docs/reviewer/QUICK_START_FOR_GRANT_REVIEWERS.md`
- `docs/THREAT_MODEL.md`
- `docs/BENCHMARK_LIMITATIONS.md`
- `docs/GT_RUNTIME_ROADMAP.md`
- `docs/governance/IMPLEMENTED_CAPABILITIES.md`
- `docs/audit/`

## 4. Validation Commands

```bash
python3 -m compileall runtime tests
PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v
```

## 5. Context Boundary

Historical runtime entrypoints such as `runtime/main.py`, `runtime/run.sh`,
`runtime/run_web.sh`, and `scripts/start_tui.sh` are legacy/transitional
surfaces unless explicitly promoted by current governance. Do not treat their
broad execution, provider, browser, or agent references as the current NLnet
second-review claim.

LSC, MHLM or MDLH, SCEMDA or HNC, and Gary-related materials are external
research or audit context and are not AOIA-Core runtime authority.
