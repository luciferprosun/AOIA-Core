# Memory Hats / WhiteHat v0.1 Prototype Status — 1 June 2026

## 1. Executive Status

The Memory Hats / WhiteHat v0.1 dev prototype exists on the `dev/rhcsa-command-grammar-layer` branch.

It is not merged to `main`. The protected NLnet-safe `main` branch remains at `d7e3448`, with `origin/main` also at `d7e3448`.

The prototype is advisory-only. It is a local-first correction memory layer for known Linux/RHCSA command-shape mistakes and does not execute commands, route runtime behavior, or prove command safety.

## 2. What Is Implemented

- GT-HAT-1: standalone dataclasses and enums for `PheromoneTag`, `TagType`, `ReviewStatus`, and advisory-only safety level.
- GT-HAT-2: deterministic trigger normalization and SHA-256 fingerprint hashing.
- GT-HAT-3: standalone Leaf-Vein path builder and parser.
- GT-HAT-3B: canonical `runtime/memory_hats/__init__.py` package init.
- GT-HAT-4: one-table local SQLite tag store for `pheromone_tags`.
- GT-HAT-5: `AdvisoryWarning` data object and tag-to-advisory conversion.
- GT-HAT-6: narrow RHCSA advisory lookup integration inside `runtime/memory_hats`.
- GT-HAT-8: local JSONL export/import helpers for `PheromoneTag` records.
- GT-HAT-7: tiny local Linux/RHCSA seed example tag set.
- GT-HAT-9: end-to-end prototype test for seed loading, SQLite import, and advisory lookup.

## 3. End-To-End Prototype Proof

The GT-HAT-9 test proves the minimal local pipeline:

- Seed JSONL is loaded from `runtime/knowledge/memory_hats/linux_rhcsa_seed_tags.jsonl`.
- Tags are imported into an in-memory `SQLiteTagStore`.
- The command-like input `dnf status sshd` is normalized and mapped to the Memory Hats RHCSA advisory lookup path.
- A confirmed seed tag returns an active high-confidence `AdvisoryWarning`.
- A missing command returns `None`.
- A candidate seed returns a low-confidence advisory.
- Repeated seed import is idempotent.
- Lookup does not mutate `seen_count`.

## 4. What The Prototype Proves

- A local correction tag workflow can function with deterministic inputs.
- A known command hallucination pattern can produce an advisory warning.
- The path, hash, storage, JSONL, seed, and advisory pipeline works together.
- The workflow does not require command execution.
- The prototype can remain isolated from executor, router, provider, provenance, TUI, and web code.

## 5. What The Prototype Does Not Prove

- It does not prove truth.
- It does not eliminate hallucinations.
- It does not prove command safety.
- It does not replace ShellCheck or a Bash parser.
- It does not provide global or shared tags.
- It does not implement sync.
- It does not implement UI.
- It does not implement Memory Garden or Phi visualization.
- It does not merge to stable `main`.

## 6. Safety Boundaries

- No command execution.
- No subprocess or shell calls.
- No prompt injection.
- No automatic model feedback.
- No network behavior.
- No sync or global tags.
- No runtime executor integration.
- No merge to `main`.

## 7. Current Branch / Tag / Test Status

- Dev branch: `dev/rhcsa-command-grammar-layer`
- Latest prototype commit before closure docs: `3399265 test(memory-hats): add end-to-end RHCSA advisory prototype [GT-HAT-9]`
- Latest dev tag before closure docs: `dev-memory-hats-gt-hat-9`
- Latest full unittest result: `Ran 283 tests, OK (skipped=4)`
- Protected `main`: `d7e3448`
- Protected `origin/main`: `d7e3448`
- Stable tag: `nlnet-safe-d7e3448`

## 8. Safe Public Wording

Use grant-safe wording:

- "local-first human-reviewed correction memory layer"
- "advisory warning"
- "known-error boundary detection"
- "does not prove truth"
- "does not execute commands"

Avoid overclaims:

- no "truth engine"
- no "hallucination cure"
- no "command safety proof"
- no "autonomous correction"
- no "production-ready safety layer"
