# Model Audit Evidence Policy

Model audit outputs are advisory material. They are useful for surfacing
questions, suspected issues, review priorities, and comparison signals, but
they are not canonical project evidence.

## Authoritative Evidence

Authoritative AOIA-Core evidence is:

- Source code.
- Tests.
- Commits.
- CI results.
- Reproducible artifacts.
- Human review decisions.

## Advisory Evidence

Model outputs can support review work when they are tied back to authoritative
evidence. A model report can say where to look, but it does not establish that
a bug, fix, or safety property exists.

## Required Handling

- Verify model claims against repository files and commit history.
- Prefer exact file paths, commit hashes, test names, and CI run evidence.
- Keep large generated artifacts outside the repository unless there is an
  explicit archival reason and size policy approval.
- Use checksums for external PDFs, ZIPs, and full snapshots when possible.
- Record human decisions separately from model suggestions.

## Canonical Status

No model output promotes knowledge, modifies runtime policy, changes safety
classification, or establishes canonical truth by itself. Canonical status
requires the normal AOIA review path and explicit human approval.
