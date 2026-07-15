# AOIA-Core Status

## Current

AOIA-Core is a development prototype with a local-first, human-controlled
authority model. Provider Runtime, Selector and Critic; Artifact Preview;
ActionProposal; controlled write and human-gate bindings; Durable Audit Ledger;
Knowledge Foundation; Linux, Bash, Python and UNIX Hats; retrieval; routing;
offline review; adversarial validation; and deterministic evidence are present.

The baseline entering Cleanup 1E was 3,255 passed, 4 skipped, 0 failures, and
0 errors. The current UNIX freeze is `aoia-unix-unit-1a-r1`.

## Packaging and commands

`pyproject.toml` defines both the `runtime.*` package and the retained top-level
compatibility imports. After the documented editable installation, no
`PYTHONPATH=runtime:.` workaround is required for the stable developer flow.
The canonical commands are maintained and tested in `README.md`.

## Authority status

AOIA-Core is not an autonomous executor. Provider and critic output, previews,
proposals, knowledge, Hat descriptors, routes, retrieval results, audit records,
manifests, and freezes are metadata only. Only the existing separate canonical
human barrier may authorize its exact controlled path.

## Next controlled step

The next permitted roadmap step after successful Cleanup 1E is isolated
clean-clone and full-prototype validation. No commit, push, release ZIP, or
deployment is authorized by this status document.
