# AOIA TUI Phase 1 Report

Date: 2026-05-25

Repository: `/home/l/Desktop/AOIA-Core`

Phase: Minimal Terminal Prototype - Observability + Operator Control

## 1. Installed Dependencies

Only the approved TUI dependencies were added to `runtime/requirements.txt`:

- `rich>=13.7.0`
- `textual>=0.86.0`

Installed versions in `runtime/.venv`:

| Package | Version |
|---|---:|
| `rich` | `15.0.0` |
| `textual` | `8.2.7` |
| `markdown-it-py` | `4.2.0` |
| `pygments` | `2.20.0` |
| `mdit-py-plugins` | `0.6.1` |
| `linkify-it-py` | `2.1.0` |
| `platformdirs` | `4.9.6` |
| `uc-micro-py` | `2.0.0` |

No FastAPI, Redis, Celery, LangGraph, CrewAI, AutoGen, Electron, or new browser framework was installed.

## 2. TUI Structure

Created:

```text
tui/
|-- __init__.py
|-- app.py
|-- widgets/
|   |-- __init__.py
|   |-- log_panel.py
|   `-- status_panel.py
`-- views/
    |-- __init__.py
    `-- dashboard.py
```

The TUI imports the existing runtime directly and does not move existing runtime modules.

## 3. Runtime Compatibility Verification

The TUI wraps:

- `AgentRuntime`
- `ProviderManager`
- `AgentRuntime.snapshot_status()`
- existing provider switching through `ProviderManager.switch_model()`
- existing session log paths

No runtime orchestration, retrieval, provenance, provider adapter, or approval semantics were rewritten.

The dashboard displays:

- current provider/model
- cwd
- retrieval status
- session log path
- memory mode
- approval mode
- kill switch state
- active memory hat
- safe operational events

## 4. Safe Log Panel

`LogPanel` tails only safe operational event kinds:

- `action_result`
- `local_route_result`
- `knowledge_route_hit`
- `knowledge_route_miss`
- `aoia_kernel_hit`
- `external_link_review`
- `external_repository_review`
- `planned_step_result`
- `step_result`
- `orchestrated_step_result`

It intentionally excludes:

- raw prompts
- raw model outputs
- hidden reasoning
- chain-of-thought
- reasoning trace internals

## 5. Provider Switching

Provider switching in the TUI maps to the existing provider manager:

```text
ProviderManager.switch_model(model_name)
```

Supported input examples:

- `gemini`
- `openrouter`
- `deepseek`
- `/model gemini`

No provider adapter logic was rewritten.

## 6. Safe Shutdown

The TUI supports:

- `q` to quit
- `Ctrl+C` terminal interruption
- Textual normal shutdown
- best-effort `tui_shutdown` operational event logging

No forced process termination behavior was introduced.

## 7. Tests

Added:

`tests/test_tui_phase1.py`

Coverage:

- status panel renders runtime snapshot fields
- log panel filters prompt/model-output events
- TUI app builds against existing runtime
- provider switching uses existing provider manager

Validation commands:

```bash
PYTHONPATH=runtime:. runtime/.venv/bin/python -m compileall -q runtime tui tests
PYTHONPATH=runtime:. runtime/.venv/bin/python -m unittest tests.test_tui_phase1 -v
PYTHONPATH=runtime:. runtime/.venv/bin/python -m unittest discover -s tests -v
```

Results:

| Check | Result |
|---|---:|
| Compile check | PASS |
| TUI smoke tests | PASS, 4 tests |
| Full unittest suite | PASS, 116 tests |
| Runtime import smoke | PASS |
| TUI import smoke | PASS |

Full suite result:

`Ran 116 tests in 7.444s - OK`

## 8. Startup Instructions

From repository root:

```bash
cd /home/l/Desktop/AOIA-Core
PYTHONPATH=runtime:. runtime/.venv/bin/python -m tui.app
```

Operator controls:

- `Ctrl+R`: refresh status
- `q`: quit
- provider input box: enter `gemini`, `openrouter`, `deepseek`, or `/model NAME`

## 9. Remaining Blockers

The minimal TUI is only an operator wrapper. Remaining larger blockers:

- No full command input execution panel yet.
- No live command approval modal yet.
- No interactive provider health test button yet.
- No log-level filtering controls yet.
- No packaged launcher script yet.
- No FastAPI or websocket system, by design.
- No PostgreSQL, by design.

## 10. Prototype Readiness Update

AOIA now has:

- stable runtime tests
- deterministic retrieval guard coverage
- environment audit
- minimal Textual/Rich wrapper
- safe status dashboard
- safe operational log tail
- provider switching wrapper

Prototype readiness improved from environment-prep state to first usable terminal-operator shell foundation.

## 11. Recommended Next TUI Milestone

Next milestone:

**TUI Phase 2 - Operator Command Console**

Scope:

- add an input panel that calls `AgentRuntime.run_text_request()`;
- display transcript output;
- preserve existing approval prompts;
- keep hidden reasoning and prompt internals out of the UI;
- add tests for command execution through the wrapper;
- add a launcher script such as `scripts/run_tui.sh`.

Do not add FastAPI, websocket systems, agents, autonomous loops, or new provenance semantics in the next milestone.
