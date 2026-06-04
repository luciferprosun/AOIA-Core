# Quick Start for Grant Reviewers

## 1. What AOIA-Core is

AOIA-Core is a local-first, non-executing inspection and audit layer for
AI-proposed shell commands.

The current reviewer scope is Bash Safety / GT-RUNTIME inspection work:
rule-based command parsing, classification, dry-run safety decisions, approval
metadata, audit records, and explicit provenance/evidence-boundary context.

`allowed=True` means a proposed command passed the current inspection rules. It
does not authorize execution.

## 2. What AOIA-Core is not

AOIA-Core is not:

- AGI
- an autonomous production agent
- a truth engine
- a scientific validation system
- an LSC or neutrino validation project
- a GUI, mobile, or frontend product
- a sandbox
- a shell executor
- a production terminal security layer

## 3. What to inspect first

Start with:

- `README.md`
- `docs/REVIEWER_QUICKSTART.md`
- `docs/THREAT_MODEL.md`
- `docs/BENCHMARK_LIMITATIONS.md`
- `docs/GT_RUNTIME_ROADMAP.md`
- `docs/governance/IMPLEMENTED_CAPABILITIES.md`
- `docs/reviewer/PROJECT_OVERVIEW_FOR_REVIEWERS.md`
- `docs/reviewer/ONE_CONCRETE_EXAMPLE.md`

Then inspect representative inspection-layer files:

- `runtime/tools/validator.py`
- `runtime/commands/grammar.py`
- `tests/test_bash_parser_inert.py`
- `tests/test_respond_shell_safety.py`

## 4. How to run validation

From the repository root:

```bash
python3 -m compileall runtime tests
PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v
```

## 5. Expected validation result

`compileall` is syntax validation only. It does not prove runtime correctness,
security, scientific validity, command safety, or production readiness.

The last known full validation before this cleanup reported:

- `146` tests run
- `4` optional UI/Textual tests skipped
- `OK`

## 6. Capability evidence map

Use `docs/governance/IMPLEMENTED_CAPABILITIES.md` as the conservative capability
map. It separates implemented, partial, planned, legacy/transitional, and
documentation-only claims. Do not infer production readiness from documentation
presence alone.

## 7. Scope warnings

Historical runtime entrypoints such as `runtime/main.py`, `runtime/run.sh`,
`runtime/run_web.sh`, and `scripts/start_tui.sh` are legacy/transitional
surfaces unless explicitly promoted by current governance. Do not treat their
broad execution, provider, browser, or agent references as the current NLnet
second-review claim.

LSC appears only as a historical research origin and high-claim-density neutrino
archive stress-test corpus. It is not validated physics, not AOIA-Core
scientific output, and not runtime authority.

Provenance verifies local lineage and chain integrity only. It does not validate
truth, external source authenticity, scientific claims, or model output.

The evidence boundary is a controlled write path and audit-support mechanism,
not a complete immutable content-addressed evidence store.

Runtime safety contracts are strong design and governance contracts with partial
runtime enforcement today. The current public scope is non-executing inspection;
full execution containment remains out of scope.

Web/TUI surfaces are legacy/transitional visualization, debug, and operator
interfaces. Generated `state/`, `memory/`, `logs/`, and `obsidian_vault/`
artifacts are runtime artifacts, not canonical source authority.

## 8. Recommended reading order

1. `README.md`
2. `docs/reviewer/QUICK_START_FOR_GRANT_REVIEWERS.md`
3. `docs/REVIEWER_QUICKSTART.md`
4. `docs/governance/IMPLEMENTED_CAPABILITIES.md`
5. `docs/reviewer/PROJECT_OVERVIEW_FOR_REVIEWERS.md`
6. `docs/reviewer/ONE_CONCRETE_EXAMPLE.md`
