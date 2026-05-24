# Linux Retrieval Engine v1 Report

Phase: AIOA Linux Knowledge Layer - Deterministic Retrieval Engine v1

## Purpose

This layer provides the first operational local retrieval execution path for RHCSA/Linux knowledge. It is infrastructure, not chatbot behavior.

The engine answers only from existing local evidence-backed knowledge artifacts and refuses low-confidence queries instead of inventing commands.

## Reused Architecture

The implementation reuses the existing AIOA runtime knowledge structure:

- `runtime/knowledge/`
- `runtime/knowledge/canonical/rhcsa_commands.json`
- `runtime/knowledge/index/command_index.json`
- `runtime/knowledge/parsed/rhcsa_sections.json`
- `runtime/knowledge/command_graph.json`
- `runtime/tools/rhcsa_search.py`
- `runtime/knowledge/rhcsa_engine.py`
- `runtime/memory/rhcsa_context.py`

No runtime router, epistemic kernel, external provider, vector database, embedding layer, or agent loop was added.

## New Files

- `runtime/retrieval/linux/query_normalizer.py`
- `runtime/retrieval/linux/scoring.py`
- `runtime/retrieval/linux/provenance_attach.py`
- `runtime/retrieval/linux/retrieval_engine.py`
- `tests/test_linux_retrieval.py`

## Retrieval Flow

```text
query
  -> normalization
  -> exact command lookup
  -> alias lookup
  -> subcommand lookup
  -> category lookup
  -> command family lookup
  -> keyword lookup
  -> low-confidence refusal
  -> provenance-attached bounded response
```

## Supported Lookup Modes

- Exact command lookup
- Alias lookup
- Subcommand lookup
- Category lookup
- Keyword lookup
- Command family lookup through `command_graph.json`

## Scoring Logic

Deterministic score buckets:

- exact match: `100`
- alias match: `92`
- subcommand match: `84`
- category match: `65`
- command family match: `58`
- keyword match: `45`
- low confidence: `20`
- refusal threshold: below `30`

Confidence labels:

- `high`: score >= 90
- `medium`: score >= 60
- `low`: score >= 30
- `none`: score < 30

## Provenance Output

Every answered result attaches:

- source file
- source page if available
- canonical source
- confidence score

Current canonical source is read from:

- `runtime/knowledge/manifests/library_manifest.yaml`

Current canonical PDF:

- `runtime/knowledge/source/linux_master_library_v1.pdf`

## Hallucination Boundaries

The engine must not:

- invent commands
- infer missing syntax
- call external APIs
- use embeddings
- use vector databases
- rewrite runtime routing
- modify epistemic kernel state
- enter autonomous reasoning loops

If local confidence is too low, it refuses and asks for clarification.

## Example Behaviors

Exact command:

```text
query: ls
status: answered
match_type: exact
confidence: high
```

Alias:

```text
query: firewall
status: answered
match_type: alias
alias target: firewall-cmd
```

Category:

```text
query: filesystem
status: answered
match_type: category
confidence: medium
```

Failure/refusal:

```text
query: zzzz-not-a-linux-command-xyz
status: refused
confidence: none
message: clarify the command, category, or Linux task
```

## Limitations

- Source page is `null` unless a future parser records page numbers.
- Alias table is intentionally small and deterministic.
- Keyword lookup is lexical, not semantic.
- Candidate indexes from the new Library of Linux PDF are not yet promoted into canonical runtime JSON.
- The engine is not wired into the runtime router in this phase.

## Next Architecture Phase

Build the deterministic index loader:

1. parse `runtime/knowledge/extracted/linux_master_library_v1.txt`
2. generate candidate command records with source page metadata
3. deduplicate against `rhcsa_commands.json`
4. review aliases and command families
5. validate schema
6. then update canonical indexes append-only
