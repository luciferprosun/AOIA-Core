# RED-1-C2 Filesystem and Git Surface Freeze Report

Date: 2026-06-11

Branch: `feature/red1-c2-filesystem-git-freeze`

Purpose: apply the second targeted RED-1 fix by freezing direct filesystem mutation and git-operation surfaces from approved runtime/model/public flow.

## Files changed

- `runtime/tools/filesystem_tools.py`
- `runtime/tools/executor.py`
- `tests/test_red1_filesystem_git_surface_freeze.py`
- `tests/test_executor_containment.py`
- `tests/test_main.py`
- `docs/audit/RED_1_C2_FILESYSTEM_GIT_FREEZE_REPORT.md`

## Freeze method used

- Added explicit filesystem freeze markers:
  - `LEGACY_FILESYSTEM_SURFACE = True`
  - `APPROVED_RUNTIME_FILESYSTEM_FLOW = False`
  - `FILESYSTEM_MUTATION_FROZEN = True`
- Added default-off legacy opt-in:
  - `AOIA_LEGACY_FILESYSTEM_ENABLED`
- Added `_require_legacy_filesystem_enabled()` guard with a runtime error explaining that direct mutation is frozen by default.
- Guarded direct filesystem mutation functions in `runtime/tools/filesystem_tools.py`.
- Marked executor registry file mutation action descriptions as `Frozen legacy filesystem surface`.
- Updated existing legacy mutation tests to opt in explicitly with `AOIA_LEGACY_FILESYSTEM_ENABLED=1`.

## Filesystem surfaces found

- `runtime/tools/filesystem_tools.py`: direct file/folder mutation helpers.
- `runtime/tools/executor.py`: action registry exposing legacy filesystem action names.
- `runtime/tools/memory.py` and `runtime/tools/memory_hats.py`: runtime state persistence surfaces. These were classified as memory/state persistence rather than direct model/public filesystem action surfaces for this task.

## Git surfaces found

- No dedicated runtime git module or executor git action was found.
- Current git risk is shell-mediated or documentation/knowledge-corpus mediated.
- Git command strings exist in docs and knowledge data; those were not treated as live git automation.

## What is now proven

- Direct filesystem mutation helpers carry explicit frozen/not-approved markers.
- Without `AOIA_LEGACY_FILESYSTEM_ENABLED=1`, direct file mutation entrypoints raise before writing, deleting, moving, or creating files/folders.
- Executor registry still exposes legacy file action names for compatibility, but marks mutation actions as frozen legacy filesystem surface.
- No direct git action is registered in the default executor registry.
- Existing RED-1-B and RED-1-C browser freeze tests continue to pass.

## What remains unproven

- RED-1 is not closed.
- File/Git approved architecture is not implemented.
- No sandbox exists yet.
- No FileWriteProposal exists yet.
- No GitOperationProposal exists yet.
- No HumanApprovalDecision is wired to file/git actions.
- Shell-mediated git remains part of the shell/executor freeze work.
- Memory/state persistence and canonical-promotion boundaries still require separate targeted review.

## Remaining RED-1 blockers

- Provider/network gateway separation remains open.
- Shell/executor freeze remains open.
- Memory/retrieval and canonical-promotion follow-up remains open.
- UI approval must remain separate from system execution permission.

## Explicit non-claims

- No file-write execution was added.
- No git automation was added.
- No browser/shell/provider action was added.
- CPT behavior was not changed.
- This is a freeze, not a filesystem/git execution implementation.

## Recommended next targeted fix

RED-1-D provider/network gateway separation.

