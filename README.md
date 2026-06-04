# AIOA Whitehat / AOIA-Core

## Current Public Scope

AOIA-Core is a local-first, non-executing inspection and audit layer for
AI-proposed shell commands.

The current public reviewer scope is Bash Safety / GT-RUNTIME inspection work:

- parse and classify proposed shell commands
- identify known dangerous command shapes
- produce deterministic dry-run safety decisions
- record approval and audit metadata for proposed actions
- preserve provenance, evidence-boundary, and contradiction-governance context

`allowed=True` means a proposed command passed the current inspection rules. It
does not authorize execution.

## Safety Boundary

AOIA-Core currently makes no public claim to provide:

- shell execution
- sandboxed execution
- terminal automation
- autonomous agent operation
- production containment
- browser automation safety
- provider-output truth validation

The reviewer-facing deliverable is a pre-execution inspection layer. It is not a
sandbox, not a ShellCheck replacement, not a production terminal security layer,
and not a complete model-output validation system.

## Entrypoint Reality

The repository still contains historical and transitional runtime entrypoints:

- `runtime/main.py`
- `runtime/run.sh`
- `runtime/run_web.sh`
- `scripts/start_tui.sh`

These files reflect earlier local runtime experiments and are not the current
public safety claim for NLnet second review. They may reference model providers,
filesystem tools, browser surfaces, approval prompts, or executor concepts.
Those surfaces are legacy/transitional material unless a specific current
governance document promotes them into scope.

For this review, evaluate AOIA-Core by the non-executing Bash Safety inspection
and audit boundary, not by broad historical runtime ambitions.

## What AOIA-Core Is

AOIA-Core is:

- local-first
- non-executing in the current Bash Safety reviewer scope
- deterministic where implemented in rule-based command inspection
- explicit about provenance, evidence boundaries, and model-output limits
- designed for human review before any future execution path exists

## What AOIA-Core Is Not

AOIA-Core is not:

- AGI
- an autonomous agent
- a truth engine
- a RAG wrapper
- a sandbox
- cloud-first infrastructure
- a validated science project
- production-ready terminal security software

LSC, MHLM, MDLH, SCEMDA, HNC, Gary-related, and other research or collaborator
materials are historical context unless explicitly promoted by governance. They
are not AOIA-Core runtime authority.

## Reviewer Start Here

Read these files first:

- `docs/reviewer/QUICK_START_FOR_GRANT_REVIEWERS.md`
- `docs/reviewer/NLNET_EXTERNAL_REVIEWER_BRIEF.md`
- `docs/REVIEWER_QUICKSTART.md`
- `docs/THREAT_MODEL.md`
- `docs/BENCHMARK_LIMITATIONS.md`
- `docs/GT_RUNTIME_ROADMAP.md`
- `docs/governance/IMPLEMENTED_CAPABILITIES.md`
- `docs/governance/EXTERNAL_MODEL_OUTPUT_POLICY.md`

The most important status register is
`docs/governance/IMPLEMENTED_CAPABILITIES.md`. It separates implemented,
partial, planned, and documentation-only items. Do not infer implementation
from aspirational or historical documentation.

## Validation

From the repository root:

```bash
python3 -m compileall runtime tests
PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v
```

Validation does not prove complete shell safety, production readiness, or
scientific correctness. It checks syntax and the current regression suite.

## Public Provenance Anchor

The first public AIOA NiFe SPARKhat provenance record is published on Zenodo:

- DOI: `10.5281/zenodo.20522947`
- Record: `https://zenodo.org/records/20522947`
- Report:
  `docs/audit/AIOA_NIFE_SPARKHAT_001_ZENODO_PUBLICATION_REPORT_03_JUNE_2026.md`

This record is a public provenance and lineage anchor for the AOIA / AIOA
workstream. It is not a claim that Zenodo publication validates AOIA, AIOA,
MHLM, MDLH, LSC, or any scientific claim.

## External Model Output Policy

AOIA-Core preserves some model-assisted reviews, forensic exports, and audit
packets as historical context. These files are not canonical source, not
evidence, and not runtime authority. They must not override governance
contracts, ADRs, or the current non-execution boundary.

See `docs/governance/EXTERNAL_MODEL_OUTPUT_POLICY.md`.

## License

AOIA-Core is released under the MIT License. See `LICENSE`.
