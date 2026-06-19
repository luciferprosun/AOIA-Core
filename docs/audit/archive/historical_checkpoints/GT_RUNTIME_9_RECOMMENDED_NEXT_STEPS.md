# GT-RUNTIME-9 Recommended Next Steps

## Position

GT-RUNTIME-9 should begin conservatively. The immediate next step should remain non-executing and should not introduce shell execution, a terminal agent, an approval API, a GUI, an event ledger integration, or a runtime pipeline facade.

## Recommended Conservative Options

| Option | Direction | Execution Boundary |
|---|---|---|
| A | Corpus v0.4 expansion | Inert strings only; no execution. |
| B | Parser hardening from remaining gaps | Static classification only; no command running. |
| C | Formal threat model update | Documentation only. |
| D | Inert event/audit schema preparation | Schema/reviewer design only; no `event_ledger.py` integration. |
| E | Reviewer/security package consolidation | Documentation and validation packaging only. |

## Option A: Corpus v0.4 Expansion

Expand adversarial coverage without changing runtime architecture. Possible areas:

- quoting and escaping variants
- variable and arithmetic expansion markers
- more process substitution and here-string shapes
- interpreter wrapper chains
- package-manager mutation shapes
- symlink-sensitive command text
- more Unicode and encoding markers

Corpus records should remain inert strings only.

## Option B: Parser Hardening From Remaining Gaps

Continue small, targeted static classification improvements. Prefer:

- `dangerous` for clearly destructive/static risky shapes
- `ambiguous` for wrappers, obfuscation, and unclear shell syntax
- `unknown` when parsing confidence is too low
- `safe` only for narrow read-only command contracts

Do not broaden `safe` classification aggressively.

## Option C: Formal Threat Model Update

Update the threat model before any future execution discussion. The model should clarify:

- command-string threats
- parser bypass classes
- reviewer misunderstanding risks
- trust boundaries
- non-goals
- what OS isolation would be required for any future prototype

## Option D: Inert Event/Audit Schema Preparation

If audit work continues, keep it inert first. Define event shapes, review vocabulary, and validation contracts without writing to disk and without integrating `event_ledger.py`.

Do not present inert audit objects as compliance-grade audit records.

## Option E: Reviewer/Security Package Consolidation

Create a small reviewer package that points to the boundary statement, validation summary, coverage matrix, gap report, and parser-hardening report. This can improve external review without adding runtime capability.

## Staged Gate Before Any Future Execution

Any future execution prototype should require all of the following gates first:

1. Threat model update.
2. External review.
3. Sandbox design.
4. Explicit human approval design.
5. Rollback/audit design.
6. Non-production prototype only.

Execution should not be introduced until these gates are complete and explicitly approved in a separate milestone.

## Not Recommended as Immediate GT-RUNTIME-9 Work

- shell execution
- command runner
- terminal agent
- API approval endpoint
- GUI approval flow
- event ledger integration
- provider/routing changes
- Cloudflare integration
- NiFe runtime
- production shell safety claims

## Recommended Next Safe Step

Start GT-RUNTIME-9 with a non-execution milestone: either corpus v0.4 planning/expansion or a formal Bash Safety threat model update.
