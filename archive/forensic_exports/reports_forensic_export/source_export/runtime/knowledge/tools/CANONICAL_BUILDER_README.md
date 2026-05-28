# RHCSA Canonical Builder

`canonical_builder.py` converts parsed RHCSA section data into static canonical
command entries.

## Canonical Entry Philosophy

The builder creates a stable JSON artifact from already parsed section data. It
normalizes whitespace, preserves source order, and removes exact duplicate
commands only.

Each entry uses this structure:

```json
{
  "command": "",
  "category": "",
  "risk": "",
  "description": "",
  "examples": [],
  "source_section": ""
}
```

`category` is copied from the source section. `risk` is set to `unclassified`
because this phase does not perform semantic risk classification.

## Deterministic-Only Processing

- stable source-order iteration
- exact duplicate removal only
- no command rewriting
- no generated tags
- no adaptive metadata
- stdout warnings for malformed entries

## What It Does Not Do

- does not infer semantic meaning
- does not classify intent
- does not generate embeddings
- does not implement retrieval
- does not rank entries
- does not use AI enrichment
- does not mutate router or runtime code

## Usage

Default input:

```text
python3 knowledge/tools/canonical_builder.py
```

Explicit input:

```text
python3 knowledge/tools/canonical_builder.py knowledge/parsed/rhcsa_sections.json
```
