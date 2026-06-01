# Dangerous Python APIs Index

Source status: schema_hardening_reference. This file is not runtime-integrated.

| API | risk_level | reason | required_policy | advisory_rule |
| --- | --- | --- | --- | --- |
| `eval` | critical | Executes Python expressions from strings. | `never_execute` or `reference_only_no_execution` | Never apply to user, model, or file input. Prefer `ast.literal_eval` only for trusted literal parsing. |
| `exec` | critical | Executes arbitrary Python code. | `never_execute` | Do not present as a corrected pattern for dynamic behavior. |
| `compile` | critical | Can compile attacker-controlled code for later execution. | `never_execute` | Avoid with untrusted input, especially `exec` mode. |
| `input` | high | User input is untrusted and may later feed unsafe APIs. | `reference_only_no_execution` | Validate and never pass to `eval` or `exec`. |
| `open` | medium | Can read sensitive files or overwrite data. | `reference_only_no_execution` | Use explicit modes, encoding, path validation, and context managers. |
| `getattr` | medium | Dynamic attribute access may expose internals or trigger code. | `reference_only_no_execution` | Use whitelists for dynamic names. |
| `setattr` | high | Dynamic mutation can break invariants or security boundaries. | `reference_only_no_execution` | Avoid on untrusted names or objects. |
| `delattr` | high | Dynamic deletion can break object invariants. | `reference_only_no_execution` | Avoid on untrusted names or objects. |
| `globals` | high | Exposes global namespace and can support injection. | `reference_only_no_execution` | Do not mutate returned namespace in examples. |
| `locals` | high | Exposes local namespace and can mislead about mutability. | `reference_only_no_execution` | Use for diagnostics only, not control flow. |
| `import` | critical | Dynamic import can load unintended modules. | `never_execute` | Use explicit imports or whitelisted `importlib` usage. |
| `subprocess.run` | high | Executes system commands; shell use enables injection. | `reference_only_no_execution` | Use list arguments, `shell=False`, `check=True`, and timeouts. |
| `os.system` | critical | Sends a string to the shell. | `never_execute` | Replace with reviewed `subprocess.run` list form. |
| `os.popen` | critical | Shell command execution with stream handling. | `never_execute` | Replace with reviewed `subprocess.run` list form. |
| `pathlib.Path.unlink` | medium | Deletes filesystem entries. | `requires_human_confirmation` | Require dry-run/confirmation and symlink review. |
| `os.remove` | medium | Deletes files. | `requires_human_confirmation` | Require dry-run/confirmation and path validation. |
| `os.unlink` | medium | Deletes filesystem entries. | `requires_human_confirmation` | Require dry-run/confirmation and symlink review. |
| `shutil.rmtree` | critical | Recursive deletion can destroy large directory trees. | `never_execute` | Require dry-run, confirmation, and strict path containment. |
| `pickle.load` | critical | Can execute code during untrusted deserialization. | `never_execute` | Never unpickle untrusted data; prefer JSON or safer formats. |
| `pickle.loads` | critical | Can execute code during untrusted deserialization. | `never_execute` | Never unpickle untrusted bytes; prefer JSON or safer formats. |
| `tempfile.NamedTemporaryFile` | medium | Misuse can create lifecycle and portability issues. | `reference_only_no_execution` | Prefer context managers and avoid predictable names. |
| `tempfile.mktemp` | high | Deprecated unsafe temp filename creation. | `never_execute` | Use `NamedTemporaryFile` or `TemporaryDirectory`. |
| `requests.get` | medium | Network calls can hang or leak data without timeout. | `reference_only_no_execution` | Always use `timeout=` and avoid secrets in URLs. |
| `requests.post` | medium | Network calls can hang or leak data without timeout. | `reference_only_no_execution` | Always use `timeout=` and protect credentials. |
| pip invocation from scripts | high | Can pollute system Python or execute package install hooks. | `requires_human_confirmation` | Prefer venv or pipx; forbid `sudo pip install`. |
