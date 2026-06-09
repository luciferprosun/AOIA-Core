# AOIA-Core Framework Surface Map

AOIA-Core is being cleaned into a professional framework repository. This map defines the current framework surface, archive/research areas, future-only knowledge packs, and legacy surfaces that must not be mistaken for approved production behavior.

## 1. Purpose

This document defines the classification boundary for framework cleanup.

It separates:

- framework-core candidates that should remain visible in the main repository surface
- active runtime and test surfaces that still need later review
- research, audit, archive, and future-pack areas that should not dominate the framework identity
- legacy and audit-sensitive surfaces that must not be treated as approved runtime behavior

This map does not clean the repository by itself. It only defines the classification boundary for later cleanup.

## 2. Current Repository Problem

The repository is overloaded by mixed concerns and mixed visibility.

- 1055 tracked files
- 266 docs files
- 126 docs/audit files
- 78 test files
- 92 knowledge files

The main overload comes from:

- `docs/audit/` checkpoint accumulation
- `archive/forensic_exports/` historical source-export material
- mixed framework/runtime content and knowledge-pack content in the same visible tree
- legacy runtime surfaces remaining present beside narrower reviewer-facing claims

## 3. Framework Core Surface

The following are framework-core candidates and should be treated as `KEEP_CORE` pending final API cleanup:

- `runtime/model_router.py` — `KEEP_CORE`
- `runtime/model_catalog.py` — `KEEP_CORE`
- `runtime/schemas/model_router.py` — `KEEP_CORE`
- `runtime/safety/approval_gate.py` — `KEEP_CORE`
- `runtime/provider_audit.py` — `KEEP_CORE`
- `runtime/provider_config.py` — `KEEP_CORE`
- `runtime/retrieval/` — `KEEP_CORE`
- `runtime/runtime_paths.py` — `KEEP_CORE`
- `web/app.js` — `KEEP_CORE`
- `web/index.html` — `KEEP_CORE`
- `web/styles.css` — `KEEP_CORE`

These are framework-core candidates, not a claim of final stable public API.

## 4. Active Runtime/API Surface

The current active runtime and API entry surfaces should be classified as follows:

- `runtime/webapp.py` — active local API/UI entrypoint, `REVIEW_LATER` because public-entrypoint boundary work remains
- `runtime/main.py` — `REVIEW_LATER` because legacy surfaces remain
- `runtime/provider_clients.py` — `REVIEW_LATER` because provider/network gates remain sensitive
- `runtime/providers/` — `REVIEW_LATER` because provider/network gates remain sensitive

These files are active and important, but they should not be treated as fully settled framework surface yet.

## 5. Active Test Surface

The test surface should be classified by function, not treated as one flat mass:

- core router, approval, provenance, retrieval, and safety tests — `KEEP_TESTS`
- RED-1 diagnostic/security tests — `KEEP_TESTS`
- future-pack tests such as Hat004, knowledge-pack, or broader research validation — `MOVE_LATER`
- TUI tests — `REVIEW_LATER`

Diagnostic tests are useful and should remain visible, but they should not dominate the long-term framework test surface.

## 6. Canonical Documentation Surface

The canonical reviewer-facing documentation surface should remain small and explicit:

- `README.md` — `KEEP_CANONICAL_DOCS`
- `CURRENT_STATE.md` — `KEEP_CANONICAL_DOCS`
- `docs/REVIEWER_QUICKSTART.md` — `KEEP_CANONICAL_DOCS`
- `docs/THREAT_MODEL.md` — `KEEP_CANONICAL_DOCS`
- `docs/RUNTIME_BOUNDARY.md` — `KEEP_CANONICAL_DOCS`
- `docs/ARCHITECTURE.md` — `KEEP_CANONICAL_DOCS`
- `docs/audit/RED_1_BLOCKER_REGISTER.md` — `KEEP_CANONICAL_DOCS`
- `docs/FRAMEWORK_SURFACE_MAP.md` — `KEEP_CANONICAL_DOCS`

