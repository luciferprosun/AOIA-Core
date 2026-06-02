# GT-RUNTIME-7D Adversarial Corpus Stub Report

- Branch: `dev/gt-runtime-5-single-event-ledger`
- HEAD before GT-RUNTIME-7D: `bae1be9 test: add mocked approval gate control flow`

## Files Created

- `corpus/adversarial_v0.2_stub.jsonl`
- `docs/adversarial_corpus_v0.2_plan.md`
- `tests/test_adversarial_corpus_v0_2_stub.py`
- `docs/audit/GT_RUNTIME_7D_ADVERSARIAL_CORPUS_STUB_REPORT_02_JUNE_2026.md`

## Corpus Record Count

- `22`

## Categories Represented

- `whitespace_obfuscation`
- `quoting_tricks`
- `variable_interpolation`
- `command_substitution`
- `encoded_payload_indicator`
- `heredoc_indicator`
- `chained_commands`
- `pipe_to_shell`
- `redirection_to_sensitive_path`
- `recursive_permission_change`
- `privilege_escalation_indicator`
- `safe_command_false_positive_trap`
- `ambiguous_admin_command`
- `context_dependent_danger`
- `unknown_or_incomplete_command`

## Validation Commands

```bash
PYTHONPATH=runtime:. python3 -m unittest tests.test_adversarial_corpus_v0_2_stub -v
python3 -m compileall runtime tests
PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v
```

## Validation Results

- Targeted GT-RUNTIME-7D test: PASS
- `python3 -m compileall runtime tests`: PASS
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`: PASS

## Final Git Status Before Commit

```text
?? corpus/adversarial_v0.2_stub.jsonl
?? docs/adversarial_corpus_v0.2_plan.md
?? docs/audit/GT_RUNTIME_7D_ADVERSARIAL_CORPUS_STUB_REPORT_02_JUNE_2026.md
?? tests/test_adversarial_corpus_v0_2_stub.py
```

## Stash Status

Cloudflare stash was not touched:

`stash@{0}: On dev/gt-runtime-5-single-event-ledger: WIP cloudflare context before post-GT-RUNTIME-6 baseline report`

## Scope Statement

"GT-RUNTIME-7D added an inert adversarial corpus v0.2 stub only. No shell execution, runtime executor, shell_tools, event ledger, provider, existing corpus, or Cloudflare logic was modified."

"GT-RUNTIME-7E has not started."
