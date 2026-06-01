# Python Master Library First Cross-Check Targets

This file is a planning list only. It does not assert that any target has been checked, resolved, or promoted.

## H19 Draft Advisory Batch Note
H19 created draft advisory records for the first dangerous built-ins and dynamic execution batch. No official cross-check was performed, no status was promoted, and these records remain first targets for H20/H21 human and official-doc review.

| priority | record_or_term | domain | reason | expected_official_source | action |
| --- | --- | --- | --- | --- | --- |
| 1 | eval | builtins | dangerous built-in with code execution risk | docs.python.org built-in functions documentation | cross-check behavior and safety notes |
| 1 | exec | builtins | dangerous built-in with code execution risk | docs.python.org built-in functions documentation | cross-check behavior and safety notes |
| 1 | compile | builtins | compilation surface tied to exec/eval flows | docs.python.org built-in functions documentation | cross-check behavior and risk wording |
| 1 | import | language syntax | import semantics affect code loading and trust boundaries | docs.python.org language reference | cross-check syntax and scope wording |
| 1 | open | builtins/files | file access and overwrite risk surface | docs.python.org built-in functions documentation | cross-check modes, overwrite, encoding notes |
| 1 | input | builtins | user-input handling and trust boundary | docs.python.org built-in functions documentation | cross-check behavior and safety notes |
| 1 | subprocess.run | subprocess | command execution and shell safety | docs.python.org subprocess documentation | cross-check shell safety guidance |
| 1 | os.system | os | shell execution risk | docs.python.org os documentation | cross-check legacy command execution warnings |
| 1 | os.popen | os | shell/process invocation and legacy API risk | docs.python.org os documentation | cross-check behavior and caution notes |
| 1 | shutil.rmtree | shutil | destructive recursive deletion | docs.python.org shutil documentation | cross-check destructive semantics |
| 1 | os.remove | os | deletion primitive | docs.python.org os documentation | cross-check file deletion semantics |
| 1 | os.unlink | os | deletion primitive alias/sibling | docs.python.org os documentation | cross-check deletion semantics |
| 1 | pathlib.Path.unlink | pathlib | object-oriented deletion API | docs.python.org pathlib documentation | cross-check delete behavior and missing_ok notes |
| 1 | pickle.load | serialization | untrusted deserialization risk | docs.python.org pickle documentation | cross-check security warning wording |
| 1 | pickle.loads | serialization | untrusted deserialization risk | docs.python.org pickle documentation | cross-check security warning wording |
| 1 | tempfile.mktemp | tempfile | historically unsafe temporary file pattern | docs.python.org tempfile documentation | cross-check warning and safer alternatives |
| 1 | tempfile.NamedTemporaryFile | tempfile | safer temp file workflow with platform caveats | docs.python.org tempfile documentation | cross-check behavior and caveats |
| 1 | json.loads | serialization | common parsing API with trust and type assumptions | docs.python.org json documentation | cross-check parsing behavior |
| 1 | tomllib.load | serialization | version-scoped parser in newer Python | docs.python.org tomllib documentation | cross-check version scope and behavior |
| 2 | match/case | language syntax | version-specific syntax introduced in newer Python | docs.python.org language reference and peps.python.org | cross-check syntax and version scope |
| 2 | ExceptionGroup | exceptions | new exception grouping behavior | docs.python.org exceptions documentation and peps.python.org | cross-check semantics and version scope |
| 2 | type statement / PEP 695 | typing/language | version-specific typing feature | peps.python.org and docs.python.org language reference | cross-check syntax and version scope |
| 2 | free-threaded Python / PEP 703 | runtime/implementation notes | version-specific interpreter change with caveats | peps.python.org and relevant official Python docs | cross-check status and scope wording |
