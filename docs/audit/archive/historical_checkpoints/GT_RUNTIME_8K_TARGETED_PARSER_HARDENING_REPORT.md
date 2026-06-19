# GT-RUNTIME-8K Targeted Parser Hardening Report

## Branch

`dev/gt-runtime-8-bash-safety-planning`

## Starting HEAD

`94fe1a0 docs: add GT-RUNTIME-8J Bash corpus coverage matrix`

## Files Modified

- `runtime/safety/bash_parser.py`
- `tests/test_bash_safety_corpus_v0_3_coverage.py`
- `docs/audit/GT_RUNTIME_8K_TARGETED_PARSER_HARDENING_REPORT.md`

## 8J Gaps Targeted

GT-RUNTIME-8K targets four narrow gaps from the 8J classifier gap report:

- process substitution and here-string shell runner variants
- encoded payload indicators that are not already pipe-to-shell
- sensitive redirection variants with file-descriptor prefixes
- Unicode/confusable command indicators

## Parser Heuristics Changed

`runtime/safety/bash_parser.py` was updated with static classification only:

- Shell runners using process substitution, such as `bash <(...)`, classify as `dangerous`.
- Standalone encoded payload decode markers such as `base64 -d ...` classify as `ambiguous` unless an existing pipe-to-shell rule already makes them `dangerous`.
- Redirections such as `2>/etc/...`, `2>>/root/...`, and `&>/etc/...` are recognized as sensitive-path redirection and classify as `ambiguous`.
- Commands containing non-ASCII markers classify as `ambiguous`.

These changes do not decode payloads, expand shell syntax, inspect files, access the network, or execute commands.

## Tests Added or Updated

`tests/test_bash_safety_corpus_v0_3_coverage.py` was updated with targeted GT-RUNTIME-8K cases:

- `bash <(echo rm -rf /)` -> `dangerous`
- `base64 -d <<< cm0gLXJmIC8=` -> `ambiguous`
- `echo test 2>/etc/cron.d/example` -> `ambiguous`
- a non-ASCII command marker example -> `ambiguous`

The existing v0.3 corpus was not modified.

## What Remains Unresolved

- The parser is still heuristic and not a full Bash grammar.
- It does not model shell expansion, aliases, functions, globbing, arithmetic expansion, process execution, or OS state.
- It does not decode base64 or escaped payload bytes.
- Unicode handling remains conservative marker detection, not normalization or homoglyph analysis.
- This does not replace ShellCheck, sandboxing, seccomp, firejail, nsjail, bubblewrap, containers, or OS-level containment.

## No-Execution Boundary

GT-RUNTIME-8K remains pre-execution inspection only. It does not execute shell commands.

No shell execution capability was added. No subprocess, `os.system`, `shell=True`, `Popen`, `eval`, or `exec` path was added.

No runtime facade or pipeline was added. No `runtime/safety/pipeline.py`, `evaluate_command_text`, `evaluate_and_audit_command`, or `HumanApprovalRequest` was added.

No event ledger integration was added.

## Validation Commands and Results

Targeted validation:

```text
PYTHONPATH=runtime:. python3 -m unittest tests/test_bash_safety_corpus_v0_3.py -v
PYTHONPATH=runtime:. python3 -m unittest tests/test_bash_safety_corpus_v0_3_coverage.py -v
```

Result: PASS.

Full validation to record before closure:

```text
python3 -m compileall runtime tests
PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v
```

Result: PASS, 470 tests run, 4 skipped.

Static safety scans:

- Full-repository forbidden primitive scan still reports existing historical references in `.venv`, older tests, and older audit docs.
- Scoped scan of the GT-RUNTIME-8K changed parser/test files found no new forbidden execution primitive use.
- Scoped scan of the GT-RUNTIME-8K report found boundary statements only.

## Final Git Status

```text
 M runtime/safety/bash_parser.py
 M tests/test_bash_safety_corpus_v0_3_coverage.py
?? docs/audit/GT_RUNTIME_8K_TARGETED_PARSER_HARDENING_REPORT.md
```

## Cloudflare Stash

Cloudflare stash untouched.

## GT-RUNTIME-8L

GT-RUNTIME-8L was not started.
