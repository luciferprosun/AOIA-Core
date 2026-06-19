# AOIA TUI Phase 2 Report

Generated: 2026-05-25

## 1. New Operator Console Features

TUI Phase 2 adds a controlled operator console around the existing runtime.
The implementation remains a compatibility wrapper and does not replace routing,
provider management, retrieval, provenance, or executor semantics.

New elements:

- `tui/widgets/transcript_panel.py` for bounded operator-visible transcript output.
- `tui/widgets/approval_panel.py` for visible risky-action approval state.
- `tui/widgets/status_bar.py` for persistent compact runtime status.
- Updated `tui/app.py` operator input dispatch.
- Updated `tui/views/dashboard.py` layout.
- `scripts/start_tui.sh` startup wrapper.
- `tests/test_tui_phase2.py` coverage.

## 2. Runtime Compatibility Verification

Operator input is routed through:

```text
AOIATerminalApp -> AgentRuntime.run_text_request()
```

Provider switching uses the existing:

```text
ProviderManager.switch_model()
```

No new provider adapter, router, websocket, FastAPI layer, agent framework,
embedding system, vector database, or autonomous loop was introduced.

## 3. Transcript Safety Verification

The transcript panel is bounded and sanitizes runtime-internal markers.
It intentionally excludes:

- system prompts
- runtime state JSON
- planner request JSON
- raw provider output markers
- prompt previews
- reasoning trace markers
- chain-of-thought style internals

Displayed content is limited to operator-visible runtime transcript,
approved execution summaries, and safe operational output.

## 4. Approval-Boundary Verification

The TUI wraps the existing executor approval path by replacing the executor
instance approval callback inside the TUI instance only.

Risky actions still flow through:

```text
ExecutionEngine.execute() -> _request_approval()
```

TUI approval behavior:

- `Ctrl+A` approves pending risky action.
- `Ctrl+X` rejects pending risky action.
- pending approval state is visible in `ApprovalPanel`.
- timeout defaults to safe rejection after 120 seconds.
- safe actions continue through existing runtime behavior.

This does not weaken shell classification or executor validation.

## 5. Test Results

Commands run:

```bash
PYTHONPATH=runtime:. runtime/.venv/bin/python -m compileall -q runtime tui tests
bash -n scripts/start_tui.sh
PYTHONPATH=runtime:. runtime/.venv/bin/python -m unittest tests.test_tui_phase1 tests.test_tui_phase2 -v
PYTHONPATH=runtime:. runtime/.venv/bin/python -m unittest discover -s tests -v
```

Results:

| Check | Result |
|---|---:|
| Compile check | PASS |
| Startup script syntax | PASS |
| TUI Phase 1 + 2 tests | 11 / 11 PASS |
| Full unittest suite | 123 / 123 PASS |

## 6. Startup Instructions

Start the TUI with:

```bash
cd /home/l/Desktop/AOIA-Core
./scripts/start_tui.sh
```

Controls:

| Control | Behavior |
|---|---|
| Enter request | Runs through `AgentRuntime.run_text_request()` |
| `/model` | Lists configured model presets |
| `/model NAME` | Switches provider/model through existing provider manager |
| `/status` | Prints runtime status into transcript |
| `/clear` | Clears visible transcript |
| `Ctrl+A` | Approves pending risky action |
| `Ctrl+X` | Rejects pending risky action |
| `Ctrl+P` / `Ctrl+N` | Command history navigation |
| `Ctrl+R` | Refresh runtime status |
| `Ctrl+C` or `q` | Exit |

## 7. Remaining Blockers

- TUI startup was validated by import and script syntax, not by a long-lived
  manual terminal session in this report.
- Approval timeout is implemented as a fixed 120-second guard and is not yet
  user-configurable.
- The TUI transcript is intentionally minimal; it does not yet include rich
  filtering controls or export controls.
- Runtime remains uncommitted with prior environment fixes and Phase 1 changes.

## 8. Prototype Readiness Update

AOIA now has a working terminal prototype surface:

- status dashboard
- live replay-safe operational log panel
- operator input
- slash command support
- provider switching
- bounded transcript view
- approval visibility
- safe shutdown event logging
- startup wrapper

This is still a controlled prototype, not an autonomous agent system.

## 9. Recommended Next Milestone

Recommended next milestone:

```text
TUI Phase 3 — Operator Session Controls and Export
```

Scope should remain narrow:

- transcript export
- session replay selection
- current log file selector
- clearer approval timeout display
- manual provider health refresh
- no runtime router rewrite
- no hidden reasoning exposure
- no autonomous orchestration expansion
