# RHCSA Engine Review

Review date: 2026-05-21

Reviewed file:

```text
knowledge/rhcsa_engine.py
```

## Classification

Classification: LEGACY, NEEDS ISOLATION.

It is not unsafe by itself, but it is not part of the new static AOIA Knowledge
Pack pipeline.

## Findings

### Retrieval Logic

Present: YES.

The engine imports and calls:

- `search_commands`
- `search_workflows`
- `retrieve_examples`
- `search_rhcsa`

This is local retrieval over existing RHCSA memory/search utilities.

### Semantic Ranking

Present: PARTIAL.

The file does not use embeddings or model-based semantic ranking, but it does
compute a deterministic score and confidence value from counts of matched
commands, workflows, troubleshooting items, examples, related topics, and graph
matches.

### Scoring

Present: YES.

`_score()` assigns fixed weights to result types. `_confidence()` maps score
ranges to `high`, `medium`, `low`, or `none`.

### Hidden State

Present: LOW.

The engine loads `knowledge/command_graph.json` during initialization and stores
it on the instance. It does not appear to write state.

### AI-Like Behavior

Present: NO direct AI behavior.

The file does not call providers, generate text with a model, use embeddings, or
perform autonomous actions. It formats local search results as a local answer.

### Runtime Mutation Risk

Risk: LOW.

The file reads local JSON and returns Python objects/strings. No file mutation
or runtime policy mutation was found.

## Conflict With AOIA Foundation

Conflict level: MEDIUM.

Reason: current AOIA Knowledge Pack work explicitly avoids retrieval, scoring,
ranking, and runtime integration. This file contains older local retrieval and
scoring behavior and can be confused with the new deterministic static pipeline.

## Recommendation

Do not modify the file in this cleanup phase.

Recommended next cleanup action:

- Add a label or README note marking `knowledge/rhcsa_engine.py` as legacy
  runtime memory.
- Keep the new static pipeline under `knowledge/raw`, `knowledge/parsed`,
  `knowledge/canonical`, `knowledge/index`, `knowledge/context`, and
  `knowledge/injection`.
- Do not import the new AOIA static injection artifacts into runtime until a
  later approved integration phase.
