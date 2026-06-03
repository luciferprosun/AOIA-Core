# Terminal Provider Switcher Quickstart

## Scope

`scripts/terminal_provider_switcher.py` is a local AOIA-Core developer utility for inspecting API key presence, listing provider presets, selecting the current provider/model, and optionally sending one explicit prompt to the selected provider.

This is DEV-TOOLS-1. It is not GT-RUNTIME-9, not Bash Safety runtime work, not a terminal agent, and not an execution layer.

## Security Boundary

- API key values are never printed.
- API key values are never written by this tool.
- Key status is shown only as `present` or `missing`.
- `--status`, `--list`, `--select`, and `--dry-run` do not call model APIs.
- `--prompt` makes one live provider API call only when explicitly passed.
- `--prompt` may consume provider quota.
- Model output is printed as plain text only.
- Model output is never executed.
- The tool does not run shell commands returned by a model.
- The tool does not start a daemon, GUI, web app, or autonomous terminal agent.

## Commands

From the repository root:

```bash
./scripts/terminal_provider_switcher.py --help
./scripts/terminal_provider_switcher.py --status
./scripts/terminal_provider_switcher.py --list
./scripts/terminal_provider_switcher.py --select gemini --dry-run
./scripts/terminal_provider_switcher.py --select openrouter --dry-run
./scripts/terminal_provider_switcher.py --select gemini
./scripts/terminal_provider_switcher.py --select gemini --prompt "Say hello from AOIA terminal switcher."
```

## Provider Selection

`--select MODEL` accepts a preset alias such as `gemini` or `openrouter`, or a full `provider/model` name.

`--select MODEL --dry-run` resolves the selection and prints what would happen without writing the model config.

`--select MODEL` without `--dry-run` writes only the current model selection through the existing local `ProviderManager` state path. It does not write API keys.

## API Calls

Only `--prompt` calls a provider API. The prompt path intentionally calls the current or selected provider once and does not use fallback routing across multiple providers.

For Gemini one-shot prompt testing, the utility can call the Gemini HTTPS API directly with `GEMINI_API_KEY` or `GOOGLE_API_KEY`; it does not require the `google-genai` SDK for this dev-tool path.

If a key, SDK, network path, or provider backend is missing, the tool reports a graceful provider error with known secret values redacted.

## Expected Local Key Status

On the recovered June 3, 2026 environment, expected status was:

- `OPENROUTER_API_KEY`: present
- `GOOGLE_API_KEY`: present
- `GEMINI_API_KEY`: present
- other main provider keys: missing

Actual status depends on the current shell environment and private local secret files.
