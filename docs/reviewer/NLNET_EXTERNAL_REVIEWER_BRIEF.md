# NLnet External Reviewer Brief

## Purpose

This repository should be reviewed as a local-first, non-executing inspection
and audit layer for AI-proposed shell commands.

The current public scope is narrow:

- parse and classify proposed shell commands
- identify known dangerous shell shapes
- produce dry-run safety decisions
- record approval and audit metadata
- preserve provenance and evidence-boundary context

`allowed=True` means the proposed command passed inspection. It does not mean
the command will execute.

## What To Verify

A reviewer can confirm the current claim in five minutes by checking:

- `README.md`
- `docs/governance/IMPLEMENTED_CAPABILITIES.md`
- `docs/reviewer/PROJECT_OVERVIEW_FOR_REVIEWERS.md`
- `docs/reviewer/ONE_CONCRETE_EXAMPLE.md`
- `docs/REVIEWER_QUICKSTART.md`

These documents should all describe the same boundary: inspection and audit,
not shell execution, sandboxing, terminal automation, or autonomous agent
behavior.

## What Not To Infer

Do not infer that the repository currently claims:

- shell execution
- sandboxed execution
- browser automation safety
- provider truth validation
- production readiness
- autonomous agent operation

Historical runtime entrypoints and legacy provider/web/TUI references may still
exist in the tree. They are not the current NLnet second-review claim unless a
current governance document explicitly promotes them.

## Clutter Note

The repository contains a large amount of historical PDF and documentation
material. Much of it is archival, forensic, or grant-context material rather
than active runtime authority. Reviewers should rely on the explicit reviewer
and governance docs above instead of assuming every file reflects the current
public scope.
