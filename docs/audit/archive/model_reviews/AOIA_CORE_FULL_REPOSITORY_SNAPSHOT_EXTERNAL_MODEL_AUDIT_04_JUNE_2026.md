# AOIA-Core Full Repository Snapshot for External Model Audit - 04 June 2026

## 1. Executive Summary

AOIA-Core is currently framed for public review as a local-first,
non-executing shell-command inspection and audit layer. Its current safety
work is reviewer-facing and narrowed for NLnet: inspect proposed shell commands,
classify risk, support dry-run approval/audit records, and document boundaries.

AOIA-Core should not be read as a shell executor, terminal agent, autonomous
agent loop, production cloud/provider system, production browser automation
system, or general AI-safety proof.

- Current branch: `dev/gt-runtime-8-bash-safety-planning`
- Current HEAD: `165ef4b docs: add NLnet final cleanliness checkpoint`
- Current validation result: `python3 -m compileall runtime tests` completed,
  and `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`
  ran `470` tests with `OK (skipped=4)`.

## 2. Current Public Review Scope

The current public/reviewer scope is:

- non-executing command inspection
- inert command proposal structures
- Bash/shell safety classification
- approval decision and dry-run gate behavior
- approval/audit event support
- reviewer documentation and reviewer boundary clarity
- no runtime execution expansion

`allowed=True` in this context means a proposed command passed current
inspection rules. It does not authorize execution.

## 3. Baseline and Change Window

- Change window starts: `01 June 2026 12:00`
- Baseline commit before that time: `771ebc9 docs: consolidate Python master library external reviews`
- Current HEAD: `165ef4b docs: add NLnet final cleanliness checkpoint`
- Commits since the baseline window: `51`

Commit list from
`git log --since="2026-06-01 12:00" --oneline --decorate --reverse`:

```text
da9f030 docs: push Python master library post-freeze work
98271ac docs: add Python official docs cross-check plan
4d254c8 data: add Python dangerous built-ins advisory batch
4841df3 docs: add official docs cross-check batch for Python dangerous built-ins
3c74160 test: add Python advisory duplicate conflict scan
6bc0183 test: add Python advisory duplicate conflict scan
57b63b2 docs: add NVIDIA NeMo NIM feasibility audit
4db6f43 docs: add local disk cleanup and USB backup plan
4c82383 docs: record local cleanup USB archive and NVIDIA prep
64abb95 docs: record local desktop reports cleanup
4c2c64c docs: record full repository snapshot creation
5d76697 docs: add runtime restart safepoint
170e5d0 fix: reduce runtime boot side effects
9600a3b fix: move generated runtime state out of repo
5ef22a9 fix: warn on unsafe shell advice in responses
006dab8 fix: classify high-risk shell advice in responses
92309e1 docs: close runtime hardening round
4d6fddf feat: add single event ledger prototype
0167357 docs: add runtime full closure report
c0aa676 feat: add GT-RUNTIME-6 shell safety metrics harness
98f2d46 docs: add post-GT-RUNTIME-6 external audit baseline
3812577 docs: add GT-RUNTIME-7A honesty pack
9172305 feat: add inert CommandProposal schema
44b063a fix: correct runtime schemas package init
bae1be9 test: add mocked approval gate control flow
b473b59 test: add inert adversarial corpus stub
c0b5468 docs: add CommandProposal ledger schema
e19dd40 docs: close GT-RUNTIME-7 phase gate
0f5261a docs: add Bash Safety Phase 1 spec [GT-RUNTIME-8]
133e637 docs: add GT-RUNTIME-8B API boundary planning
fd6d27f feat: add inert Bash command proposal parser
b57d69b test: add inert Bash safety corpus
b328cce feat: add dry-run approval gate
8f8bde8 fix: harden GT-RUNTIME-8E approval gate
f029870 feat: add dry-run approval audit event
a511d95 docs: add AOIA IOA 2027-2028 verification roadmap
8bda7e3 docs: add NiFe Synapses future tag maps
dcfffdb docs: add NiFe source registry validation workflow
ab63ea6 test: add GT-RUNTIME-8G inert mini-stack integration
1526cb7 docs: add GT-RUNTIME-8H reviewer boundary statement
a39b8e5 test: add GT-RUNTIME-8I Bash Safety corpus v0.3
94fe1a0 docs: add GT-RUNTIME-8J Bash corpus coverage matrix
9e351bd feat: add GT-RUNTIME-8K targeted parser hardening
cf69e0c docs: add GT-RUNTIME-8 final phase closure package
de30e0f docs: add GT-RUNTIME-8M final savepoint pack
fa15330 feat: add DEV-TOOLS-1 terminal provider switcher
36889c2 feat: add DEV-TOOLS-2 IOA lab clone utility
d36c21e docs: add AIOA NiFe SPARKhat 001 Zenodo publication anchor
059fffc docs: narrow NLnet reviewer scope
f889c0b docs: add NLnet external reviewer brief
165ef4b (HEAD -> dev/gt-runtime-8-bash-safety-planning, origin/dev/gt-runtime-8-bash-safety-planning) docs: add NLnet final cleanliness checkpoint
```

