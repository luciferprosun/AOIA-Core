# RHCSA Index Builder

`index_builder.py` creates a static keyword lookup index from canonical RHCSA
command entries.

## Deterministic Lookup Philosophy

The builder uses only existing `category` and `command` fields. Keywords are
created by deterministic token splitting. Output keys are sorted
alphabetically, and each command list is sorted alphabetically.

The output format is:

```json
{
  "keyword": [
    "command"
  ]
}
```

## Lookup vs Semantic Search

Lookup is exact token matching against a static JSON index. Semantic search
would require inferred meaning, embeddings, ranking, or model-based expansion.
Those behaviors are outside this phase.

## What It Does Not Do

- does not infer meaning
- does not rewrite commands
- does not rank commands
- does not create embeddings
- does not use vector databases
- does not implement AI retrieval
- does not modify router or runtime code

## Usage

Default input:

```text
python3 knowledge/tools/index_builder.py
```

Explicit input:

```text
python3 knowledge/tools/index_builder.py knowledge/canonical/rhcsa_commands.json
```
