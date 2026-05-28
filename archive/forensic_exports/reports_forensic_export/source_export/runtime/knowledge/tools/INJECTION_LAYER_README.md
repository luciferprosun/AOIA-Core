# RHCSA Context Injection Layer

`context_injector.py` builds static helper context from deterministic context
packs.

## Deterministic Injection Philosophy

The injector copies existing matched commands into stable helper strings:

```json
{
  "query": "network ports",
  "static_context": [
    "Use: podman network"
  ],
  "source": "RHCSA knowledge pack"
}
```

It does not rewrite commands, sort by relevance, infer missing meaning, or
generate new explanations.

## Static Helper Context

The output is a local JSON artifact. It is prepared for later review or future
integration, but this phase does not pass it to a model or modify prompts.

## Injection vs AI Reasoning

Injection is deterministic copying of known local context. AI reasoning would
interpret, summarize, expand, or decide how to use that context. That behavior
is outside this phase.

## Why AOIA Remains Stateless

The injector reads static input files and writes one static output file. It does
not store request history, learn from usage, mutate configuration, or change
router/runtime behavior.

## Usage

```text
python3 knowledge/tools/context_injector.py
```
