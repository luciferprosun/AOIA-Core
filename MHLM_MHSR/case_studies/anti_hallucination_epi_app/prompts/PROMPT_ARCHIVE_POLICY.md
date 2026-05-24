# Prompt Archive Policy

Phase: 2 AOIA forensic migration

## Purpose

Prepare prompt archival rules without normalizing or migrating prompts yet.

## Raw Prompts

Raw prompts are preserved exactly as captured from their source.

Rules:

- preserve original text
- preserve original filename when available
- record source path or export source
- record capture timestamp
- do not edit provider/system/user boundaries

Target:

- `prompts/raw/`

## Normalized Prompts

Normalized prompts may be created in a future phase only after raw prompt preservation.

Rules:

- must point back to raw prompt source
- may normalize filename, metadata, and layout
- must not remove provenance-relevant content
- must not merge AOIA and LSC prompts

Target:

- `prompts/normalized/`

## Provider Tagging

Provider tags must be explicit:

- `claude`
- `gemini`
- `kimi`
- `codex`
- `deepseek`
- `unknown`

If provider is uncertain, use `unknown`.

## Timestamp Policy

Use ISO-style timestamps where possible:

- `YYYY-MM-DD`
- `YYYY-MM-DDTHH-MM-SS`

Do not infer timestamps from memory if source metadata is absent.

## Phase 2 Stop Rule

No prompt normalization was performed in Phase 2.
