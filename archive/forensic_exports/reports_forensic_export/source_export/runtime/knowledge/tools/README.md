# RHCSA PDF Extraction Tool

`pdf_extract.py` performs deterministic raw text extraction from the RHCSA
command library PDF.

## What It Does

- reads one local PDF file
- extracts raw text with the local `pdftotext` command
- writes UTF-8 text to `knowledge/raw/rhcsa_raw.txt`
- verifies that the output file exists
- verifies that the output file is non-empty
- prints a clear stdout report with page count, output size, and output path

## What It Does Not Do

- does not parse commands
- does not classify commands
- does not implement retrieval
- does not use AI
- does not create embeddings
- does not use vector databases
- does not rank results
- does not modify router or runtime code

## Deterministic-Only Philosophy

The extractor is a local preprocessing tool. It has no hidden background work,
no async behavior, no multiprocessing, and no runtime mutation. The same input
PDF and local extractor version should produce the same raw text output.

## Usage

Default expected input:

```text
python3 knowledge/tools/pdf_extract.py
```

Explicit input:

```text
python3 knowledge/tools/pdf_extract.py "knowledge/source/RHCSA_Command_Library (1).pdf"
```