These files should define the visible framework story more than dated checkpoint history.

## 7. Research, Audit, and Archive Surface

The following areas are important history, but they should not dominate the framework surface:

- `docs/audit/` — `ARCHIVE_LATER`
- `archive/forensic_exports/` — `ARCHIVE_LATER`
- `docs/stress_tests/` — `MOVE_LATER`
- `docs/refactor/` — `MOVE_LATER`
- `docs/future/` — `MOVE_LATER`
- `docs/nms/` — `MOVE_LATER`
- embedded PDFs — `ARCHIVE_LATER`
- dated checkpoint reports — `ARCHIVE_LATER`
- external-review artifacts — `ARCHIVE_LATER`

These materials are historically useful, but they currently make the repository surface look overloaded and mixed-purpose.

## 8. Knowledge and Future-Pack Surface

The following areas should later be isolated as optional research or knowledge packs, not presented as core framework runtime:

- `knowledge/` — `MOVE_LATER`
- `runtime/knowledge/` — `MOVE_LATER`
- `knowledge/hats/hat_003_python/` — `MOVE_LATER`
- `knowledge/languages/python/` — `MOVE_LATER`
- `MHLM_MHSR/` — `MOVE_LATER`
- `experiments/` — `MOVE_LATER`

These areas are not invalid. They are simply not the clean framework core surface.

## 9. Legacy and Risk Surface

The following remain audit-sensitive and should be classified conservatively:

- `runtime/tools/browser_tools.py` — `DO_NOT_TOUCH_YET`
- `runtime/tools/web_reader.py` — `DO_NOT_TOUCH_YET`
- `runtime/tools/shell_tools.py` — `DO_NOT_TOUCH_YET`
- `runtime/tools/executor.py` — `DO_NOT_TOUCH_YET`
- `runtime/provider_clients.py` — `REVIEW_LATER`
- `runtime/providers/` — `REVIEW_LATER`
- `runtime/main.py` — `REVIEW_LATER`
- `runtime/requirements.txt` includes Playwright — `REVIEW_LATER`

These are not automatically unsafe in all contexts, but they remain audit-sensitive and must not be mistaken for approved production surfaces.

## 10. Do-Not-Touch-Yet Surface

The following should not be changed during cleanup unless a dedicated hardening or migration task explicitly targets them:

- shell, browser, provider, and executor code outside dedicated hardening tasks — `DO_NOT_TOUCH_YET`
- current passing tests — `DO_NOT_TOUCH_YET`
- canonical docs — `DO_NOT_TOUCH_YET`
- state, config, and secrets surfaces — `DO_NOT_TOUCH_YET`
- knowledge packs until a migration manifest exists — `DO_NOT_TOUCH_YET`
- historical archives and forensic exports — `DELETE_ONLY_AFTER_HUMAN_REVIEW`

## 11. Cleanup Classification Labels

This map uses the following labels:

- `KEEP_CORE` — active framework-core candidate
- `KEEP_TESTS` — active test surface that should remain in the working framework repo
- `KEEP_CANONICAL_DOCS` — small reviewer-facing documentation surface
- `ARCHIVE_LATER` — important history that should later be compressed or indexed, not deleted casually
- `MOVE_LATER` — valid material that likely belongs outside the main framework surface later
- `REVIEW_LATER` — still active but not yet cleanly settled as final framework surface
- `DO_NOT_TOUCH_YET` — sensitive area that should change only under dedicated scoped work
- `DELETE_ONLY_AFTER_HUMAN_REVIEW` — material that should never be removed casually

## 12. Next Cleanup Phases

FRAMEWORK-CLEANUP phase sequence:

- Phase 2: compress/index `docs/audit` history
- Phase 3: separate runtime core from legacy shell/browser/provider surfaces
- Phase 4: classify tests into core, RED diagnostics, future packs
- Phase 5: isolate knowledge/hats/RHCSA/Python packs from framework runtime
- Phase 6: packaging, examples, CI, and root README polish

This map defines the cleanup boundary. It does not perform those phases.