## 4. Dedicated Chapter - Changes Since NLnet Submission

### 4.1 GT-RUNTIME Safety Hardening

Supported by git history and repository documents, the GT-RUNTIME line moved
through several safety-oriented milestones:

- GT-RUNTIME restart and generated-state cleanup: reduced boot side effects and
  moved generated runtime state out of the repository.
- Response shell-safety warnings: added warning/classification paths for unsafe
  shell advice in responses.
- GT-RUNTIME-6: added a shell safety metrics harness and documented external
  audit baseline material.
- GT-RUNTIME-7: added docs/spec boundary work, inert `CommandProposal` schema,
  mocked approval gate control flow, inert adversarial corpus stub, and ledger
  schema documentation.
- GT-RUNTIME-8: added Bash Safety Phase 1 planning, inert Bash command proposal
  parser, inert Bash safety corpus, dry-run approval gate, approval gate
  hardening, dry-run approval audit event, inert mini-stack integration,
  reviewer boundary statement, Bash Safety corpus v0.3, corpus coverage matrix,
  targeted parser hardening, and final phase closure/savepoint packages.

These milestones support controlled regression coverage and non-executing
validation for the current stated scope. They do not prove general AI safety or
production shell safety.

### 4.2 Reviewer / NLnet Packaging

Reviewer packaging work since the window includes:

- README and public framing narrowed to the NLnet reviewer scope.
- `docs/reviewer/NLNET_EXTERNAL_REVIEWER_BRIEF.md` and PDF added as a short
  external reviewer brief.
- `docs/audit/NLNET_FINAL_CLEANLINESS_CHECKPOINT_REPORT_04_JUNE_2026.md`
  added as a final cleanliness checkpoint.
- Reviewer quickstarts and boundary docs identify legacy/transitional runtime,
  provider, browser, and TUI references as outside the current public claim
  unless explicitly promoted by governance.

### 4.3 Developer Tools and Lab Separation

Developer-tool commits added:

- DEV-TOOLS-1 terminal provider switcher.
- DEV-TOOLS-2 IOA lab clone utility.

The related docs describe these as developer utilities and lab-separation tools,
not as the current public runtime scope. Lab tooling should be audited as
separate from production AOIA-Core reviewer claims.

### 4.4 NiFe / Knowledge Hats / Future Architecture

The repository contains NiFe, White Hat, Memory Hats, and future architecture
materials under `docs/future/`, `docs/architecture/`, and `docs/audit/`.
Recent commits added NiFe Synapses future tag maps, source registry validation
workflow material, and a Zenodo publication anchor.

These should be read as future/internal/research-context documentation unless a
current governance file explicitly marks a component implemented. Future
architecture is not runtime. White Hat, hats, and NiFe concepts are not current
NLnet implemented scope by default.

### 4.5 Cleanup / Repository Hygiene

Repository hygiene findings:

- `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, generated runtime logs,
  runtime state, screenshots, and memory artifacts are ignored in `.gitignore`.
- No tracked `.venv`, `__pycache__`, or `.pyc` files were found with
  `git ls-files`.
- `runtime/.venv` is ignored by `.gitignore`; local validation may still print
  it during `compileall` if the local virtual environment exists.
- `docs/audit/NLNET_FINAL_CLEANLINESS_CHECKPOINT_REPORT_04_JUNE_2026.md`
  records the final cache/cleanliness checkpoint.
- Before this snapshot report was generated, the branch was clean and synced
  with `origin/dev/gt-runtime-8-bash-safety-planning`.

## 5. What Is Implemented Now

Current implemented items, stated conservatively:

- inert command proposal/schema components
- shell/Bash parser and classifier components for proposed commands
- Bash safety corpus and related controlled regression tests
- dry-run approval gate behavior where implemented
- approval audit event schema/support
- tests around non-execution and advisory boundaries in the current scope
- reviewer-readable safety boundary documentation
- provenance, evidence-boundary, contradiction, retrieval, and policy docs with
  mixed implemented/partial/planned status depending on the component

The current evidence should be described as controlled regression coverage,
non-executing validation, current internal test coverage, and reviewer-readable
safety boundary documentation.

## 6. What Is Not Implemented / Out of Scope

Out of current public scope:

- shell execution added in this scope
- production terminal agent
- production cloud deployment
- production browser automation
- billing or user accounts
- White Hat production access
- full autonomous agent
- OS sandbox replacement
- claim of general AI safety
- production shell security certification
- provider-output truth validation

## 7. Validation Snapshot

Commands:

```bash
python3 -m compileall runtime tests
PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v
```

Result observed on 04 June 2026:

- `compileall`: completed
- unittest discovery: `Ran 470 tests`
- skipped tests: `4`
- result: `OK (skipped=4)`

Expected safety-rejection output observed during tests:

```text
[STEP 1] action=shell_execute
Reason: Install curl.
command: sudo apt install curl

