# RED-1-C Browser Surface Freeze Report

Date: 2026-06-11

Branch: `feature/red1-c-browser-surface-freeze`

Purpose: apply the first targeted RED-1 fix by freezing legacy browser-capable surfaces so they are not treated as approved H4/runtime execution paths.

## Files changed

- `runtime/tools/browser_tools.py`
- `runtime/tools/web_reader.py`
- `runtime/tools/executor.py`
- `tests/test_red1_browser_surface_freeze.py`
- `docs/audit/RED_1_C_BROWSER_SURFACE_FREEZE_REPORT.md`

## Freeze method used

- Added explicit frozen legacy markers:
  - `LEGACY_BROWSER_SURFACE = True`
  - `APPROVED_RUNTIME_BROWSER_FLOW = False`
  - `H4_APPROVED_BROWSER_FLOW = False`
  - `BROWSER_EXECUTION_FROZEN = True`
- Added a default-off legacy opt-in flag:
  - `AOIA_LEGACY_BROWSER_ENABLED`
- Added `_require_legacy_browser_enabled()` guard with a runtime error explaining that the browser surface is frozen by default.
- Guarded browser-control methods in `runtime/tools/browser_tools.py`.
- Guarded `fetch_page()` in `runtime/tools/web_reader.py` before network fetch/cache behavior.
- Marked browser action descriptions in the executor registry as `Frozen legacy browser surface`.

## What is now proven

- Legacy browser modules carry explicit frozen/not-approved markers.
- Browser execution entrypoints are guarded by default before browser launch.
- Web-reader fetch is guarded before network fetch.
- Executor registry still exposes legacy action names for compatibility, but marks browser actions as frozen legacy surface.
- Existing RED-1-B boundary tests continue to prove CPT/webapp transform paths do not invoke browser/shell/provider/file/git primitives.

## What remains unproven

- RED-1 is not closed.
- Browser H4 approved architecture is not implemented.
- No sandbox exists yet.
- No BrowserActionProposal exists yet.
- No HumanApprovalDecision is wired to browser actions.
- No complete browser approval architecture exists.
- Legacy browser action names still exist in the executor registry for compatibility and remain a RED-1 surface until the next cleanup pass decides whether to remove or isolate them further.

## Remaining RED-1 blockers

- Direct filesystem/git boundary coverage remains partial.
- Provider/network gateway separation remains a live architecture concern outside the CPT transform path.
- Shell/executor freeze still needs its own targeted closure pass.
- Memory/retrieval and canonical-promotion follow-up remains open.
- UI approval must remain separate from system execution permission.

## Explicit non-claims

- No browser execution was added.
- No browser launch was performed.
- No shell/provider/file/git action was added.
- CPT behavior was not changed.
- This is a freeze, not an H4 browser implementation.

## Recommended next targeted fix

RED-1-C2 direct filesystem/git boundary freeze.

