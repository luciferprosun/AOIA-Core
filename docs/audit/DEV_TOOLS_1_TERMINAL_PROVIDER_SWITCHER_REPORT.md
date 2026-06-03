# DEV-TOOLS-1 Terminal Provider Switcher Report

## Phase

DEV-TOOLS-1 - Terminal Provider Switcher

## Repository State

- Repository: `/home/l/Desktop/AOIA-Core`
- Branch: `dev/gt-runtime-8-bash-safety-planning`
- Base HEAD before DEV-TOOLS-1 commit: `de30e0f docs: add GT-RUNTIME-8M final savepoint pack`
- GT-RUNTIME-8 status: closed
- GT-RUNTIME-9 status: not started
- Cloudflare stash: untouched

## Scope

This checkpoint finalizes a local terminal developer utility:

- `scripts/terminal_provider_switcher.py`
- `docs/dev/TERMINAL_PROVIDER_SWITCHER_QUICKSTART.md`
- `docs/audit/DEV_TOOLS_1_TERMINAL_PROVIDER_SWITCHER_REPORT.md`

The work is not GT-RUNTIME-9 and does not modify Bash Safety runtime behavior.

## Security Boundary

The terminal switcher remains non-executing:

- No shell execution was added.
- No command runner was added.
- No autonomous terminal agent was added.
- No background daemon was added.
- No GUI, web app, or API endpoint was added.
- No model output execution path was added.
- Model output is printed as text only.

API key handling:

- API key values are not printed.
- API key values are not written by the tool.
- Status output shows keys only as `present` or `missing`.
- Known secret values are redacted from provider error messages.

API call handling:

- `--status` does not call model APIs.
- `--list` does not call model APIs.
- `--select` does not call model APIs.
- `--dry-run` does not call model APIs and cannot be combined with `--prompt`.
- `--prompt` is the only path that calls a provider API.
- `--prompt` warns that API use may consume quota.
- `--prompt` calls the current or selected provider once and avoids fallback routing across multiple providers.
- Gemini one-shot prompt testing can use the Gemini HTTPS API directly with `GEMINI_API_KEY` or `GOOGLE_API_KEY`.

## Validation Commands

Required local validation set:

```bash
./scripts/terminal_provider_switcher.py --help
./scripts/terminal_provider_switcher.py --status
./scripts/terminal_provider_switcher.py --list
./scripts/terminal_provider_switcher.py --select gemini --dry-run
./scripts/terminal_provider_switcher.py --select openrouter --dry-run
./scripts/terminal_provider_switcher.py --select gemini
./scripts/terminal_provider_switcher.py --select gemini --prompt "Say hello from AOIA terminal switcher."
```

Additional static validation:

```bash
python3 -c 'from pathlib import Path; import ast; ast.parse(Path("scripts/terminal_provider_switcher.py").read_text(encoding="utf-8"))'
```

## Validation Result

Validated on June 3, 2026:

- `--help`: PASS
- `--status`: PASS; key values were not printed.
- `--list`: PASS
- `--select gemini --dry-run`: PASS
- `--select openrouter --dry-run`: PASS
- `--select gemini`: PASS
- `--select gemini --prompt "Say hello from AOIA terminal switcher."`: PASS after explicit network approval; model output was printed as text only.
- Static AST parse: PASS

## Expected Key Status

Recovered local environment expectation:

- `OPENROUTER_API_KEY`: present
- `GOOGLE_API_KEY`: present
- `GEMINI_API_KEY`: present
- other main provider keys: missing

The validation output must not include actual API key values.

## Files Intentionally Not Modified

- Runtime safety files
- Runtime executor files
- Runtime shell tool files
- Runtime provider routing files
- Bash parser files
- Event ledger files
- Cloudflare files
- NiFe files
- `docs/future`
- GT-RUNTIME-9 files

## Result

DEV-TOOLS-1 provides a small local terminal utility for developer provider selection and one-shot prompt testing. It is intentionally bounded to provider inspection and text generation, with no model-output execution and no autonomous behavior.
