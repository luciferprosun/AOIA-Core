# How to Reproduce GT-RUNTIME-6

## 1. Purpose

This guide lets a reviewer reproduce the local GT-RUNTIME-6 controlled regression harness.

## 2. Requirements

- Python 3.
- Repository checkout.
- No network required for the validator itself.
- No shell commands from the corpus are executed.

## 3. Safety Note

The corpus commands are inert test strings.
Do not copy or execute corpus command strings manually.
The validator classifies strings only.

## 4. Commands

```bash
git status --short
python3 -m compileall runtime tests
PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v
```

## 5. Expected Current Result

- Current expected test result: 372 tests run, 4 skipped, PASS.
- One pre-existing test may propose `sudo apt install curl`; it must not be executed manually.

## 6. Scope Note

No Cloudflare bindings, provider keys, GUI setup, or shell execution are required to reproduce this documentation-facing validation state.
