# AOIA Single Event Ledger Plan

Date: 2026-05-28
Scope: analysis only.

## Current Event / Log / Provenance Sinks

| Sink | Path | Current role | Plan |
| --- | --- | --- | --- |
| Append-only provenance log | `provenance/provenance_log.jsonl` via `runtime/tools/provenance.py` | Hash-chained event ledger | Keep as conceptual core; rename target to `provenance.log.jsonl` in AOIA-Nano. |
| Provenance registry | `runtime/provenance_registry.json` | Knowledge artifact registry | Convert to manifest/artifact input to ledger, not a live event sink. |
| Evidence memory | `runtime/memory/evidence_memory.jsonl` | Evidence entries with source/fingerprint restrictions | Fold into `retrieval_hit`, `retrieval_miss`, and `action_result` events. |
| Reasoning trace | `runtime/memory/reasoning_trace.jsonl` | Internal reasoning and route trace | Replace with bounded `route_decision` and `action_proposed` metadata; avoid unbounded chain-of-thought style capture. |
| History | `runtime/memory/history.jsonl` | Runtime history | Fold into event ledger. |
| Session logs | `runtime/logs/sessions/*.jsonl` | Session event timeline | Fold into event ledger using `run_id`. |
| Command logs | `runtime/logs/commands/*.json` | Command execution records | Fold into `action_result`. |
| Error logs | `runtime/logs/errors/*.json` | Runtime exceptions | Fold into `action_result` with `status=error`. |
| Obsidian session logs | `runtime/obsidian_vault/Sessions/*.jsonl` | Duplicate session timeline | Move out of runtime repo or generate from ledger as optional view. |
| Obsidian evidence/reasoning notes | `runtime/obsidian_vault/Evidence`, `runtime/obsidian_vault/Reasoning` | Markdown projection of memory events | Move out of runtime repo; treat as derived view. |
| Token report | `runtime/state/token_savings_report.json` | Knowledge-router metrics | Fold into `route_decision` facet/metadata or keep external runtime state. |
| Provider state | `runtime/state/providers.json`, `state/providers.json` | Provider config/state | Move to local runtime config, not ledger. |
| Model config | `runtime/state/model_config.json`, `state/model_config.json` | Mutable runtime choice | Move to local runtime config, not ledger. |
| Runtime reports | `runtime/reports/*.md` | Generated stabilization/checkpoint reports | Archive as historical docs, not live event sinks. |

## Target Ledger

Target file:

```text
provenance.log.jsonl
```

Each line should be canonical JSON with at least:

- `schema_version`
- `run_id`
- `event_id`
- `timestamp`
- `event_kind`
- `actor`
- `payload`
- `payload_digest`
- `previous_entry_digest`
- `entry_digest`

## Minimal Event Kinds

- `request_received`
- `route_decision`
- `retrieval_hit`
- `retrieval_miss`
- `action_proposed`
- `action_approved`
- `action_result`
- `provider_call_requested`
- `provider_call_completed`
- `replay_verified`

## Consolidation Principle

The ledger should be the authoritative write path. Markdown notes, Obsidian views, command reports, token reports, and standard exports should be derived artifacts, not separate sources of truth.
