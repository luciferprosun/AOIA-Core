# AOIA Knowledge Hat Index

This file is a reviewer-facing map of the current AOIA-Core knowledge library.
It documents the existing knowledge domains and intake rules. It does not add
runtime behavior, command execution, or a new architecture layer.

## Hat 001: Bash Safety Corpus

Hat 001 is the Bash Safety corpus.

Location:
- `tests/corpus/`

Purpose:
- defines behavioral risk examples for shell-like command text
- records dangerous, ambiguous, safe, and unknown boundary cases
- covers risky patterns such as destructive deletion, privilege use, pipe-to-shell,
  command substitution, chaining, redirection, wrapper commands, and false-positive
  or false-negative traps

Boundary:
- Hat 001 is test/corpus material only
- it does not permit command execution
- it does not make a command safe to run
- it supports pre-execution inspection and regression testing

## Hat 002: RHCSA / Linux Admin Knowledge

Hat 002 is the RHCSA/Linux administration knowledge library.

Location:
- `runtime/knowledge/`

Purpose:
- stores structured Linux administration knowledge
- covers RHCSA/Linux domains such as filesystems, permissions, users, groups,
  systemd, networking, storage, LVM, SELinux, Podman, troubleshooting, Bash, and
  package management
- separates source material, raw extraction, extracted text, canonical records,
  candidate records, indexes, grammar patterns, validation material, and reports

Boundary:
- Hat 002 is knowledge/reference material
- it does not automatically permit command execution
- a command appearing in Hat 002 is not approval to run it
- reviewer-safe execution remains blocked by default

## Canonical / Candidate / Rejected Model

GT-RUNTIME-11C froze the current Desktop filtered inventory baseline:

- canonical records: `848`
- candidate/review records: `2618`
- rejected/noise records: `175`

Meaning:
- `canonical` is the current reviewed working seed
- `candidate/review` is quarantined material that requires review before use
- `rejected` is retained as noise memory to avoid reintroducing known bad or
  fragmentary records

These counts describe the frozen GT-RUNTIME-11C Desktop inventory baseline, not
automatic runtime authority.

## Intake Rule For New Commands

Before adding any new Linux/Bash/RHCSA command or pattern:

1. Check the GT-RUNTIME-11C filtered CSV in the Desktop inventory.
2. Do not add directly to canonical data.
3. Add new material through candidate/review intake first.
4. Promotion must go through `review_queue` and `promote_candidates.py`.
5. Do not bulk auto-promote candidate material.
6. Preserve provenance and review status for every promoted item.

## Source Governance

Use `runtime/knowledge/provenance/PROVENANCE_POLICY.md` as the source governance
reference for provenance, source authority, and promotion discipline.