PROPOSED ACTION
Action: shell_execute
Reason: Install curl.
command: sudo apt install curl
Result: Action rejected by user.
```

## 8. Repository Structure Overview

Key folders:

- `runtime/`: current runtime and inspection-layer code, plus legacy or
  transitional runtime surfaces. External reviewers should distinguish current
  Bash Safety inspection scope from older broader runtime references.
- `tests/`: regression tests, Bash Safety tests, schema tests, provenance and
  retrieval tests, and boundary tests.
- `docs/`: architecture, governance, reviewer, audit, roadmap, future, and
  stress-test documentation.
- `docs/reviewer/`: fastest reviewer entry point, including the NLnet external
  reviewer brief.
- `docs/audit/`: milestone reports, closure reports, audit records, and
  checkpoint documentation.
- `scripts/`: developer utilities, including lab/provider-related helpers that
  should not be treated as public runtime scope.
- `tools/`: validation and support tools.
- `archive/`: historical/forensic/quarantine material.
- `docs/dev/` and lab-related docs: development/lab support material, not
  current public runtime scope.

Recommended first inspection order:

1. `README.md`
2. `docs/reviewer/NLNET_EXTERNAL_REVIEWER_BRIEF.md`
3. `docs/governance/IMPLEMENTED_CAPABILITIES.md`
4. `docs/reviewer/PROJECT_OVERVIEW_FOR_REVIEWERS.md`
5. `docs/reviewer/ONE_CONCRETE_EXAMPLE.md`
6. `docs/REVIEWER_QUICKSTART.md`
7. `docs/audit/NLNET_FINAL_CLEANLINESS_CHECKPOINT_REPORT_04_JUNE_2026.md`

## 9. Recommended External Model Audit Questions

1. Does README accurately match implemented scope?
2. Are runtime claims narrower than code reality?
3. Are legacy/transitional entrypoints clearly marked?
4. Are docs overclaiming?
5. Is the non-execution boundary clear?
6. Are tests meaningful for the stated scope?
7. What is confusing for a grant reviewer?
8. What should be fixed before public/default branch merge?
9. Are future concepts clearly separated from current implementation?
10. What would an external security reviewer question first?

## 10. Known Risks / Reviewer Caveats

- The repository contains historical, legacy, and transitional material.
- Future architecture docs must not be confused with implemented runtime.
- The public default branch may need alignment if this branch is not the public
  default review branch.
- Large docs/archive volume may confuse reviewers and external models.
- `.venv` is local/ignored, but validation commands may print it if present
  locally.
- The project is early-stage and must avoid overclaiming.
- Commit history includes developer tools and lab utilities; those are not the
  current NLnet public runtime scope.

## 11. Recommended Next Steps

- Verify GitHub default branch and public branch alignment.
- Ensure `LICENSE` exists and is visible.
- Add or update `CONTRIBUTING.md` if missing.
- Add `pyproject.toml` if the project needs standardized Python packaging,
  tooling, or CI entry points.
- Add GitHub Actions CI if not present.
- Tag or release a stable reviewer checkpoint.
- Keep runtime frozen unless explicitly needed.
- Continue docs-only reviewer readiness before new feature work.

## 12. Final Snapshot Status

- Branch: `dev/gt-runtime-8-bash-safety-planning`
- HEAD: `165ef4b docs: add NLnet final cleanliness checkpoint`
- Origin sync status before this snapshot report: synced with
  `origin/dev/gt-runtime-8-bash-safety-planning`
- Validation result: `470` tests run, `4` skipped, `OK`
- Snapshot package path:
  `docs/audit/AOIA_CORE_FULL_REPOSITORY_SNAPSHOT_EXTERNAL_MODEL_AUDIT_04_JUNE_2026.md`

This report is for external model audit and reviewer-readiness only. It is not
a runtime feature, not a safety certification, and not an expansion of public
claims.
