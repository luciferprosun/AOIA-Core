# AGENTS.md - AOIA-Core Codex Operating Instructions

## 1. Project Identity

AOIA-Core / AIOA Whitehat is a local-first Epistemic Control System.

It is not a normal autonomous agent.

Provider output is never authority.

Critic verdicts are metadata only.

Human approval, hash binding, gates, and audit are the authority boundary.

AOIA-Core helps a human inspect, review, preview, and decide on AI-generated
suggestions before any write or execution occurs.

## 2. AGENTS.md Boundary

This file is for Codex/operator workflow only.

It is not an AOIA runtime component.

It must not be imported by runtime code.

It must not be read by runtime code.

It must not define executable behavior.

It must not become authority.

It must not change AOIA-Core behavior.

It is a repository-level working instruction for safer production work.

## 3. Current Production Roadmap

Step 6 - Provider Runtime 1A: DONE

Step 7 - Provider Selector 1A / Chat Provider: DONE

Step 8 - Provider Critic 1A: DONE

Step 9 - Artifact Preview 1A: DONE

Step 10 - Control Write 1A: DONE

Step 11 - ActionProposal 1A: NEXT, but do not start unless explicitly instructed

## 4. Production Discipline

Build the system, not documents.

Prefer one small runtime file plus one focused test file.

Avoid broad refactors.

Avoid docs-only closure loops.

Avoid large architecture rewrites.

Do not rename the roadmap.

Do not invent new roadmap steps.

Do not insert research layers into active production tasks.

Do not mix unrelated work into the same commit.

## 5. Safety Invariants

Provider output never becomes authority.

Preview is not permission.

Tags, tetrads, hats, and metadata are not authority.

Sandbox is not permission.

Open model is not authority.

Guardrails are not approval.

Approval for one action type does not authorize another action type.

File write approval does not authorize commit, push, package install, shell
execution, provider calls, browser actions, or other execution.

Human approval, hash binding, gates, and audit evidence are required before
controlled write or execution.

## 6. Default Forbidden Additions Unless Explicitly Requested

Do not add UI.

Do not add provider/API/network calls.

Do not add env/API key/secrets handling.

Do not add provider SDK dependencies.

Do not add fallback/retry/streaming behavior.

Do not add subprocess/shell/browser/executor expansion.

Do not add Git commit/push automation in runtime.

Do not add package installation behavior.

Do not insert Knowledge Hub / Reach / Tetrad / Pheromone Tags into the current
control path.

Do not change global approval/gate/write authority.

## 7. Required Task-Start Checks

At the start of every Codex task, run:

```bash
git status -sb
git branch --show-current
git rev-parse HEAD
git diff --name-only
```

Confirm the intended branch is:

```text
feature/m2-b0-provider-critic-inert-core
```

If the branch is wrong, stop and report.

If the worktree is dirty before the task, stop and report the dirty files unless
the task explicitly says to clean known files.

## 8. Required Task-End Report

Every Codex task must report:

```text
START_HEAD
END_HEAD
BRANCH
FILES_CHANGED
TESTS_RUN
COMMIT_HASH
PUSH_RESULT
FINAL_GIT_STATUS
SCOPE_VIOLATIONS: YES/NO
```

If any expected validation was not run, explain why.

## 9. Validation Expectations

For code tasks:

Run focused tests first.

Then run related regression tests.

Then run compileall.

Then run git diff --check.

Run the full unittest suite when feasible.

Known full-suite command from Step 10:

```bash
PYTHONPATH=runtime:. python3 -m unittest discover -s tests -v
```

Note:

```bash
python3 -m unittest discover -v
```

from repo root may discover 0 tests.

```bash
python3 -m unittest discover -s tests -v
```

may fail due import path assumptions.

Use:

```bash
PYTHONPATH=runtime:. python3 -m unittest discover -s tests -v
```

for the full suite unless the repo changes this later.

## 10. Commit Discipline

Use small commits.

Commit only intended files.

Before commit, run:

```bash
git status -sb
git diff --name-only
```

Never include accidental untracked files.

Never combine unrelated work.

Push only after tests/checks pass.

## 11. Current Next Work After This AGENTS.md Task

After this AGENTS.md task is committed and pushed, the next production planning
target is:

```text
Step 11 - ActionProposal 1A
```

Do not implement Step 11 in this task.
