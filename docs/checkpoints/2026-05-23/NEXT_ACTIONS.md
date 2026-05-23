# Next Actions

Date: 2026-05-23
Repository: `/home/l/Desktop/AOIA-Core`
Mode: checkpoint guidance

## Recommended Next Step

The next safest step is repository validation and checkpoint commit hygiene.

Before any new implementation:

- Review untracked documentation under `docs/refactor/`.
- Review untracked validation report under `docs/reports/`.
- Decide whether `docs/forensic-runtime-audit/` should be committed as architecture audit material.
- Keep `state/` uncommitted unless a specific runtime-state policy is accepted.
- Confirm Phase 2A containment diff remains minimal.
- Run the focused containment test again.

## What Must Not Be Done Next

Do not:

- split `memory.py`
- create memory adapters
- redesign retrieval
- modify providers
- modify routing
- implement governance
- redesign Vault
- move runtime directories
- treat `memory/evidence_memory.jsonl` as canonical L4
- index L0/L1/L2/Vault in retrieval
- commit `state/` by default
- push to LSC or MHLM/MDLH repositories

## Safest Phase 2B Candidate

Safest Phase 2B candidate:

- Add a narrow evidence-write validation boundary around `append_evidence()` usage.

Goal:

- Ensure only explicitly approved evidence-like events can call evidence storage.
- Preserve existing kernel evidence flow until L4 schema exists.
- Do not redesign evidence storage yet.
- Do not implement CAS yet.
- Do not implement retrieval guard yet.

Alternative safe Phase 2B candidate:

- Add documentation-only migration notes for legacy `memory/evidence_memory.jsonl` as quarantined mixed memory.

## Repo Readiness For Next Implementation Phase

Ready:

- Ready for narrow pseudo-evidence containment validation.
- Ready for documentation checkpointing.
- Ready for focused regression tests around executor containment.

Not ready:

- Not ready for broad memory split.
- Not ready for retrieval guard implementation.
- Not ready for CAS evidence store implementation.
- Not ready for governance runtime implementation.

Reason:

- Phase 2A contained the strongest active leak, but L4 schema, CAS evidence model, L2 physical quarantine, provenance event schema, and contradiction event schema are not yet implemented.

## Tomorrow's Recommended Order

1. Validate current worktree.
2. Decide which documentation directories should be committed.
3. Keep `state/` out of git unless explicitly approved.
4. Commit Phase 2A containment and checkpoint docs.
5. Only then define Phase 2B scope.

## Stop Rule

If a proposed next change touches provider logic, routing logic, governance, or broad memory architecture, stop and create a new explicit phase document before implementation.
