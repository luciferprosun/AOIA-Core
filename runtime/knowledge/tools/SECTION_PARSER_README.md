# RHCSA Section Parser

`section_parser.py` converts `knowledge/raw/rhcsa_raw.txt` into deterministic
section-level JSON.

## What It Does

- reads local raw text extracted from the RHCSA PDF
- detects section titles in source order
- extracts command-like table cells without semantic classification
- writes UTF-8 JSON to `knowledge/parsed/rhcsa_sections.json`
- validates that section names are not empty
- prints a stdout report with section count, command count, skipped malformed
  blocks, and output path

## What It Does Not Do

- does not classify command intent
- does not generate canonical knowledge entries
- does not implement retrieval
- does not rank commands
- does not use AI
- does not create embeddings
- does not use vector databases
- does not modify router or runtime code

## Deterministic-Only Philosophy

The parser is a local structural extraction tool. It preserves source order,
uses stable regex rules, writes deterministic JSON, and performs no hidden
background processing.

## Usage

Default input:

```text
python3 knowledge/tools/section_parser.py
```

Explicit input:

```text
python3 knowledge/tools/section_parser.py knowledge/raw/rhcsa_raw.txt
```
