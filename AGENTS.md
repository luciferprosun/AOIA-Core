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

Provider Runtime, Selector, Critic, Artifact Preview, controlled write,
ActionProposal, Durable Audit Ledger, static capability boundaries, Knowledge
Foundation, and the Linux/Bash/Python/UNIX Hat prototype are implemented and
test-protected in the current development handoff.

The next permitted repository step after Cleanup 1E is isolated clean-clone
validation. Do not begin it unless explicitly instructed.

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

The current task must explicitly identify its intended Git identity as either an
intended branch or, for audit/certification only, an exact commit SHA with
explicit authorization to use detached HEAD.

If the task provides neither identity, stop and report.

For branch work, confirm the current branch exactly matches the branch named by
the task. For explicitly authorized detached audit/certification work, confirm
HEAD is detached and exactly matches the commit SHA named by the task.
Otherwise, stop and report.

If the worktree is dirty before the task, stop and report the dirty files unless
the task explicitly says to clean known files.

Do not automatically checkout, reset, or clean to satisfy these identity or
cleanliness checks.

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

Canonical installed full-suite command:

```bash
CI=1 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p 'test*.py' -q < /dev/null
```

Install the editable package first. The packaging metadata preserves both the
canonical `runtime.*` namespace and required top-level compatibility imports;
do not reintroduce an undocumented `PYTHONPATH` dependency.

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

## 11. Current Next Work

After successful Cleanup 1E validation, the next separately instructed target
is Repository Production Cleanup 1F — isolated clean-clone and full-prototype
validation. This instruction grants no commit, push, release, or deployment.
