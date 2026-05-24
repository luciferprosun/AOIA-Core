---
title: Wyszukiwanie i filtrowanie tekstu
topic: bash
source_section: Wyszukiwanie i filtrowanie tekstu
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [awk, bash, file, grep, linux, rhcsa, wyszukiwanie-i-filtrowanie-tekstu]
---

# Wyszukiwanie i filtrowanie tekstu

Imported RHCSA material for 30 commands. Primary command families: awk, file, grep.

## Tags

awk, bash, file, grep, linux, rhcsa, wyszukiwanie-i-filtrowanie-tekstu

## Examples

- `grep 'pattern' file`
- `grep -i 'pattern'`
- `file`
- `grep -r 'pattern'`
- `/dir`
- `grep -v 'pattern'`
- `grep -n 'pattern'`
- `grep -c 'pattern'`
- `grep -l 'pattern'`
- `grep -w 'word' file`

## Troubleshooting

- Quote patterns explicitly to avoid shell expansion when matching text.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Wyszukiwanie i filtrowanie tekstu`

## Commands

### `grep 'pattern' file`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `grep`
- Examples:
  - `grep 'pattern' file`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `grep -i 'pattern'`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `grep`
- Examples:
  - `grep -i 'pattern'`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `file`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `file`
- Examples:
  - `file`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `grep -r 'pattern'`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `grep`
- Examples:
  - `grep -r 'pattern'`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `/dir`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `dir`
- Examples:
  - `/dir`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `grep -v 'pattern'`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `grep`
- Examples:
  - `grep -v 'pattern'`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `grep -n 'pattern'`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `grep`
- Examples:
  - `grep -n 'pattern'`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `grep -c 'pattern'`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `grep`
- Examples:
  - `grep -c 'pattern'`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `grep -l 'pattern'`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `grep`
- Examples:
  - `grep -l 'pattern'`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `grep -w 'word' file`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `grep`
- Examples:
  - `grep -w 'word' file`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `grep -A 3 'pattern'`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `grep`
- Examples:
  - `grep -A 3 'pattern'`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `grep -B 3 'pattern'`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `grep`
- Examples:
  - `grep -B 3 'pattern'`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `grep -C 3 'pattern'`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `grep`
- Examples:
  - `grep -C 3 'pattern'`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `grep -E 'pat1|pat2'`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `grep`
- Examples:
  - `grep -E 'pat1|pat2'`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `grep -P '\d+' file`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `grep`
- Examples:
  - `grep -P '\d+' file`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `grep -o 'pattern'`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `grep`
- Examples:
  - `grep -o 'pattern'`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `grep -m 5 'pattern'`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `grep`
- Examples:
  - `grep -m 5 'pattern'`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `grep -q 'pattern'`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `grep`
- Examples:
  - `grep -q 'pattern'`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `grep -F 'literal'`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `grep`
- Examples:
  - `grep -F 'literal'`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `grep`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `grep`
- Examples:
  - `grep`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `awk '{print $1}'`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `awk`
- Examples:
  - `awk '{print $1}'`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `awk -F: '{print $1}'`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `awk`
- Examples:
  - `awk -F: '{print $1}'`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `awk 'NR==5' file`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `awk`
- Examples:
  - `awk 'NR==5' file`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `awk 'NR>=5 &&`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `awk`
- Examples:
  - `awk 'NR>=5 &&`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `awk '/pattern/' file`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `awk`
- Examples:
  - `awk '/pattern/' file`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `awk '{sum+=$1}`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `awk`
- Examples:
  - `awk '{sum+=$1}`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `awk '{print NF}'`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `awk`
- Examples:
  - `awk '{print NF}'`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `awk 'END{print NR}'`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `awk`
- Examples:
  - `awk 'END{print NR}'`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `awk '{print $NF}'`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `awk`
- Examples:
  - `awk '{print $NF}'`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`

### `awk -v FS=':'`

- Category: `Wyszukiwanie i filtrowanie tekstu`
- Risk: `unclassified`
- Tags: `bash`, `awk`
- Examples:
  - `awk -v FS=':'`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Wyszukiwanie i filtrowanie tekstu`
