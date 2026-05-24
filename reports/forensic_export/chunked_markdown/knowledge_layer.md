# Knowledge Layer

Canonical knowledge records, indexes, source extraction artifacts, candidate pipeline, and knowledge reports.

Commit: `04adfbdb5a6b34d2969d67ac7e84c704c8e0915a`

Files in this chunk: 85

## `runtime/knowledge/README.md`

- size: 974 bytes
- sha256: `5b8c73e1184b61b7b2ee474ce4f2fd1c9c41e8cf84e2b5c482a4362f5aa111e8`
- category: knowledge

```markdown
# RHCSA Local Knowledge Base

This directory contains the structured local RHCSA knowledge base built from the
existing canonical command import. The original deterministic JSON pipeline remains
in place; these markdown modules add topic-oriented operator-readable knowledge.

## Topic Layout

- `filesystem/`: 187 commands
- `networking/`: 121 commands
- `users/`: 49 commands
- `permissions/`: 31 commands
- `selinux/`: 36 commands
- `systemd/`: 174 commands
- `storage/`: 29 commands
- `lvm/`: 15 commands
- `podman/`: 109 commands
- `bash/`: 101 commands
- `troubleshooting/`: 88 commands

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Parsed sections: `knowledge/parsed/rhcsa_sections.json`

## Notes

- Existing deterministic JSON artifacts are preserved.
- Markdown modules are generated from the canonical command import.
- Topic mapping is heuristic but deterministic.
```

## `runtime/knowledge/__init__.py`

- size: 69 bytes
- sha256: `2c92085a9550a1b477621635943e49c8009db4b7dd238dd606e7c667c9f4b649`
- category: knowledge

```python
"""Local operational knowledge layer for the AI terminal runtime."""
```

## `runtime/knowledge/bash/README.md`

- size: 646 bytes
- sha256: `0ede11b4fdc0359f45642cfee4539d007637090815fafcd97470ce86c2ef0a17`
- category: knowledge

```markdown
# Bash

Shell variables, scripting, text processing, and CLI composition patterns.

## Modules

- `bash/skrypty-bash-podstawy.md`: 25 imported commands from `Skrypty bash — podstawy`
- `bash/wyszukiwanie-i-filtrowanie-tekstu.md`: 30 imported commands from `Wyszukiwanie i filtrowanie tekstu`
- `bash/zaawansowane-narzdzia-tekstowe.md`: 11 imported commands from `Zaawansowane narz■dzia tekstowe`
- `bash/zmienne-rodowiskowe-i-powoka.md`: 35 imported commands from `Zmienne ■rodowiskowe i pow■oka`

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
```

## `runtime/knowledge/bash/skrypty-bash-podstawy.md`

- size: 8809 bytes
- sha256: `bf38c89257112f90f7305bd52aa576bcde2f82b72306da2a2195d640ce4e83e9`
- category: knowledge

```markdown
---
title: Skrypty bash — podstawy
topic: bash
source_section: Skrypty bash — podstawy
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [bash, break, chmod, continue, do, done, echo, else, esac, fi, linux, mktemp, rhcsa, skrypty-bash-podstawy, then]
---

# Skrypty bash — podstawy

Imported RHCSA material for 25 commands. Primary command families: break, chmod, continue, do, done, echo, else, esac.

## Tags

bash, break, chmod, continue, do, done, echo, else, esac, fi, linux, mktemp, rhcsa, skrypty-bash-podstawy, then

## Examples

- `esac`
- `chmod +x script.sh`
- `./script.sh`
- `}`
- `VAR='value'`
- `VAR=$(command)`
- `$@`
- `$#`
- `echo "Value: $VAR"`
- `$0`

## Troubleshooting

- Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Skrypty bash — podstawy`

## Commands

### `esac`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `esac`
- Examples:
  - `esac`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `chmod +x script.sh`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `chmod`
- Examples:
  - `chmod +x script.sh`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `./script.sh`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `script-sh`
- Examples:
  - `./script.sh`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `}`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `module`
- Examples:
  - `}`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `VAR='value'`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `var-value`
- Examples:
  - `VAR='value'`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `VAR=$(command)`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `var-command`
- Examples:
  - `VAR=$(command)`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `$@`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `module`
- Examples:
  - `$@`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `$#`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `module`
- Examples:
  - `$#`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `echo "Value: $VAR"`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo "Value: $VAR"`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `$0`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `0`
- Examples:
  - `$0`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `$$`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `module`
- Examples:
  - `$$`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `$?`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `module`
- Examples:
  - `$?`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `then`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `then`
- Examples:
  - `then`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `else`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `else`
- Examples:
  - `else`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `2>/dev/null`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `2-dev-null`
- Examples:
  - `2>/dev/null`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `fi`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `fi`
- Examples:
  - `fi`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `1>/dev/null`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `1-dev-null`
- Examples:
  - `1>/dev/null`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `ARRAY+=('e')`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `array-e`
- Examples:
  - `ARRAY+=('e')`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `done`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `done`
- Examples:
  - `done`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `do`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `do`
- Examples:
  - `do`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `echo ${MAP[k1]}`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo ${MAP[k1]}`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `mktemp`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `mktemp`
- Examples:
  - `mktemp`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `break`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `break`
- Examples:
  - `break`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `continue`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `continue`
- Examples:
  - `continue`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`

### `TMPFILE=$(mktemp)`

- Category: `Skrypty bash — podstawy`
- Risk: `unclassified`
- Tags: `bash`, `tmpfile-mktemp`
- Examples:
  - `TMPFILE=$(mktemp)`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Skrypty bash — podstawy`
```

## `runtime/knowledge/bash/wyszukiwanie-i-filtrowanie-tekstu.md`

- size: 10709 bytes
- sha256: `9576ba68147d6541d1eb97b947142c584dbe0c43c895f8a40883f4f5b60ad789`
- category: knowledge

```markdown
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
```

## `runtime/knowledge/bash/zaawansowane-narzdzia-tekstowe.md`

- size: 4675 bytes
- sha256: `1d52cff9b59f7ae03ba50c11e67dc77fa955a2a5ccd383225d79782bbd4f51a0`
- category: knowledge

```markdown
---
title: Zaawansowane narz■dzia tekstowe
topic: bash
source_section: Zaawansowane narz■dzia tekstowe
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [bash, cat, date, echo, gpg, hwclock, linux, rhcsa, zaawansowane-narzdzia-tekstowe]
---

# Zaawansowane narz■dzia tekstowe

Imported RHCSA material for 11 commands. Primary command families: cat, date, echo, gpg, hwclock.

## Tags

bash, cat, date, echo, gpg, hwclock, linux, rhcsa, zaawansowane-narzdzia-tekstowe

## Examples

- `echo {1..5}`
- `echo file{1..3}.txt`
- `echo {a,b,c}.log`
- `echo $((RANDOM %`
- `100))`
- `32`
- `echo '3.14 * 2' | bc`
- `date`
- `gpg`
- `hwclock`

## Troubleshooting

- Validate command intent against current host state before applying changes in production.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Zaawansowane narz■dzia tekstowe`

## Commands

### `echo {1..5}`

- Category: `Zaawansowane narz■dzia tekstowe`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo {1..5}`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zaawansowane narz■dzia tekstowe`

### `echo file{1..3}.txt`

- Category: `Zaawansowane narz■dzia tekstowe`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo file{1..3}.txt`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zaawansowane narz■dzia tekstowe`

### `echo {a,b,c}.log`

- Category: `Zaawansowane narz■dzia tekstowe`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo {a,b,c}.log`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zaawansowane narz■dzia tekstowe`

### `echo $((RANDOM %`

- Category: `Zaawansowane narz■dzia tekstowe`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo $((RANDOM %`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zaawansowane narz■dzia tekstowe`

### `100))`

- Category: `Zaawansowane narz■dzia tekstowe`
- Risk: `unclassified`
- Tags: `bash`, `100`
- Examples:
  - `100))`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zaawansowane narz■dzia tekstowe`

### `32`

- Category: `Zaawansowane narz■dzia tekstowe`
- Risk: `unclassified`
- Tags: `bash`, `32`
- Examples:
  - `32`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zaawansowane narz■dzia tekstowe`

### `echo '3.14 * 2' | bc`

- Category: `Zaawansowane narz■dzia tekstowe`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo '3.14 * 2' | bc`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zaawansowane narz■dzia tekstowe`

### `date`

- Category: `Zaawansowane narz■dzia tekstowe`
- Risk: `unclassified`
- Tags: `bash`, `date`
- Examples:
  - `date`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zaawansowane narz■dzia tekstowe`

### `gpg`

- Category: `Zaawansowane narz■dzia tekstowe`
- Risk: `unclassified`
- Tags: `bash`, `gpg`
- Examples:
  - `gpg`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zaawansowane narz■dzia tekstowe`

### `hwclock`

- Category: `Zaawansowane narz■dzia tekstowe`
- Risk: `unclassified`
- Tags: `bash`, `hwclock`
- Examples:
  - `hwclock`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zaawansowane narz■dzia tekstowe`

### `cat /etc/chrony.conf`

- Category: `Zaawansowane narz■dzia tekstowe`
- Risk: `unclassified`
- Tags: `bash`, `cat`
- Examples:
  - `cat /etc/chrony.conf`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zaawansowane narz■dzia tekstowe`
```

## `runtime/knowledge/bash/zmienne-rodowiskowe-i-powoka.md`

- size: 12829 bytes
- sha256: `9cf79632f711d2cc0a8cc6a8ba2cf86b724d4fbfae8bd9ee812994cfc19102cc`
- category: knowledge

```markdown
---
title: Zmienne ■rodowiskowe i pow■oka
topic: bash
source_section: Zmienne ■rodowiskowe i pow■oka
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [alias, bash, cat, complete, ctrl+r, echo, env, false, hash, history, linux, ls, printenv, rhcsa, set, source, true, zmienne-rodowiskowe-i-powoka]
---

# Zmienne ■rodowiskowe i pow■oka

Imported RHCSA material for 35 commands. Primary command families: alias, cat, complete, ctrl+r, echo, env, false, hash.

## Tags

alias, bash, cat, complete, ctrl+r, echo, env, false, hash, history, linux, ls, printenv, rhcsa, set, source, true, zmienne-rodowiskowe-i-powoka

## Examples

- `env`
- `printenv`
- `echo $VARIABLE`
- `Ctrl+R`
- `echo $HISTSIZE`
- `echo $HISTFILE`
- `set`
- `echo $HISTFILESIZE`
- `echo $SHELL`
- `echo $BASH_VERSION`

## Troubleshooting

- Validate command intent against current host state before applying changes in production.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Zmienne ■rodowiskowe i pow■oka`

## Commands

### `env`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `env`
- Examples:
  - `env`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `printenv`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `printenv`
- Examples:
  - `printenv`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `echo $VARIABLE`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo $VARIABLE`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `Ctrl+R`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `ctrl+r`
- Examples:
  - `Ctrl+R`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `echo $HISTSIZE`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo $HISTSIZE`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `echo $HISTFILE`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo $HISTFILE`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `set`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `set`
- Examples:
  - `set`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `echo $HISTFILESIZE`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo $HISTFILESIZE`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `echo $SHELL`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo $SHELL`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `echo $BASH_VERSION`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo $BASH_VERSION`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `echo $PS1`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo $PS1`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `alias ll='ls -alh'`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `alias`
- Examples:
  - `alias ll='ls -alh'`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `alias`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `alias`
- Examples:
  - `alias`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `hash`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `hash`
- Examples:
  - `hash`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `echo ${ARRAY[0]}`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo ${ARRAY[0]}`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `complete`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `complete`
- Examples:
  - `complete`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `echo ${ARRAY[@]}`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo ${ARRAY[@]}`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `echo ${#ARRAY[@]}`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo ${#ARRAY[@]}`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `source`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `source`
- Examples:
  - `source`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `cat ~/.bashrc`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `cat`
- Examples:
  - `cat ~/.bashrc`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `cat ~/.bash_profile`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `cat`
- Examples:
  - `cat ~/.bash_profile`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `true`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `true`
- Examples:
  - `true`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `cat ~/.bash_logout`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `cat`
- Examples:
  - `cat ~/.bash_logout`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `false`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `false`
- Examples:
  - `false`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `cat /etc/profile`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `cat`
- Examples:
  - `cat /etc/profile`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `cat /etc/bashrc`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `cat`
- Examples:
  - `cat /etc/bashrc`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `echo $$`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo $$`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `ls /etc/profile.d/`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `ls`
- Examples:
  - `ls /etc/profile.d/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `echo $?`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo $?`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `echo $!`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo $!`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `history`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `history`
- Examples:
  - `history`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `echo $0`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo $0`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `echo $#`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo $#`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `echo $@`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo $@`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`

### `echo $*`

- Category: `Zmienne ■rodowiskowe i pow■oka`
- Risk: `unclassified`
- Tags: `bash`, `echo`
- Examples:
  - `echo $*`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zmienne ■rodowiskowe i pow■oka`
```

## `runtime/knowledge/candidates/candidate_command_index.json`

- size: 2037636 bytes
- sha256: `68d42c89c39db570c994de835b6ae7d1e3ec2a5a7c2d257755e27d19c110d325`
- category: knowledge

Content omitted from inline markdown because this generated artifact is 2037636 bytes.
Full file is preserved at `source_export/runtime/knowledge/candidates/candidate_command_index.json`.

## `runtime/knowledge/candidates/candidate_commands.csv`

- size: 750184 bytes
- sha256: `f31f89e1e6284a67b594b0cfd08bdc525081f00e98bceba9a999eaddf7cf781d`
- category: knowledge

Content omitted from inline markdown because this generated artifact is 750184 bytes.
Full file is preserved at `source_export/runtime/knowledge/candidates/candidate_commands.csv`.

## `runtime/knowledge/canonical/rhcsa_commands.json`

- size: 220301 bytes
- sha256: `637a4ae1d03ba9b04e41cf1a566be97d88994bf9f3cfe0c5520b2e41bac73c85`
- category: knowledge

Content omitted from inline markdown because this generated artifact is 220301 bytes.
Full file is preserved at `source_export/runtime/knowledge/canonical/rhcsa_commands.json`.

## `runtime/knowledge/command_graph.json`

- size: 2027 bytes
- sha256: `ee66ed8e6af4795feb86dde840fe4fdd36a4bfea66e95a44be3fca850592f842`
- category: knowledge

```json
{
  "version": 1,
  "nodes": {
    "nginx": {
      "kind": "service",
      "commands": [
        "dnf install nginx",
        "systemctl enable --now nginx",
        "systemctl status nginx",
        "journalctl -u nginx -b",
        "firewall-cmd --add-service=http --permanent",
        "firewall-cmd --reload"
      ],
      "related": ["dnf", "systemctl", "journalctl", "firewall-cmd", "selinux"]
    },
    "httpd": {
      "kind": "service",
      "commands": [
        "dnf install httpd",
        "systemctl enable --now httpd",
        "systemctl status httpd",
        "journalctl -u httpd -b",
        "firewall-cmd --add-service=http --permanent",
        "restorecon -Rv /var/www/html"
      ],
      "related": ["dnf", "systemctl", "journalctl", "firewall-cmd", "selinux"]
    },
    "ssh": {
      "kind": "service",
      "commands": [
        "systemctl status sshd",
        "journalctl -u sshd -b",
        "ss -tulpn | grep :22",
        "ssh -vvv user@host"
      ],
      "related": ["systemctl", "journalctl", "ss", "firewall-cmd", "permissions"]
    },
    "lvm": {
      "kind": "storage",
      "commands": [
        "lsblk",
        "pvcreate /dev/DEVICE",
        "vgcreate VG /dev/DEVICE",
        "lvcreate -n LV -L SIZE VG",
        "mkfs.xfs /dev/VG/LV",
        "mount -a"
      ],
      "related": ["storage", "mount", "fstab", "xfs", "ext4"]
    },
    "selinux": {
      "kind": "security",
      "commands": [
        "getenforce",
        "sestatus",
        "ls -Z PATH",
        "restorecon -Rv PATH",
        "semanage fcontext -a -t TYPE 'PATH_REGEX'"
      ],
      "related": ["permissions", "audit", "services", "web"]
    },
    "firewall-cmd": {
      "kind": "network_security",
      "commands": [
        "firewall-cmd --state",
        "firewall-cmd --get-active-zones",
        "firewall-cmd --list-all",
        "firewall-cmd --add-service=SERVICE --permanent",
        "firewall-cmd --reload"
      ],
      "related": ["networking", "ssh", "httpd", "nginx"]
    }
  }
}
```

## `runtime/knowledge/context/context_pack.json`

- size: 692 bytes
- sha256: `fc6464e3cc23407afec3dd8256798c3672058276a6144ef2ccbbcb8b7b0107cf`
- category: knowledge

```json
[
  {
    "query": "network ports",
    "matched_keywords": [
      "network"
    ],
    "matched_commands": [
      {
        "command": "podman network",
        "description": "",
        "examples": [
          "podman network"
        ],
        "source_section": "Kontenery Podman"
      },
      {
        "command": "podman network ls",
        "description": "",
        "examples": [
          "podman network ls"
        ],
        "source_section": "Kontenery Podman"
      },
      {
        "command": "podman network rm",
        "description": "",
        "examples": [
          "podman network rm"
        ],
        "source_section": "Kontenery Podman"
      }
    ]
  }
]
```

## `runtime/knowledge/examples/ls-command.json`

- size: 525 bytes
- sha256: `42d4bc928ee4ef2c15a961c8d17885ea917bbd64be0ce498e30865e215d1a176`
- category: knowledge

```json
{
  "id": "ls-command",
  "command": "ls",
  "description": "Lists directory contents.",
  "category": "filesystem",
  "tags": [
    "directory-listing",
    "read-only"
  ],
  "risk": "low",
  "os": [
    "linux",
    "macos"
  ],
  "shell": [
    "bash",
    "sh",
    "zsh"
  ],
  "examples": [
    {
      "input": "ls -la",
      "expected_effect": "Prints detailed directory contents including hidden entries."
    }
  ],
  "notes": "Read-only inspection command.",
  "related_commands": [
    "find",
    "stat"
  ]
}
```

## `runtime/knowledge/examples/rm-recursive-force.json`

- size: 632 bytes
- sha256: `ff6400c227c917e4fdcb7cf211c175861563dff1536e35bad6bee66be7bd25d0`
- category: knowledge

```json
{
  "id": "rm-recursive-force",
  "command": "rm -rf",
  "description": "Removes files or directories recursively without prompting.",
  "category": "filesystem",
  "tags": [
    "destructive",
    "recursive-delete"
  ],
  "risk": "critical",
  "os": [
    "linux",
    "macos"
  ],
  "shell": [
    "bash",
    "sh",
    "zsh"
  ],
  "examples": [
    {
      "input": "rm -rf build/",
      "expected_effect": "Deletes the build directory and its contents if the path exists."
    }
  ],
  "notes": "Critical risk because incorrect paths can cause irreversible data loss.",
  "related_commands": [
    "rmdir",
    "trash"
  ]
}
```

## `runtime/knowledge/examples/systemctl-status.json`

- size: 670 bytes
- sha256: `dd0ed5761bd48c9a90cba7600bb807f8d0c25762a1610d4caa63285e05da41c4`
- category: knowledge

```json
{
  "id": "systemctl-status",
  "command": "systemctl status",
  "description": "Shows service manager status for a unit.",
  "category": "service",
  "tags": [
    "read-only",
    "service-status"
  ],
  "risk": "low",
  "os": [
    "linux",
    "rhel",
    "ubuntu"
  ],
  "shell": [
    "bash",
    "sh",
    "zsh"
  ],
  "examples": [
    {
      "input": "systemctl status sshd",
      "expected_effect": "Prints the current status and recent logs for the sshd service."
    }
  ],
  "notes": "Status inspection is low risk. Start, stop, restart, and enable operations require higher risk entries.",
  "related_commands": [
    "journalctl",
    "systemctl"
  ]
}
```

## `runtime/knowledge/extracted/linux_master_library_v1.md`

- size: 797025 bytes
- sha256: `4e18a23a0c33340f536b1b34910e950f66070c3bfe4fc73dd9ad71e18b774927`
- category: knowledge

Content omitted from inline markdown because this generated artifact is 797025 bytes.
Full file is preserved at `source_export/runtime/knowledge/extracted/linux_master_library_v1.md`.

## `runtime/knowledge/extracted/linux_master_library_v1.txt`

- size: 797025 bytes
- sha256: `4e18a23a0c33340f536b1b34910e950f66070c3bfe4fc73dd9ad71e18b774927`
- category: knowledge

Content omitted from inline markdown because this generated artifact is 797025 bytes.
Full file is preserved at `source_export/runtime/knowledge/extracted/linux_master_library_v1.txt`.

## `runtime/knowledge/filesystem/README.md`

- size: 835 bytes
- sha256: `b1a3251dfdc7d1d80808a1bd92625bf9405b4e75bb428808ccad82e9e91d2958`
- category: knowledge

```markdown
# Filesystem

File navigation, file operations, search, archives, and editor-oriented workflows.

## Modules

- `filesystem/archiwizacja-i-kompresja.md`: 23 imported commands from `Archiwizacja i kompresja`
- `filesystem/edytor-vim.md`: 60 imported commands from `Edytor Vim`
- `filesystem/nawigacja-po-systemie-plikow.md`: 26 imported commands from `Nawigacja po systemie plików`
- `filesystem/operacje-na-plikach-i-katalogach.md`: 27 imported commands from `Operacje na plikach i katalogach`
- `filesystem/przegldanie-zawartoci-plikow.md`: 4 imported commands from `Przegl■danie zawarto■ci plików`
- `filesystem/wyszukiwanie-plikow.md`: 47 imported commands from `Wyszukiwanie plików`

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
```

## `runtime/knowledge/filesystem/archiwizacja-i-kompresja.md`

- size: 8646 bytes
- sha256: `a1790486b17e69965fe65b0933634e69a0002b6fedac27fb65363e31031a5380`
- category: knowledge

```markdown
---
title: Archiwizacja i kompresja
topic: filesystem
source_section: Archiwizacja i kompresja
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [archive.tar.bz2, archive.tar.gz, archive.tar.xz, archiwizacja-i-kompresja, filesystem, find, linux, newfile, rhcsa, tar]
---

# Archiwizacja i kompresja

Imported RHCSA material for 23 commands. Primary command families: archive.tar.bz2, archive.tar.gz, archive.tar.xz, find, newfile, tar.

## Tags

archive.tar.bz2, archive.tar.gz, archive.tar.xz, archiwizacja-i-kompresja, filesystem, find, linux, newfile, rhcsa, tar

## Examples

- `tar -cvf archive.tar`
- `tar -cvzf`
- `tar -cvjf`
- `tar -cvJf`
- `tar -xvf archive.tar`
- `tar -xvzf`
- `archive.tar.gz`
- `tar -xvjf`
- `archive.tar.bz2`
- `tar -xvJf`

## Troubleshooting

- Validate command intent against current host state before applying changes in production.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Archiwizacja i kompresja`

## Commands

### `tar -cvf archive.tar`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `tar`
- Examples:
  - `tar -cvf archive.tar`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `tar -cvzf`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `tar`
- Examples:
  - `tar -cvzf`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `tar -cvjf`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `tar`
- Examples:
  - `tar -cvjf`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `tar -cvJf`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `tar`
- Examples:
  - `tar -cvJf`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `tar -xvf archive.tar`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `tar`
- Examples:
  - `tar -xvf archive.tar`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `tar -xvzf`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `tar`
- Examples:
  - `tar -xvzf`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `archive.tar.gz`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `archive.tar.gz`
- Examples:
  - `archive.tar.gz`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `tar -xvjf`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `tar`
- Examples:
  - `tar -xvjf`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `archive.tar.bz2`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `archive.tar.bz2`
- Examples:
  - `archive.tar.bz2`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `tar -xvJf`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `tar`
- Examples:
  - `tar -xvJf`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `archive.tar.xz`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `archive.tar.xz`
- Examples:
  - `archive.tar.xz`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `tar -tvf archive.tar`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `tar`
- Examples:
  - `tar -tvf archive.tar`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `tar -tvzf`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `tar`
- Examples:
  - `tar -tvzf`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `tar -rvf archive.tar`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `tar`
- Examples:
  - `tar -rvf archive.tar`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `newfile`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `newfile`
- Examples:
  - `newfile`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `tar -uvf archive.tar`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `tar`
- Examples:
  - `tar -uvf archive.tar`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `tar --delete -f`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `tar`
- Examples:
  - `tar --delete -f`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `tar`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `tar`
- Examples:
  - `tar`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `tar --exclude-vcs`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `tar`
- Examples:
  - `tar --exclude-vcs`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `tar -czf - /path |`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `tar`
- Examples:
  - `tar -czf - /path |`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `tar -czf arch.tar.gz`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `tar`
- Examples:
  - `tar -czf arch.tar.gz`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `--newer-mtime='2023-`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `newer-mtime-2023`
- Examples:
  - `--newer-mtime='2023-`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`

### `find /path -print |`

- Category: `Archiwizacja i kompresja`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find /path -print |`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Archiwizacja i kompresja`
```

## `runtime/knowledge/filesystem/edytor-vim.md`

- size: 17661 bytes
- sha256: `b63bad518761f1a624ab831eb5877d0ceca6169fe5282b5653a56de7dea7b7af`
- category: knowledge

```markdown
---
title: Edytor Vim
topic: filesystem
source_section: Edytor Vim
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [a, b, cat, cc, ctrl+b, ctrl+d, ctrl+f, ctrl+r, ctrl+u, ctrl+v, cw, d, d0, dd, dw, e, edytor-vim, esc, filesystem, g, gg, gt, gu, i, linux, n, o, p, q, qa, r, rhcsa, u, v, vim, x, yy, zq, zz]
---

# Edytor Vim

Imported RHCSA material for 60 commands. Primary command families: a, b, cat, cc, ctrl+b, ctrl+d, ctrl+f, ctrl+r.

## Tags

a, b, cat, cc, ctrl+b, ctrl+d, ctrl+f, ctrl+r, ctrl+u, ctrl+v, cw, d, d0, dd, dw, e, edytor-vim, esc, filesystem, g, gg, gt, gu, i, linux, n, o, p, q, qa, r, rhcsa, u, v, vim, x, yy, zq, zz

## Examples

- `vim file.txt`
- `c$`
- `vim +10 file.txt`
- `cw`
- `vim +/pattern`
- `cc`
- `vim -R file.txt`
- `dw`
- `d$`
- `vim -d file1 file2`

## Troubleshooting

- Validate command intent against current host state before applying changes in production.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Edytor Vim`

## Commands

### `vim file.txt`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `vim`
- Examples:
  - `vim file.txt`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `c$`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `c`
- Examples:
  - `c$`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `vim +10 file.txt`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `vim`
- Examples:
  - `vim +10 file.txt`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `cw`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `cw`
- Examples:
  - `cw`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `vim +/pattern`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `vim`
- Examples:
  - `vim +/pattern`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `cc`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `cc`
- Examples:
  - `cc`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `vim -R file.txt`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `vim`
- Examples:
  - `vim -R file.txt`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `dw`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `dw`
- Examples:
  - `dw`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `d$`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `d`
- Examples:
  - `d$`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `vim -d file1 file2`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `vim`
- Examples:
  - `vim -d file1 file2`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `d0`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `d0`
- Examples:
  - `d0`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `D`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `d`
- Examples:
  - `D`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `vim -u NONE file.txt`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `vim`
- Examples:
  - `vim -u NONE file.txt`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `/pattern`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `pattern`
- Examples:
  - `/pattern`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `?pattern`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `pattern`
- Examples:
  - `?pattern`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `n`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `n`
- Examples:
  - `n`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `N`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `n`
- Examples:
  - `N`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `*`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `module`
- Examples:
  - `*`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `i`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `i`
- Examples:
  - `i`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `I`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `i`
- Examples:
  - `I`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `a`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `a`
- Examples:
  - `a`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `A`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `a`
- Examples:
  - `A`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `o`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `o`
- Examples:
  - `o`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `O`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `o`
- Examples:
  - `O`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `Esc`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `esc`
- Examples:
  - `Esc`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `ZZ`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `zz`
- Examples:
  - `ZZ`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `ZQ`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `zq`
- Examples:
  - `ZQ`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `v`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `v`
- Examples:
  - `v`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `V`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `v`
- Examples:
  - `V`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `Ctrl+v`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `ctrl+v`
- Examples:
  - `Ctrl+v`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `b`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `b`
- Examples:
  - `b`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `gU`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `gu`
- Examples:
  - `gU`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `e`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `e`
- Examples:
  - `e`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `gu`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `gu`
- Examples:
  - `gu`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `0`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `0`
- Examples:
  - `0`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `$`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `module`
- Examples:
  - `$`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `gg`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `gg`
- Examples:
  - `gg`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `G`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `g`
- Examples:
  - `G`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `10G`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `10g`
- Examples:
  - `10G`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `Ctrl+f`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `ctrl+f`
- Examples:
  - `Ctrl+f`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `Ctrl+b`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `ctrl+b`
- Examples:
  - `Ctrl+b`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `Ctrl+d`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `ctrl+d`
- Examples:
  - `Ctrl+d`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `gt`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `gt`
- Examples:
  - `gt`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `Ctrl+u`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `ctrl+u`
- Examples:
  - `Ctrl+u`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `gT`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `gt`
- Examples:
  - `gT`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `dd`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `dd`
- Examples:
  - `dd`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `5dd`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `5dd`
- Examples:
  - `5dd`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `yy`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `yy`
- Examples:
  - `yy`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `qa`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `qa`
- Examples:
  - `qa`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `5yy`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `5yy`
- Examples:
  - `5yy`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `q`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `q`
- Examples:
  - `q`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `p`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `p`
- Examples:
  - `p`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `P`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `p`
- Examples:
  - `P`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `u`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `u`
- Examples:
  - `u`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `Ctrl+r`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `ctrl+r`
- Examples:
  - `Ctrl+r`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `x`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `x`
- Examples:
  - `x`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `X`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `x`
- Examples:
  - `X`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `r`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `r`
- Examples:
  - `r`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `cat ~/.vimrc`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `cat`
- Examples:
  - `cat ~/.vimrc`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`

### `R`

- Category: `Edytor Vim`
- Risk: `unclassified`
- Tags: `filesystem`, `r`
- Examples:
  - `R`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Edytor Vim`
```

## `runtime/knowledge/filesystem/nawigacja-po-systemie-plikow.md`

- size: 9395 bytes
- sha256: `bb5e3365bd9e1565634f053e56fc9f561829809fbd72419a9e0f2712b86ea554`
- category: knowledge

```markdown
---
title: Nawigacja po systemie plików
topic: filesystem
source_section: Nawigacja po systemie plików
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [basename, cd, dirname, dirs, echo, filesystem, linux, ls, nawigacja-po-systemie-plikow, popd, pwd, rhcsa, tree]
---

# Nawigacja po systemie plików

Imported RHCSA material for 26 commands. Primary command families: basename, cd, dirname, dirs, echo, ls, popd, pwd.

## Tags

basename, cd, dirname, dirs, echo, filesystem, linux, ls, nawigacja-po-systemie-plikow, popd, pwd, rhcsa, tree

## Examples

- `pwd`
- `tree`
- `ls`
- `ls -l`
- `ls -la`
- `ls -lh`
- `ls -lt`
- `ls -lS`
- `ls -R`
- `ls -d */`

## Troubleshooting

- Validate command intent against current host state before applying changes in production.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Nawigacja po systemie plików`

## Commands

### `pwd`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `pwd`
- Examples:
  - `pwd`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `tree`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `tree`
- Examples:
  - `tree`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `ls`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `ls`
- Examples:
  - `ls`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `ls -l`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `ls`
- Examples:
  - `ls -l`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `ls -la`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `ls`
- Examples:
  - `ls -la`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `ls -lh`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `ls`
- Examples:
  - `ls -lh`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `ls -lt`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `ls`
- Examples:
  - `ls -lt`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `ls -lS`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `ls`
- Examples:
  - `ls -lS`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `ls -R`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `ls`
- Examples:
  - `ls -R`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `ls -d */`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `ls`
- Examples:
  - `ls -d */`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `basename`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `basename`
- Examples:
  - `basename`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `ls -i`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `ls`
- Examples:
  - `ls -i`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `dirname`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `dirname`
- Examples:
  - `dirname`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `ls --color=auto`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `ls`
- Examples:
  - `ls --color=auto`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `cd /path/to/dir`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `cd`
- Examples:
  - `cd /path/to/dir`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `cd ~`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `cd`
- Examples:
  - `cd ~`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `cd -`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `cd`
- Examples:
  - `cd -`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `echo $PATH`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `echo`
- Examples:
  - `echo $PATH`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `echo $HOME`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `echo`
- Examples:
  - `echo $HOME`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `echo $PWD`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `echo`
- Examples:
  - `echo $PWD`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `cd /`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `cd`
- Examples:
  - `cd /`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `echo $OLDPWD`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `echo`
- Examples:
  - `echo $OLDPWD`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `ls /etc | head -20`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `ls`
- Examples:
  - `ls /etc | head -20`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `popd`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `popd`
- Examples:
  - `popd`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `ls /proc | wc -l`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `ls`
- Examples:
  - `ls /proc | wc -l`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`

### `dirs`

- Category: `Nawigacja po systemie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `dirs`
- Examples:
  - `dirs`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Nawigacja po systemie plików`
```

## `runtime/knowledge/filesystem/operacje-na-plikach-i-katalogach.md`

- size: 10273 bytes
- sha256: `a3c2d08d8401ec6f6ba8c7ef0963cc79cca5615df5a0e142cded335993901156`
- category: knowledge

```markdown
---
title: Operacje na plikach i katalogach
topic: filesystem
source_section: Operacje na plikach i katalogach
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [cp, filesystem, linux, mkdir, nadpisaniem, operacje-na-plikach-i-katalogach, rhcsa, rm, rsync, touch]
---

# Operacje na plikach i katalogach

Imported RHCSA material for 27 commands. Primary command families: cp, mkdir, nadpisaniem, rm, rsync, touch.

## Tags

cp, filesystem, linux, mkdir, nadpisaniem, operacje-na-plikach-i-katalogach, rhcsa, rm, rsync, touch

## Examples

- `touch file.txt`
- `mkdir dirname`
- `touch -t`
- `mkdir -p a/b/c`
- `touch -d`
- `mkdir -m 755 dirname`
- `cp source dest`
- `mkdir -v dirname`
- `cp -r src/ dst/`
- `cp -p src dst`

## Troubleshooting

- Verify the full target path with `pwd` and `ls` before destructive filesystem commands.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Operacje na plikach i katalogach`

## Commands

### `touch file.txt`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `touch`
- Examples:
  - `touch file.txt`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `mkdir dirname`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `mkdir`
- Examples:
  - `mkdir dirname`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `touch -t`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `touch`
- Examples:
  - `touch -t`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `mkdir -p a/b/c`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `mkdir`
- Examples:
  - `mkdir -p a/b/c`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `touch -d`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `touch`
- Examples:
  - `touch -d`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `mkdir -m 755 dirname`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `mkdir`
- Examples:
  - `mkdir -m 755 dirname`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `cp source dest`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `cp`
- Examples:
  - `cp source dest`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `mkdir -v dirname`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `mkdir`
- Examples:
  - `mkdir -v dirname`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `cp -r src/ dst/`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `cp`
- Examples:
  - `cp -r src/ dst/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `cp -p src dst`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `cp`
- Examples:
  - `cp -p src dst`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `cp -a src/ dst/`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `cp`
- Examples:
  - `cp -a src/ dst/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `cp -i src dst`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `cp`
- Examples:
  - `cp -i src dst`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `cp -u src dst`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `cp`
- Examples:
  - `cp -u src dst`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `cp -v src dst`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `cp`
- Examples:
  - `cp -v src dst`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `cp --backup src dst`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `cp`
- Examples:
  - `cp --backup src dst`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `nadpisaniem`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `nadpisaniem`
- Examples:
  - `nadpisaniem`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `rsync -av src/ dst/`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `rsync`
- Examples:
  - `rsync -av src/ dst/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `rsync -avz src/`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `rsync`
- Examples:
  - `rsync -avz src/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `rsync --delete src/`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `rsync`
- Examples:
  - `rsync --delete src/`
- Troubleshooting hint:
  - Verify the full target path with `pwd` and `ls` before destructive filesystem commands.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `rsync -n src/ dst/`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `rsync`
- Examples:
  - `rsync -n src/ dst/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `rm file.txt`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `rm`
- Examples:
  - `rm file.txt`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `rsync`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `rsync`
- Examples:
  - `rsync`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `rm -f file.txt`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `rm`
- Examples:
  - `rm -f file.txt`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `rm -r dir/`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `rm`
- Examples:
  - `rm -r dir/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `rm -rf dir/`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `rm`
- Examples:
  - `rm -rf dir/`
- Troubleshooting hint:
  - Verify the full target path with `pwd` and `ls` before destructive filesystem commands.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `rm -i file`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `rm`
- Examples:
  - `rm -i file`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`

### `rm -v file`

- Category: `Operacje na plikach i katalogach`
- Risk: `unclassified`
- Tags: `filesystem`, `rm`
- Examples:
  - `rm -v file`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Operacje na plikach i katalogach`
```

## `runtime/knowledge/filesystem/przegldanie-zawartoci-plikow.md`

- size: 2285 bytes
- sha256: `3bee5e9ad124d446843c13e8d9d7ac0c8c9a0b6f86d62264a85a8389b1c2f83c`
- category: knowledge

```markdown
---
title: Przegl■danie zawarto■ci plików
topic: filesystem
source_section: Przegl■danie zawarto■ci plików
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [cat, filesystem, linux, przegldanie-zawartoci-plikow, rhcsa]
---

# Przegl■danie zawarto■ci plików

Imported RHCSA material for 4 commands. Primary command families: cat.

## Tags

cat, filesystem, linux, przegldanie-zawartoci-plikow, rhcsa

## Examples

- `cat file.txt`
- `cat -n file.txt`
- `cat -A file.txt`
- `cat file1 file2`

## Troubleshooting

- Validate command intent against current host state before applying changes in production.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Przegl■danie zawarto■ci plików`

## Commands

### `cat file.txt`

- Category: `Przegl■danie zawarto■ci plików`
- Risk: `unclassified`
- Tags: `filesystem`, `cat`
- Examples:
  - `cat file.txt`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Przegl■danie zawarto■ci plików`

### `cat -n file.txt`

- Category: `Przegl■danie zawarto■ci plików`
- Risk: `unclassified`
- Tags: `filesystem`, `cat`
- Examples:
  - `cat -n file.txt`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Przegl■danie zawarto■ci plików`

### `cat -A file.txt`

- Category: `Przegl■danie zawarto■ci plików`
- Risk: `unclassified`
- Tags: `filesystem`, `cat`
- Examples:
  - `cat -A file.txt`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Przegl■danie zawarto■ci plików`

### `cat file1 file2`

- Category: `Przegl■danie zawarto■ci plików`
- Risk: `unclassified`
- Tags: `filesystem`, `cat`
- Examples:
  - `cat file1 file2`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Przegl■danie zawarto■ci plików`
```

## `runtime/knowledge/filesystem/wyszukiwanie-plikow.md`

- size: 16184 bytes
- sha256: `415130ede8a660f67260b6e32f617c649e5a2153b2cde99d43a13235f611e427`
- category: knowledge

```markdown
---
title: Wyszukiwanie plików
topic: filesystem
source_section: Wyszukiwanie plików
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [filesystem, find, linux, reference_file, rhcsa, updatedb, wyszukiwanie-plikow]
---

# Wyszukiwanie plików

Imported RHCSA material for 47 commands. Primary command families: find, reference_file, updatedb.

## Tags

filesystem, find, linux, reference_file, rhcsa, updatedb, wyszukiwanie-plikow

## Examples

- `find / -name`
- `find . -nogroup`
- `find . -name '*.log'`
- `find . -empty`
- `find . -iname`
- `find . -maxdepth 2`
- `find / -type f -name`
- `find . -mindepth 2`
- `find / -type d -name`
- `find . ! -name`

## Troubleshooting

- Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Wyszukiwanie plików`

## Commands

### `find / -name`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find / -name`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -nogroup`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -nogroup`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -name '*.log'`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -name '*.log'`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -empty`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -empty`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -iname`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -iname`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -maxdepth 2`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -maxdepth 2`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find / -type f -name`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find / -type f -name`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -mindepth 2`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -mindepth 2`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find / -type d -name`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find / -type d -name`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . ! -name`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . ! -name`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find / -type l`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find / -type l`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find / -type b`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find / -type b`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find / -type c`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find / -type c`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -name '*.tmp'`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -name '*.tmp'`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -size +100M`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -size +100M`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -size -10k`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -size -10k`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -size +1G`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -size +1G`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -name '*.txt'`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -name '*.txt'`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -size 512c`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -size 512c`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -name '*.py'`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -name '*.py'`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -newer`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -newer`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -type f -name`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -type f -name`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `reference_file`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `reference_file`
- Examples:
  - `reference_file`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -mtime -7`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -mtime -7`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -type f -newer`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -type f -newer`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -mtime +30`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -mtime +30`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find /tmp -mtime +7`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find /tmp -mtime +7`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -mmin -60`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -mmin -60`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -name`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -name`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -atime -1`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -atime -1`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -mount -name`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -mount -name`
- Troubleshooting hint:
  - Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -ctime -1`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -ctime -1`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -xdev -name`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -xdev -name`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -perm 644`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -perm 644`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find / -inum 12345`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find / -inum 12345`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -perm -644`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -perm -644`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -links +1`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -links +1`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -perm /644`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -perm /644`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -perm -4000`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -perm -4000`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -perm -2000`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -perm -2000`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `updatedb`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `updatedb`
- Examples:
  - `updatedb`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -perm -1000`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -perm -1000`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -user`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -user`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -group`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -group`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -uid 1000`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -uid 1000`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -gid 1000`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -gid 1000`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`

### `find . -nouser`

- Category: `Wyszukiwanie plików`
- Risk: `unclassified`
- Tags: `filesystem`, `find`
- Examples:
  - `find . -nouser`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Wyszukiwanie plików`
```

## `runtime/knowledge/index/command_index.json`

- size: 130492 bytes
- sha256: `055d70472f22deebb929a659c9c3321df3eb4d1298aae3dc837dcbed1d1e66fe`
- category: knowledge

```json
{
  "$": [
    "$",
    "$#",
    "$@",
    "TMPFILE=$(mktemp)",
    "VAR=$(command)",
    "echo $!",
    "echo $#",
    "echo $((RANDOM %",
    "echo $@",
    "echo ${#ARRAY[@]}"
  ],
  "$$": [
    "$$",
    "echo $$"
  ],
  "$*": [
    "echo $*"
  ],
  "$0": [
    "$0",
    "echo $0"
  ],
  "$1": [
    "awk '{print $1}'",
    "awk '{sum+=$1}",
    "awk -F: '{print $1}'"
  ],
  "$?": [
    "$?",
    "echo $?"
  ],
  "$bash_version": [
    "echo $BASH_VERSION"
  ],
  "$histfile": [
    "echo $HISTFILE"
  ],
  "$histfilesize": [
    "echo $HISTFILESIZE"
  ],
  "$histsize": [
    "echo $HISTSIZE"
  ],
  "$home": [
    "echo $HOME"
  ],
  "$nf": [
    "awk '{print $NF}'"
  ],
  "$oldpwd": [
    "echo $OLDPWD"
  ],
  "$path": [
    "echo $PATH"
  ],
  "$ps1": [
    "echo $PS1"
  ],
  "$pwd": [
    "echo $PWD"
  ],
  "$shell": [
    "echo $SHELL"
  ],
  "$var": [
    "echo \"Value: $VAR\""
  ],
  "$variable": [
    "echo $VARIABLE"
  ],
  "${array": [
    "echo ${ARRAY[0]}",
    "echo ${ARRAY[@]}"
  ],
  "${map": [
    "echo ${MAP[k1]}"
  ],
  "*": [
    "*",
    "echo '3.14 * 2' | bc"
  ],
  "*.log": [
    "find . -name '*.log'"
  ],
  "*.py": [
    "find . -name '*.py'"
  ],
  "*.tmp": [
    "find . -name '*.tmp'"
  ],
  "*.txt": [
    "find . -name '*.txt'"
  ],
  "*/": [
    "ls -d */"
  ],
  "+/pattern": [
    "vim +/pattern"
  ],
  "+1": [
    "find . -links +1"
  ],
  "+10": [
    "vim +10 file.txt"
  ],
  "+100m": [
    "find . -size +100M"
  ],
  "+1g": [
    "find . -size +1G"
  ],
  "+30": [
    "find . -mtime +30"
  ],
  "+7": [
    "find /tmp -mtime +7"
  ],
  "+t": [
    "chmod +t dir"
  ],
  "+x": [
    "chmod +x script.sh"
  ],
  "-": [
    "cd -",
    "tar -czf - /path |"
  ],
  "--add-f": [
    "firewall-cmd --add-f"
  ],
  "--add-p": [
    "firewall-cmd --add-p"
  ],
  "--add-port": [
    "--add-port=8080/tcp"
  ],
  "--add-r": [
    "firewall-cmd --add-r"
  ],
  "--add-s": [
    "firewall-cmd --add-s"
  ],
  "--add-service": [
    "--add-service=http",
    "--add-service=https"
  ],
  "--backup": [
    "cp --backup src dst"
  ],
  "--cap-add": [
    "podman run --cap-add"
  ],
  "--changelog": [
    "rpm -q --changelog"
  ],
  "--color": [
    "ls --color=auto"
  ],
  "--complete-reload": [
    "--complete-reload"
  ],
  "--cpus": [
    "podman run --cpus"
  ],
  "--delete": [
    "rsync --delete src/",
    "tar --delete -f"
  ],
  "--disk-usage": [
    "--disk-usage"
  ],
  "--exclude-vcs": [
    "tar --exclude-vcs"
  ],
  "--filename": [
    "--filename=/tmp/test"
  ],
  "--format": [
    "podman ps --format"
  ],
  "--get-active-zones": [
    "--get-active-zones"
  ],
  "--get-default-zone": [
    "--get-default-zone"
  ],
  "--get-zones": [
    "--get-zones"
  ],
  "--import": [
    "rpm --import"
  ],
  "--leak-check": [
    "--leak-check=full"
  ],
  "--level": [
    "--level=err,warn"
  ],
  "--list-all": [
    "--list-all"
  ],
  "--list-ports": [
    "--list-ports"
  ],
  "--list-rich-rules": [
    "--list-rich-rules"
  ],
  "--list-services": [
    "--list-services"
  ],
  "--list-tags": [
    "--list-tags"
  ],
  "--memory": [
    "podman run --memory"
  ],
  "--name": [
    "podman run --name"
  ],
  "--network": [
    "podman run --network"
  ],
  "--newer-mtime": [
    "--newer-mtime='2023-"
  ],
  "--pod": [
    "podman run --pod"
  ],
  "--raid-devices": [
    "--raid-devices=2"
  ],
  "--remov": [
    "firewall-cmd --remov"
  ],
  "--restart": [
    "--restart=always",
    "podman run --restart"
  ],
  "--rm": [
    "podman run --rm"
  ],
  "--runti": [
    "firewall-cmd --runti"
  ],
  "--scan": [
    "--scan"
  ],
  "--scripts": [
    "rpm -q --scripts",
    "rpm -qp --scripts"
  ],
  "--set-d": [
    "firewall-cmd --set-d"
  ],
  "--since": [
    "journalctl --since"
  ],
  "--state": [
    "firewall-cmd --state"
  ],
  "--tail": [
    "podman logs --tail"
  ],
  "--target": [
    "--target=x86_64-efi"
  ],
  "--type": [
    "--type=service"
  ],
  "--until": [
    "journalctl --until"
  ],
  "--user": [
    "systemctl --user"
  ],
  "--vacuum-size": [
    "--vacuum-size=500M"
  ],
  "--version": [
    "podman --version"
  ],
  "--zone": [
    "--zone=drop",
    "--zone=public"
  ],
  "-1": [
    "find . -atime -1",
    "find . -ctime -1",
    "journalctl -b -1"
  ],
  "-1000": [
    "find . -perm -1000"
  ],
  "-10k": [
    "find . -size -10k"
  ],
  "-20": [
    "ls /etc | head -20"
  ],
  "-2000": [
    "find . -perm -2000",
    "find / -perm -2000"
  ],
  "-4000": [
    "find . -perm -4000",
    "find / -perm -4000"
  ],
  "-6": [
    "ip -6 addr show",
    "ip -6 route show"
  ],
  "-60": [
    "find . -mmin -60"
  ],
  "-644": [
    "find . -perm -644"
  ],
  "-7": [
    "find . -mtime -7"
  ],
  "-a": [
    "-a",
    "cat -A file.txt",
    "cp -a src/ dst/",
    "grep -A 3 'pattern'",
    "mount -a",
    "podman images -a",
    "podman ps -a",
    "podman rm -a",
    "podman rmi -a",
    "semanage fcontext -a",
    "semanage login -a -s",
    "semanage port -a -t",
    "ssh -A user@host"
  ],
  "-ag": [
    "usermod -aG docker",
    "usermod -aG group",
    "usermod -aG wheel"
  ],
  "-alh": [
    "alias ll='ls -alh'"
  ],
  "-atime": [
    "find . -atime -1"
  ],
  "-av": [
    "rsync -av src/ dst/"
  ],
  "-avz": [
    "rsync -avz",
    "rsync -avz -e ssh",
    "rsync -avz src/"
  ],
  "-b": [
    "grep -B 3 'pattern'",
    "journalctl -b",
    "journalctl -b -1"
  ],
  "-c": [
    "grep -C 3 'pattern'",
    "grep -c 'pattern'",
    "useradd -c 'Imi■",
    "usermod -c 'Nowy"
  ],
  "-ctime": [
    "find . -ctime -1"
  ],
  "-cvf": [
    "tar -cvf archive.tar"
  ],
  "-cvjf": [
    "tar -cvJf",
    "tar -cvjf"
  ],
  "-cvzf": [
    "tar -cvzf"
  ],
  "-czf": [
    "tar -czf - /path |",
    "tar -czf arch.tar.gz"
  ],
  "-d": [
    "ls -d */",
    "podman run -d image",
    "semanage fcontext -d",
    "semanage port -d -t",
    "ssh -D 1080",
    "touch -d",
    "useradd -d",
    "usermod -d /new/home",
    "vim -d file1 file2"
  ],
  "-dz": [
    "ls -dZ dir/"
  ],
  "-e": [
    "grep -E 'pat1|pat2'",
    "podman run -e",
    "rpm -e package",
    "rsync -avz -e ssh",
    "useradd -e",
    "usermod -e",
    "usermod -e '' user"
  ],
  "-empty": [
    "find . -empty"
  ],
  "-f": [
    "awk -F: '{print $1}'",
    "grep -F 'literal'",
    "journalctl -f",
    "journalctl -f -u",
    "podman build -f",
    "podman inspect -f",
    "podman logs -f",
    "podman rm -f",
    "podman rmi -f image",
    "restorecon -F /path/",
    "rm -f file.txt",
    "ssh -N -f -L",
    "tar --delete -f",
    "useradd -f 30 user"
  ],
  "-fvh": [
    "rpm -Fvh package.rpm"
  ],
  "-g": [
    "useradd -G g1,g2",
    "useradd -g group",
    "usermod -G g1,g2",
    "usermod -g group"
  ],
  "-gid": [
    "find . -gid 1000"
  ],
  "-group": [
    "find . -group"
  ],
  "-i": [
    "cp -i src dst",
    "grep -i 'pattern'",
    "ls -i",
    "podman load -i",
    "rm -i file",
    "ssh -i"
  ],
  "-iname": [
    "find . -iname"
  ],
  "-inum": [
    "find / -inum 12345"
  ],
  "-it": [
    "podman exec -it",
    "podman run -it image"
  ],
  "-ivh": [
    "rpm -ivh package.rpm"
  ],
  "-j": [
    "ssh -J jumphost"
  ],
  "-k": [
    "journalctl -k",
    "rpm -K package.rpm"
  ],
  "-l": [
    "grep -l 'pattern'",
    "ls -l",
    "ls /proc | wc -l",
    "semanage boolean -l",
    "semanage fcontext -l",
    "semanage login -l",
    "semanage port -l",
    "semanage port -l |",
    "semanage user -l",
    "ssh -L",
    "ssh -N -f -L",
    "usermod -L user",
    "usermod -l newname"
  ],
  "-la": [
    "ls -la"
  ],
  "-lh": [
    "ls -lh"
  ],
  "-links": [
    "find . -links +1"
  ],
  "-ls": [
    "ls -lS"
  ],
  "-lt": [
    "ls -lt"
  ],
  "-m": [
    "grep -m 5 'pattern'",
    "mkdir -m 755 dirname",
    "semanage fcontext -m",
    "semanage port -m -t",
    "useradd -M user",
    "useradd -m -s",
    "useradd -m username"
  ],
  "-maxdepth": [
    "find . -maxdepth 2"
  ],
  "-mindepth": [
    "find . -mindepth 2"
  ],
  "-mmin": [
    "find . -mmin -60"
  ],
  "-mount": [
    "find . -mount -name"
  ],
  "-mtime": [
    "find . -mtime +30",
    "find . -mtime -7",
    "find /tmp -mtime +7"
  ],
  "-n": [
    "cat -n file.txt",
    "grep -n 'pattern'",
    "journalctl -n 50",
    "rsync -n src/ dst/",
    "ssh -N -f -L",
    "useradd -N user"
  ],
  "-name": [
    "find . ! -name",
    "find . -mount -name",
    "find . -name",
    "find . -name '*.log'",
    "find . -name '*.py'",
    "find . -name '*.tmp'",
    "find . -name '*.txt'",
    "find . -type f -name",
    "find . -xdev -name",
    "find / -name",
    "find / -type d -name",
    "find / -type f -name"
  ],
  "-newer": [
    "find . -newer",
    "find . -type f -newer"
  ],
  "-nogroup": [
    "find . -nogroup"
  ],
  "-nouser": [
    "find . -nouser"
  ],
  "-o": [
    "grep -o 'pattern'",
    "journalctl -o",
    "journalctl -o json",
    "mount -o",
    "mount -o remount,ro",
    "mount -o remount,rw",
    "mount -o ro",
    "mount -o ro,soft",
    "mount -o rw,noexec",
    "podman save image -o",
    "ssh -o",
    "ssh -o BatchMode=yes",
    "ssh -o PasswordAuthe",
    "ssh -o PreferredAuth",
    "ssh -o StrictHostKey"
  ],
  "-o+w": [
    "find / -perm -o+w"
  ],
  "-p": [
    "cp -p src dst",
    "grep -P '\\d+' file",
    "journalctl -p",
    "journalctl -p err",
    "mkdir -p a/b/c",
    "podman run -p",
    "setsebool -P",
    "setsebool -P httpd_c",
    "setsebool -P samba_e",
    "ssh -p 2222",
    "systemctl show -p"
  ],
  "-perm": [
    "find . -perm -1000",
    "find . -perm -2000",
    "find . -perm -4000",
    "find . -perm -644",
    "find . -perm /644",
    "find . -perm 644",
    "find / -perm -2000",
    "find / -perm -4000",
    "find / -perm -o+w"
  ],
  "-print": [
    "find /path -print |"
  ],
  "-q": [
    "grep -q 'pattern'",
    "podman ps -q",
    "rpm -q --changelog",
    "rpm -q --scripts"
  ],
  "-qa": [
    "podman ps -qa",
    "rpm -qa",
    "rpm -qa kernel"
  ],
  "-qc": [
    "rpm -qc package"
  ],
  "-qd": [
    "rpm -qd package"
  ],
  "-qf": [
    "rpm -qf"
  ],
  "-qi": [
    "rpm -qi package"
  ],
  "-qip": [
    "rpm -qip package.rpm"
  ],
  "-ql": [
    "rpm -ql package"
  ],
  "-qp": [
    "rpm -qp --scripts"
  ],
  "-qr": [
    "rpm -qR package"
  ],
  "-r": [
    "chmod -R 755 dir/",
    "chown -R user:group",
    "cp -r src/ dst/",
    "grep -r 'pattern'",
    "ls -R",
    "restorecon -R",
    "rm -r dir/",
    "ssh -R",
    "useradd -r sysuser",
    "vim -R file.txt"
  ],
  "-rf": [
    "rm -rf dir/"
  ],
  "-rv": [
    "restorecon -Rv"
  ],
  "-rvf": [
    "tar -rvf archive.tar"
  ],
  "-s": [
    "ip -s link show eth0",
    "podman kill -s",
    "semanage login -a -s",
    "useradd -m -s",
    "usermod -s /bin/zsh"
  ],
  "-size": [
    "find . -size +100M",
    "find . -size +1G",
    "find . -size -10k",
    "find . -size 512c"
  ],
  "-t": [
    "-t",
    "journalctl -t",
    "mount -t cifs",
    "mount -t ext4",
    "mount -t nfs",
    "mount -t nfs4",
    "mount -t xfs",
    "mount | column -t",
    "podman build -t",
    "podman stop -t 0",
    "semanage port -a -t",
    "semanage port -d -t",
    "semanage port -m -t",
    "ssh -t user@host",
    "touch -t"
  ],
  "-tvf": [
    "tar -tvf archive.tar"
  ],
  "-tvzf": [
    "tar -tvzf"
  ],
  "-type": [
    "find . -type f -name",
    "find . -type f -newer",
    "find / -type b",
    "find / -type c",
    "find / -type d -name",
    "find / -type f -name",
    "find / -type l"
  ],
  "-u": [
    "cp -u src dst",
    "journalctl -f -u",
    "journalctl -u",
    "journalctl -u sshd",
    "podman exec -u root",
    "podman run -u user",
    "useradd -u 1500 user",
    "usermod -U user",
    "usermod -u 1600 user",
    "vim -u NONE file.txt"
  ],
  "-uid": [
    "find . -uid 1000"
  ],
  "-user": [
    "find . -user"
  ],
  "-uvf": [
    "tar -uvf archive.tar"
  ],
  "-uvh": [
    "rpm -Uvh package.rpm"
  ],
  "-v": [
    "awk -v FS=':'",
    "cp -v src dst",
    "grep -v 'pattern'",
    "mkdir -v dirname",
    "podman run -v",
    "rm -v file",
    "rpm -V package",
    "ssh -v user@host"
  ],
  "-va": [
    "rpm -Va"
  ],
  "-vvv": [
    "ssh -vvv user@host"
  ],
  "-w": [
    "grep -w 'word' file"
  ],
  "-x": [
    "ssh -X user@host"
  ],
  "-xdev": [
    "find . -xdev -name"
  ],
  "-xe": [
    "journalctl -xe"
  ],
  "-xvf": [
    "tar -xvf archive.tar"
  ],
  "-xvjf": [
    "tar -xvJf",
    "tar -xvjf"
  ],
  "-xvzf": [
    "tar -xvzf"
  ],
  "-y": [
    "dnf install -y"
  ],
  "-z": [
    "ls -Z dir/",
    "ls -Z file"
  ],
  "/": [
    "cd /",
    "find / -inum 12345",
    "find / -name",
    "find / -perm -2000",
    "find / -perm -4000",
    "find / -perm -o+w",
    "find / -type b",
    "find / -type c",
    "find / -type d -name",
    "find / -type f -name",
    "find / -type l"
  ],
  "/.autorelabel": [
    "touch /.autorelabel"
  ],
  "//server": [
    "//server"
  ],
  "/644": [
    "find . -perm /644"
  ],
  "/bin/bash": [
    "/bin/bash"
  ],
  "/bin/zsh": [
    "usermod -s /bin/zsh"
  ],
  "/boot/": [
    "ls /boot/"
  ],
  "/boot/grub2/": [
    "ls /boot/grub2/"
  ],
  "/boot/grub2/grub.cfg": [
    "/boot/grub2/grub.cfg"
  ],
  "/boot/initramfs*": [
    "/boot/initramfs*"
  ],
  "/container": [
    "/host:/container"
  ],
  "/dev/md0": [
    "/dev/md0"
  ],
  "/dev/null": [
    "1>/dev/null",
    "2>/dev/null"
  ],
  "/dev/sdb": [
    "/dev/sdb"
  ],
  "/dev/sdb1": [
    "/dev/sdb1",
    "mount /dev/sdb1 /mnt"
  ],
  "/dev/sdc": [
    "/dev/sdc"
  ],
  "/dev/sdd": [
    "/dev/sdd"
  ],
  "/dir": [
    "/dir"
  ],
  "/etc": [
    "ls /etc | head -20"
  ],
  "/etc/anacrontab": [
    "cat /etc/anacrontab"
  ],
  "/etc/at.allow": [
    "cat /etc/at.allow"
  ],
  "/etc/at.deny": [
    "cat /etc/at.deny"
  ],
  "/etc/audit/audit": [
    "cat /etc/audit/audit"
  ],
  "/etc/auto.master": [
    "cat /etc/auto.master"
  ],
  "/etc/auto.misc": [
    "cat /etc/auto.misc"
  ],
  "/etc/bashrc": [
    "cat /etc/bashrc"
  ],
  "/etc/chrony.conf": [
    "cat /etc/chrony.conf"
  ],
  "/etc/containers/": [
    "cat /etc/containers/"
  ],
  "/etc/cron.allow": [
    "cat /etc/cron.allow"
  ],
  "/etc/cron.d/": [
    "ls /etc/cron.d/"
  ],
  "/etc/cron.daily": [
    "/etc/cron.daily"
  ],
  "/etc/cron.daily/": [
    "ls /etc/cron.daily/"
  ],
  "/etc/cron.deny": [
    "cat /etc/cron.deny"
  ],
  "/etc/cron.hourly/": [
    "ls /etc/cron.hourly/"
  ],
  "/etc/cron.weekly/": [
    "ls /etc/cron.weekly/"
  ],
  "/etc/crontab": [
    "cat /etc/crontab"
  ],
  "/etc/crypto-poli": [
    "cat /etc/crypto-poli"
  ],
  "/etc/exports": [
    "cat /etc/exports"
  ],
  "/etc/fstab": [
    "cat /etc/fstab",
    "cat /etc/fstab |"
  ],
  "/etc/group": [
    "cat /etc/group"
  ],
  "/etc/gshadow": [
    "cat /etc/gshadow"
  ],
  "/etc/hostname": [
    "cat /etc/hostname"
  ],
  "/etc/hosts": [
    "cat /etc/hosts"
  ],
  "/etc/kdump.conf": [
    "cat /etc/kdump.conf"
  ],
  "/etc/logrotate.d/": [
    "ls /etc/logrotate.d/"
  ],
  "/etc/mdadm.conf": [
    "cat /etc/mdadm.conf"
  ],
  "/etc/modprobe.d/": [
    "cat /etc/modprobe.d/"
  ],
  "/etc/os-release": [
    "cat /etc/os-release"
  ],
  "/etc/passwd": [
    "cat /etc/passwd"
  ],
  "/etc/profile": [
    "cat /etc/profile"
  ],
  "/etc/profile.d/": [
    "ls /etc/profile.d/"
  ],
  "/etc/resolv.conf": [
    "cat /etc/resolv.conf"
  ],
  "/etc/selinux/config": [
    "/etc/selinux/config"
  ],
  "/etc/shadow": [
    "cat /etc/shadow"
  ],
  "/etc/sysconfig/n": [
    "cat /etc/sysconfig/n"
  ],
  "/etc/sysctl.conf": [
    "cat /etc/sysctl.conf"
  ],
  "/etc/sysctl.d/": [
    "cat /etc/sysctl.d/"
  ],
  "/etc/systemd/sys": [
    "cat /etc/systemd/sys"
  ],
  "/host": [
    "/host:/container"
  ],
  "/mnt": [
    "/mnt",
    "mount /dev/sdb1 /mnt",
    "mount UUID=xxx /mnt"
  ],
  "/mnt/nfs/share": [
    "ls /mnt/nfs/share"
  ],
  "/new/home": [
    "usermod -d /new/home"
  ],
  "/path": [
    "find /path -print |",
    "tar -czf - /path |"
  ],
  "/path/": [
    "restorecon -F /path/"
  ],
  "/path/to/dir": [
    "cd /path/to/dir"
  ],
  "/path/to/file": [
    "/path/to/file"
  ],
  "/pattern": [
    "/pattern"
  ],
  "/pattern/": [
    "awk '/pattern/' file"
  ],
  "/proc": [
    "ls /proc | wc -l"
  ],
  "/proc/cmdline": [
    "cat /proc/cmdline"
  ],
  "/proc/cpuinfo": [
    "cat /proc/cpuinfo"
  ],
  "/proc/loadavg": [
    "cat /proc/loadavg"
  ],
  "/proc/mdstat": [
    "cat /proc/mdstat"
  ],
  "/proc/meminfo": [
    "cat /proc/meminfo"
  ],
  "/proc/mounts": [
    "cat /proc/mounts"
  ],
  "/proc/net/tcp": [
    "cat /proc/net/tcp"
  ],
  "/proc/net/udp": [
    "cat /proc/net/udp"
  ],
  "/proc/pid/limits": [
    "cat /proc/PID/limits"
  ],
  "/proc/pid/maps": [
    "cat /proc/PID/maps"
  ],
  "/proc/pid/status": [
    "cat /proc/PID/status"
  ],
  "/proc/sys/kernel": [
    "cat /proc/sys/kernel"
  ],
  "/proc/sys/net/nf": [
    "cat /proc/sys/net/nf"
  ],
  "/proc/uptime": [
    "cat /proc/uptime"
  ],
  "/proc/version": [
    "cat /proc/version"
  ],
  "/script.sh": [
    "./script.sh"
  ],
  "/share": [
    "server:/share"
  ],
  "/sys/block/sda/q": [
    "cat /sys/block/sda/q"
  ],
  "/sys/class/dmi/i": [
    "cat /sys/class/dmi/i"
  ],
  "/sys/fs/cgroup/": [
    "ls /sys/fs/cgroup/"
  ],
  "/sys/fs/cgroup/m": [
    "cat /sys/fs/cgroup/m"
  ],
  "/tmp": [
    "find /tmp -mtime +7"
  ],
  "/tmp/cap.pcap": [
    "/tmp/cap.pcap"
  ],
  "/tmp/test": [
    "--filename=/tmp/test"
  ],
  "/var/l": [
    "grep 'denied' /var/l"
  ],
  "/var/log/audit/a": [
    "cat /var/log/audit/a"
  ],
  "/var/log/cron": [
    "cat /var/log/cron"
  ],
  "/var/log/maillog": [
    "cat /var/log/maillog"
  ],
  "/var/log/messages": [
    "/var/log/messages"
  ],
  "/var/log/sa/sadd": [
    "/var/log/sa/saDD"
  ],
  "/var/log/secure": [
    "cat /var/log/secure"
  ],
  "/var/spool/cron/": [
    "cat /var/spool/cron/"
  ],
  "0": [
    "0",
    "echo ${ARRAY[0]}",
    "podman stop -t 0"
  ],
  "1": [
    "1>/dev/null"
  ],
  "1..5": [
    "echo {1..5}"
  ],
  "10": [
    "ConnectTimeout=10"
  ],
  "100": [
    "100))"
  ],
  "1000": [
    "count=1000",
    "find . -gid 1000",
    "find . -uid 1000"
  ],
  "1080": [
    "ssh -D 1080"
  ],
  "10g": [
    "10G"
  ],
  "12345": [
    "find / -inum 12345"
  ],
  "1500": [
    "useradd -u 1500 user"
  ],
  "1600": [
    "usermod -u 1600 user"
  ],
  "1755": [
    "chmod 1755 dir"
  ],
  "2": [
    "--raid-devices=2",
    "2>/dev/null",
    "echo '3.14 * 2' | bc",
    "find . -maxdepth 2",
    "find . -mindepth 2"
  ],
  "2023-": [
    "--newer-mtime='2023-"
  ],
  "2222": [
    "ssh -p 2222"
  ],
  "2755": [
    "chmod 2755 dir"
  ],
  "3": [
    "grep -A 3 'pattern'",
    "grep -B 3 'pattern'",
    "grep -C 3 'pattern'"
  ],
  "3.14": [
    "echo '3.14 * 2' | bc"
  ],
  "30": [
    "useradd -f 30 user"
  ],
  "32": [
    "32"
  ],
  "4096": [
    "4096"
  ],
  "4755": [
    "chmod 4755 file"
  ],
  "5": [
    "awk 'NR==5' file",
    "awk 'NR>=5 &&",
    "dnf history info 5",
    "dnf history redo 5",
    "dnf history undo 5",
    "grep -m 5 'pattern'"
  ],
  "50": [
    "journalctl -n 50"
  ],
  "500m": [
    "--vacuum-size=500M"
  ],
  "512c": [
    "find . -size 512c"
  ],
  "512m": [
    "t_in_bytes=512M"
  ],
  "5dd": [
    "5dd"
  ],
  "5yy": [
    "5yy"
  ],
  "600": [
    "chmod 600 file",
    "chmod 600 ~/.ssh/aut"
  ],
  "644": [
    "chmod 644 file",
    "find . -perm 644"
  ],
  "700": [
    "chmod 700 ~/.ssh/"
  ],
  "755": [
    "chmod -R 755 dir/",
    "chmod 755 file",
    "mkdir -m 755 dirname"
  ],
  "777": [
    "chmod 777 file"
  ],
  "8.8.8.8": [
    "ip route get 8.8.8.8"
  ],
  "80": [
    "8080:localhost:80"
  ],
  "8080": [
    "8080:localhost:80"
  ],
  "8080/tcp": [
    "--add-port=8080/tcp",
    "e-port=8080/tcp"
  ],
  "9000": [
    "9000"
  ],
  "?pattern": [
    "?pattern"
  ],
  "a": [
    "A",
    "a",
    "echo {a,b,c}.log",
    "w■a■ciciel)",
    "w■a■ciciela"
  ],
  "a+r": [
    "chmod a+r file"
  ],
  "a/b/c": [
    "mkdir -p a/b/c"
  ],
  "accepted": [
    "grep 'Accepted'"
  ],
  "access.redhat.com/u": [
    ".access.redhat.com/u"
  ],
  "add": [
    "ip addr add",
    "ip netns add myns",
    "ip route add",
    "ip route add default",
    "nmcli connection add"
  ],
  "addr": [
    "ip -6 addr show",
    "ip addr",
    "ip addr add",
    "ip addr del",
    "ip addr show",
    "ip addr show eth0"
  ],
  "administracyjne": [
    "--zone=drop",
    "/tmp/cap.pcap",
    "alternatives",
    "authselect",
    "bash",
    "cat /etc/crypto-poli",
    "cat /sys/fs/cgroup/m",
    "emory/mygroup/memory",
    "fips-mode-setup",
    "ip netns add myns",
    "ip netns delete myns",
    "ip netns exec myns",
    "ip netns list",
    "ls /sys/fs/cgroup/",
    "memory:mygroup",
    "mygroup",
    "ntsysv",
    "scap-workbench",
    "systemd-cgls",
    "systemd-cgtop",
    "t_in_bytes=512M",
    "update-alternatives",
    "update-crypto-polici",
    "wireshark"
  ],
  "aktualizacjami": [
    "aktualizacjami"
  ],
  "alias": [
    "alias",
    "alias ll='ls -alh'"
  ],
  "all": [
    "dnf clean all",
    "dnf repolist all",
    "ip neigh flush all"
  ],
  "alternatives": [
    "alternatives"
  ],
  "always": [
    "--restart=always"
  ],
  "arch.tar.gz": [
    "tar -czf arch.tar.gz"
  ],
  "archive.tar": [
    "tar -cvf archive.tar",
    "tar -rvf archive.tar",
    "tar -tvf archive.tar",
    "tar -uvf archive.tar",
    "tar -xvf archive.tar"
  ],
  "archive.tar.bz2": [
    "archive.tar.bz2"
  ],
  "archive.tar.gz": [
    "archive.tar.gz"
  ],
  "archive.tar.xz": [
    "archive.tar.xz"
  ],
  "archiwizacja": [
    "--newer-mtime='2023-",
    "archive.tar.bz2",
    "archive.tar.gz",
    "archive.tar.xz",
    "find /path -print |",
    "newfile",
    "tar",
    "tar --delete -f",
    "tar --exclude-vcs",
    "tar -cvJf",
    "tar -cvf archive.tar",
    "tar -cvjf",
    "tar -cvzf",
    "tar -czf - /path |",
    "tar -czf arch.tar.gz",
    "tar -rvf archive.tar",
    "tar -tvf archive.tar",
    "tar -tvzf",
    "tar -uvf archive.tar",
    "tar -xvJf",
    "tar -xvf archive.tar",
    "tar -xvjf",
    "tar -xvzf"
  ],
  "array": [
    "echo ${#ARRAY[@]}"
  ],
  "array+": [
    "ARRAY+=('e')"
  ],
  "asno": [
    "chmod",
    "chmod +t dir",
    "chmod -R 755 dir/",
    "chmod 1755 dir",
    "chmod 2755 dir",
    "chmod 4755 file",
    "chmod 600 file",
    "chmod 644 file",
    "chmod 755 file",
    "chmod 777 file",
    "chmod a+r file",
    "chmod g+s dir",
    "chmod g-w file",
    "chmod o-r file",
    "chmod u+s file",
    "chmod u+x file",
    "chmod u=rwx,g=rx,o=r",
    "chown",
    "chown -R user:group",
    "chown :group file",
    "chown user file",
    "chown user:group",
    "dir/",
    "find / -perm -2000",
    "find / -perm -4000",
    "find / -perm -o+w",
    "katalogu",
    "ls -Z file",
    "umask",
    "w■a■ciciel)",
    "w■a■ciciela"
  ],
  "atq": [
    "atq"
  ],
  "aureport": [
    "aureport"
  ],
  "authselect": [
    "authselect"
  ],
  "auto": [
    "ls --color=auto"
  ],
  "autofs": [
    "cat /etc/auto.master",
    "cat /etc/auto.misc",
    "cat /etc/exports",
    "exportfs",
    "firewall-cmd --add-s",
    "ls /mnt/nfs/share",
    "mount -o",
    "mount -o ro,soft",
    "mount -t nfs",
    "mount -t nfs4",
    "nfs-server",
    "nfsstat",
    "nosuid,noexec",
    "server:/share"
  ],
  "autoremove": [
    "dnf autoremove"
  ],
  "available": [
    "dnf list available"
  ],
  "awk": [
    "awk '/pattern/' file",
    "awk 'END{print NR}'",
    "awk 'NR==5' file",
    "awk 'NR>=5 &&",
    "awk '{print $1}'",
    "awk '{print $NF}'",
    "awk '{print NF}'",
    "awk '{sum+=$1}",
    "awk -F: '{print $1}'",
    "awk -v FS=':'"
  ],
  "b": [
    "b",
    "echo {a,b,c}.log",
    "find / -type b"
  ],
  "baseboard": [
    "baseboard"
  ],
  "basename": [
    "basename"
  ],
  "bash": [
    "$#",
    "$$",
    "$0",
    "$?",
    "$@",
    "./script.sh",
    "1>/dev/null",
    "2>/dev/null",
    "ARRAY+=('e')",
    "TMPFILE=$(mktemp)",
    "VAR=$(command)",
    "VAR='value'",
    "bash",
    "break",
    "chmod +x script.sh",
    "continue",
    "do",
    "done",
    "echo \"Value: $VAR\"",
    "echo ${MAP[k1]}",
    "else",
    "esac",
    "fi",
    "mktemp",
    "then",
    "}"
  ],
  "batch": [
    "batch"
  ],
  "batchmode": [
    "ssh -o BatchMode=yes"
  ],
  "bc": [
    "echo '3.14 * 2' | bc"
  ],
  "blkid": [
    "blkid"
  ],
  "bonnie++": [
    "bonnie++"
  ],
  "boolean": [
    "semanage boolean -l"
  ],
  "boot": [
    "--target=x86_64-efi",
    "/boot/grub2/grub.cfg",
    "/boot/initramfs*",
    "GRUB",
    "cat /etc/modprobe.d/",
    "cat /etc/sysctl.conf",
    "cat /etc/sysctl.d/",
    "cat /proc/cmdline",
    "cat /proc/sys/kernel",
    "cat /proc/version",
    "dnf install kernel",
    "dnf remove",
    "echo 'module_name' >",
    "echo 'net.ipv4.ip_fo",
    "grub2-install",
    "grub2-set-default",
    "halt",
    "insmod",
    "kernel",
    "ls /boot/",
    "ls /boot/grub2/",
    "lsmod",
    "poweroff",
    "reboot",
    "rpm -qa kernel",
    "sync",
    "sysctl",
    "systemctl emergency",
    "systemctl rescue"
  ],
  "break": [
    "break"
  ],
  "build": [
    "podman build",
    "podman build -f",
    "podman build -t"
  ],
  "c": [
    "find / -type c"
  ],
  "c$": [
    "c$"
  ],
  "cat": [
    "cat",
    "cat -A file.txt",
    "cat -n file.txt",
    "cat /etc/anacrontab",
    "cat /etc/at.allow",
    "cat /etc/at.deny",
    "cat /etc/audit/audit",
    "cat /etc/auto.master",
    "cat /etc/auto.misc",
    "cat /etc/bashrc",
    "cat /etc/chrony.conf",
    "cat /etc/containers/",
    "cat /etc/cron.allow",
    "cat /etc/cron.deny",
    "cat /etc/crontab",
    "cat /etc/crypto-poli",
    "cat /etc/exports",
    "cat /etc/fstab",
    "cat /etc/fstab |",
    "cat /etc/group",
    "cat /etc/gshadow",
    "cat /etc/hostname",
    "cat /etc/hosts",
    "cat /etc/kdump.conf",
    "cat /etc/mdadm.conf",
    "cat /etc/modprobe.d/",
    "cat /etc/os-release",
    "cat /etc/passwd",
    "cat /etc/profile",
    "cat /etc/resolv.conf",
    "cat /etc/shadow",
    "cat /etc/sysconfig/n",
    "cat /etc/sysctl.conf",
    "cat /etc/sysctl.d/",
    "cat /etc/systemd/sys",
    "cat /proc/PID/limits",
    "cat /proc/PID/maps",
    "cat /proc/PID/status",
    "cat /proc/cmdline",
    "cat /proc/cpuinfo",
    "cat /proc/loadavg",
    "cat /proc/mdstat",
    "cat /proc/meminfo",
    "cat /proc/mounts",
    "cat /proc/net/tcp",
    "cat /proc/net/udp",
    "cat /proc/sys/kernel",
    "cat /proc/sys/net/nf",
    "cat /proc/uptime",
    "cat /proc/version",
    "cat /sys/block/sda/q",
    "cat /sys/class/dmi/i",
    "cat /sys/fs/cgroup/m",
    "cat /var/log/audit/a",
    "cat /var/log/cron",
    "cat /var/log/maillog",
    "cat /var/log/secure",
    "cat /var/spool/cron/",
    "cat Containerfile",
    "cat file.txt",
    "cat file1 file2",
    "cat ~/.bash_logout",
    "cat ~/.bash_profile",
    "cat ~/.bashrc",
    "cat ~/.ssh/config",
    "cat ~/.vimrc",
    "systemctl cat"
  ],
  "cc": [
    "cc"
  ],
  "cd": [
    "cd -",
    "cd /",
    "cd /path/to/dir",
    "cd ~"
  ],
  "check-update": [
    "dnf check-update"
  ],
  "checking": [
    "Checking=no"
  ],
  "chmod": [
    "chmod",
    "chmod +t dir",
    "chmod +x script.sh",
    "chmod -R 755 dir/",
    "chmod 1755 dir",
    "chmod 2755 dir",
    "chmod 4755 file",
    "chmod 600 file",
    "chmod 600 ~/.ssh/aut",
    "chmod 644 file",
    "chmod 700 ~/.ssh/",
    "chmod 755 file",
    "chmod 777 file",
    "chmod a+r file",
    "chmod g+s dir",
    "chmod g-w file",
    "chmod o-r file",
    "chmod u+s file",
    "chmod u+x file",
    "chmod u=rwx,g=rx,o=r"
  ],
  "chown": [
    "chown",
    "chown -R user:group",
    "chown :group file",
    "chown user file",
    "chown user:group"
  ],
  "ci": [
    "cat -A file.txt",
    "cat -n file.txt",
    "cat file.txt",
    "cat file1 file2"
  ],
  "ciciel": [
    "w■a■ciciel)"
  ],
  "ciciela": [
    "w■a■ciciela"
  ],
  "cifs": [
    "grep cifs",
    "mount -t cifs"
  ],
  "clean": [
    "dnf clean all",
    "dnf clean metadata",
    "dnf clean packages"
  ],
  "cmd": [
    "cmd"
  ],
  "column": [
    "mount | column -t"
  ],
  "command": [
    "VAR=$(command)"
  ],
  "commit": [
    "podman commit"
  ],
  "complete": [
    "complete"
  ],
  "config-manager": [
    "dnf config-manager"
  ],
  "connection": [
    "nmcli connection",
    "nmcli connection add",
    "nmcli connection up"
  ],
  "connecttimeout": [
    "ConnectTimeout=10"
  ],
  "container": [
    "container",
    "podman container",
    "podman rm container",
    "podman top container"
  ],
  "containerfile": [
    "cat Containerfile"
  ],
  "continue": [
    "continue"
  ],
  "count": [
    "count=1000"
  ],
  "cp": [
    "cp --backup src dst",
    "cp -a src/ dst/",
    "cp -i src dst",
    "cp -p src dst",
    "cp -r src/ dst/",
    "cp -u src dst",
    "cp -v src dst",
    "cp source dest",
    "podman cp",
    "podman cp src"
  ],
  "create": [
    "podman pod create",
    "podman volume create"
  ],
  "cron": [
    "/etc/cron.daily",
    "atq",
    "batch",
    "cat /etc/anacrontab",
    "cat /etc/at.allow",
    "cat /etc/at.deny",
    "cat /etc/cron.allow",
    "cat /etc/cron.deny",
    "cat /etc/crontab",
    "cat /etc/systemd/sys",
    "cat /var/spool/cron/",
    "list-timers",
    "ls /etc/cron.d/",
    "ls /etc/cron.daily/",
    "ls /etc/cron.hourly/",
    "ls /etc/cron.weekly/",
    "myapp.timer",
    "run-parts",
    "systemd-run",
    "tem/myapp.timer",
    "timer-name.timer"
  ],
  "ctrl+b": [
    "Ctrl+b"
  ],
  "ctrl+c": [
    "Ctrl+C"
  ],
  "ctrl+d": [
    "Ctrl+D",
    "Ctrl+d"
  ],
  "ctrl+f": [
    "Ctrl+f"
  ],
  "ctrl+r": [
    "Ctrl+R",
    "Ctrl+r"
  ],
  "ctrl+u": [
    "Ctrl+u"
  ],
  "ctrl+v": [
    "Ctrl+v"
  ],
  "ctrl+z": [
    "Ctrl+Z"
  ],
  "curl": [
    "curl"
  ],
  "cw": [
    "cw"
  ],
  "czona": [
    "w■■czona"
  ],
  "c}.log": [
    "echo {a,b,c}.log"
  ],
  "d": [
    "D",
    "find / -type d -name"
  ],
  "d$": [
    "d$"
  ],
  "d+": [
    "grep -P '\\d+' file"
  ],
  "d0": [
    "d0"
  ],
  "daemon-reexec": [
    "daemon-reexec"
  ],
  "daemon-reload": [
    "daemon-reload"
  ],
  "danie": [
    "cat -A file.txt",
    "cat -n file.txt",
    "cat file.txt",
    "cat file1 file2"
  ],
  "danych": [
    "blkid",
    "dysków",
    "lsblk",
    "partprobe",
    "print"
  ],
  "date": [
    "date"
  ],
  "dd": [
    "dd"
  ],
  "default": [
    "ip route add default",
    "ip route del default"
  ],
  "del": [
    "ip addr del",
    "ip route del",
    "ip route del default"
  ],
  "delete": [
    "ip netns delete myns"
  ],
  "denied": [
    "grep 'denied' /var/l"
  ],
  "dest": [
    "cp source dest"
  ],
  "device": [
    "nmcli device show",
    "nmcli device status"
  ],
  "df": [
    "podman system df"
  ],
  "diagnostyka": [
    "--filename=/tmp/test",
    "--leak-check=full",
    "/var/log/sa/saDD",
    "9000",
    "PID",
    "bonnie++",
    "cat /etc/hostname",
    "cat /etc/hosts",
    "cat /etc/kdump.conf",
    "cat /etc/resolv.conf",
    "cat /etc/sysconfig/n",
    "cat /proc/PID/limits",
    "cat /proc/net/tcp",
    "cat /proc/net/udp",
    "cat /proc/sys/net/nf",
    "cmd",
    "count=1000",
    "curl",
    "established",
    "fio",
    "hostname",
    "ip -6 addr show",
    "ip -6 route show",
    "ip -s link show eth0",
    "ip addr",
    "ip addr add",
    "ip addr del",
    "ip addr show",
    "ip addr show eth0",
    "ip link set eth0 down",
    "ip link set eth0 mtu",
    "ip link set eth0 up",
    "ip link show",
    "ip neigh flush all",
    "ip neigh show",
    "ip route add",
    "ip route add default",
    "ip route del",
    "ip route del default",
    "ip route get 8.8.8.8",
    "ip route show",
    "kdump",
    "nmcli connection",
    "nmcli connection add",
    "nmcli connection up",
    "nmcli device show",
    "nmcli device status",
    "nmcli general",
    "nmcli radio wifi off",
    "nmtui",
    "procesami",
    "valgrind"
  ],
  "diff": [
    "podman diff"
  ],
  "dir": [
    "chmod +t dir",
    "chmod 1755 dir",
    "chmod 2755 dir",
    "chmod g+s dir"
  ],
  "dir/": [
    "chmod -R 755 dir/",
    "dir/",
    "ls -Z dir/",
    "ls -dZ dir/",
    "rm -r dir/",
    "rm -rf dir/"
  ],
  "dirname": [
    "dirname",
    "mkdir -m 755 dirname",
    "mkdir -v dirname",
    "mkdir dirname"
  ],
  "dirs": [
    "dirs"
  ],
  "disable": [
    "dnf module disable",
    "systemctl disable"
  ],
  "distro-sync": [
    "dnf distro-sync"
  ],
  "dmesg": [
    "dmesg"
  ],
  "dnf": [
    "dnf autoremove",
    "dnf check-update",
    "dnf clean all",
    "dnf clean metadata",
    "dnf clean packages",
    "dnf config-manager",
    "dnf distro-sync",
    "dnf downgrade",
    "dnf erase package",
    "dnf groupinfo 'Group",
    "dnf groupinstall",
    "dnf grouplist",
    "dnf groupremove",
    "dnf history",
    "dnf history info 5",
    "dnf history redo 5",
    "dnf history rollback",
    "dnf history undo 5",
    "dnf info package",
    "dnf install -y",
    "dnf install kernel",
    "dnf install package",
    "dnf list available",
    "dnf list extras",
    "dnf list installed",
    "dnf list obsoletes",
    "dnf list updates",
    "dnf makecache",
    "dnf module disable",
    "dnf module enable",
    "dnf module info",
    "dnf module install m",
    "dnf module list",
    "dnf module reset",
    "dnf provides",
    "dnf reinstall",
    "dnf remove",
    "dnf remove package",
    "dnf repoinfo repo-id",
    "dnf repolist",
    "dnf repolist all",
    "dnf search keyword",
    "dnf security update",
    "dnf update",
    "dnf update package",
    "dnf updateinfo list",
    "dnf upgrade",
    "dnf upgrade-minimal",
    "dnf whatprovides"
  ],
  "dnf/rpm": [
    "Name'",
    "aktualizacjami",
    "dnf autoremove",
    "dnf check-update",
    "dnf clean all",
    "dnf clean metadata",
    "dnf clean packages",
    "dnf config-manager",
    "dnf distro-sync",
    "dnf downgrade",
    "dnf erase package",
    "dnf groupinfo 'Group",
    "dnf groupinstall",
    "dnf grouplist",
    "dnf groupremove",
    "dnf history",
    "dnf history info 5",
    "dnf history redo 5",
    "dnf history rollback",
    "dnf history undo 5",
    "dnf info package",
    "dnf install -y",
    "dnf install package",
    "dnf list available",
    "dnf list extras",
    "dnf list installed",
    "dnf list obsoletes",
    "dnf list updates",
    "dnf makecache",
    "dnf module disable",
    "dnf module enable",
    "dnf module info",
    "dnf module install m",
    "dnf module list",
    "dnf module reset",
    "dnf provides",
    "dnf reinstall",
    "dnf remove package",
    "dnf repoinfo repo-id",
    "dnf repolist",
    "dnf repolist all",
    "dnf search keyword",
    "dnf security update",
    "dnf update",
    "dnf update package",
    "dnf updateinfo list",
    "dnf upgrade",
    "dnf upgrade-minimal",
    "dnf whatprovides",
    "package",
    "rpm --import",
    "rpm -Fvh package.rpm",
    "rpm -K package.rpm",
    "rpm -Uvh package.rpm",
    "rpm -V package",
    "rpm -Va",
    "rpm -e package",
    "rpm -ivh package.rpm",
    "rpm -q --changelog",
    "rpm -q --scripts",
    "rpm -qR package",
    "rpm -qa",
    "rpm -qc package",
    "rpm -qd package",
    "rpm -qf",
    "rpm -qi package",
    "rpm -qip package.rpm",
    "rpm -ql package",
    "rpm -qp --scripts",
    "subscription-manager"
  ],
  "dniach": [
    "dniach"
  ],
  "do": [
    "do"
  ],
  "docker": [
    "usermod -aG docker"
  ],
  "dodatkowe": [
    "--zone=drop",
    "/tmp/cap.pcap",
    "alternatives",
    "authselect",
    "bash",
    "cat /etc/crypto-poli",
    "cat /sys/fs/cgroup/m",
    "emory/mygroup/memory",
    "fips-mode-setup",
    "ip netns add myns",
    "ip netns delete myns",
    "ip netns exec myns",
    "ip netns list",
    "ls /sys/fs/cgroup/",
    "memory:mygroup",
    "mygroup",
    "ntsysv",
    "scap-workbench",
    "systemd-cgls",
    "systemd-cgtop",
    "t_in_bytes=512M",
    "update-alternatives",
    "update-crypto-polici",
    "wireshark"
  ],
  "done": [
    "done"
  ],
  "dost": [
    "4096",
    "8080:localhost:80",
    "Checking=no",
    "ConnectTimeout=10",
    "cat ~/.ssh/config",
    "chmod 600 ~/.ssh/aut",
    "chmod 700 ~/.ssh/",
    "ed25519",
    "horized_keys",
    "ntication=no",
    "rsync -avz",
    "rsync -avz -e ssh",
    "scp",
    "ssh -A user@host",
    "ssh -D 1080",
    "ssh -J jumphost",
    "ssh -L",
    "ssh -N -f -L",
    "ssh -R",
    "ssh -X user@host",
    "ssh -i",
    "ssh -o",
    "ssh -o BatchMode=yes",
    "ssh -o PasswordAuthe",
    "ssh -o PreferredAuth",
    "ssh -o StrictHostKey",
    "ssh -p 2222",
    "ssh -t user@host",
    "ssh -v user@host",
    "ssh -vvv user@host",
    "ssh user@hostname",
    "ssh-add",
    "ssh-copy-id",
    "user@host",
    "user@hostname",
    "~/.ssh/id_rsa",
    "~/.ssh/id_rsa.pub",
    "~/.ssh/key.pem",
    "~/.ssh/mykey"
  ],
  "down": [
    "ip link set eth0 down"
  ],
  "downgrade": [
    "dnf downgrade"
  ],
  "drop": [
    "--zone=drop"
  ],
  "dst": [
    "cp --backup src dst",
    "cp -i src dst",
    "cp -p src dst",
    "cp -u src dst",
    "cp -v src dst",
    "dst:tag"
  ],
  "dst/": [
    "cp -a src/ dst/",
    "cp -r src/ dst/",
    "rsync -av src/ dst/",
    "rsync -n src/ dst/"
  ],
  "dw": [
    "dw"
  ],
  "dyskami": [
    "--raid-devices=2",
    "--scan",
    "/dev/md0",
    "/dev/sdd",
    "cat /etc/mdadm.conf",
    "cat /proc/mdstat",
    "mdadm"
  ],
  "dyski": [
    "blkid",
    "dysków",
    "lsblk",
    "partprobe",
    "print"
  ],
  "dysków": [
    "dysków"
  ],
  "dzanie": [
    "--raid-devices=2",
    "--scan",
    "--type=service",
    "--vacuum-size=500M",
    "/dev/md0",
    "/dev/sdd",
    "Ctrl+C",
    "Ctrl+D",
    "Ctrl+Z",
    "Name'",
    "aktualizacjami",
    "cat /etc/group",
    "cat /etc/gshadow",
    "cat /etc/mdadm.conf",
    "cat /etc/passwd",
    "cat /etc/shadow",
    "cat /proc/PID/maps",
    "cat /proc/PID/status",
    "cat /proc/loadavg",
    "cat /proc/mdstat",
    "cat /proc/meminfo",
    "daemon-reexec",
    "daemon-reload",
    "dnf autoremove",
    "dnf check-update",
    "dnf clean all",
    "dnf clean metadata",
    "dnf clean packages",
    "dnf config-manager",
    "dnf distro-sync",
    "dnf downgrade",
    "dnf erase package",
    "dnf groupinfo 'Group",
    "dnf groupinstall",
    "dnf grouplist",
    "dnf groupremove",
    "dnf history",
    "dnf history info 5",
    "dnf history redo 5",
    "dnf history rollback",
    "dnf history undo 5",
    "dnf info package",
    "dnf install -y",
    "dnf install package",
    "dnf list available",
    "dnf list extras",
    "dnf list installed",
    "dnf list obsoletes",
    "dnf list updates",
    "dnf makecache",
    "dnf module disable",
    "dnf module enable",
    "dnf module info",
    "dnf module install m",
    "dnf module list",
    "dnf module reset",
    "dnf provides",
    "dnf reinstall",
    "dnf remove package",
    "dnf repoinfo repo-id",
    "dnf repolist",
    "dnf repolist all",
    "dnf search keyword",
    "dnf security update",
    "dnf update",
    "dnf update package",
    "dnf updateinfo list",
    "dnf upgrade",
    "dnf upgrade-minimal",
    "dnf whatprovides",
    "dniach",
    "emergency.target",
    "get-default",
    "group",
    "grpck",
    "hostnamectl",
    "htop",
    "id",
    "jobs",
    "journalctl",
    "journalctl --since",
    "journalctl --until",
    "journalctl -b",
    "journalctl -b -1",
    "journalctl -f",
    "journalctl -f -u",
    "journalctl -k",
    "journalctl -n 50",
    "journalctl -o json",
    "journalctl -p",
    "journalctl -p err",
    "journalctl -u",
    "last",
    "lastb",
    "lastlog",
    "list-dependencies",
    "list-unit-files",
    "localectl",
    "loginctl",
    "lslogins",
    "lsof",
    "mdadm",
    "package",
    "ps",
    "pstree",
    "pwck",
    "rescue.target",
    "rpm --import",
    "rpm -Fvh package.rpm",
    "rpm -K package.rpm",
    "rpm -Uvh package.rpm",
    "rpm -V package",
    "rpm -Va",
    "rpm -e package",
    "rpm -ivh package.rpm",
    "rpm -q --changelog",
    "rpm -q --scripts",
    "rpm -qR package",
    "rpm -qa",
    "rpm -qc package",
    "rpm -qd package",
    "rpm -qf",
    "rpm -qi package",
    "rpm -qip package.rpm",
    "rpm -ql package",
    "rpm -qp --scripts",
    "service",
    "set-default",
    "subscription-manager",
    "systemctl",
    "systemctl --user",
    "systemctl cat",
    "systemctl disable",
    "systemctl edit",
    "systemctl enable",
    "systemctl halt",
    "systemctl hibernate",
    "systemctl is-active",
    "systemctl is-enabled",
    "systemctl is-failed",
    "systemctl isolate",
    "systemctl list-units",
    "systemctl mask",
    "systemctl poweroff",
    "systemctl reboot",
    "systemctl reload",
    "systemctl restart",
    "systemctl show",
    "systemctl show -p",
    "systemctl start",
    "systemctl status",
    "systemctl stop",
    "systemctl suspend",
    "systemctl unmask",
    "systemd-analyze",
    "timedatectl",
    "top",
    "trwa■e)",
    "uptime",
    "user",
    "useradd -G g1,g2",
    "useradd -M user",
    "useradd -N user",
    "useradd -c 'Imi■",
    "useradd -d",
    "useradd -e",
    "useradd -f 30 user",
    "useradd -g group",
    "useradd -m -s",
    "useradd -m username",
    "useradd -r sysuser",
    "useradd -u 1500 user",
    "useradd username",
    "usermod -G g1,g2",
    "usermod -L user",
    "usermod -U user",
    "usermod -aG docker",
    "usermod -aG group",
    "usermod -aG wheel",
    "usermod -c 'Nowy",
    "usermod -d /new/home",
    "usermod -e",
    "usermod -e '' user",
    "usermod -g group",
    "usermod -l newname",
    "usermod -s /bin/zsh",
    "usermod -u 1600 user",
    "u■ytkownika",
    "vigr",
    "vipw",
    "visudo",
    "w",
    "wait",
    "who",
    "whoami",
    "zalogowanego"
  ],
  "dzia": [
    "--filename=/tmp/test",
    "--leak-check=full",
    "--zone=drop",
    "/tmp/cap.pcap",
    "/var/log/sa/saDD",
    "100))",
    "32",
    "alternatives",
    "authselect",
    "bash",
    "bonnie++",
    "cat /etc/chrony.conf",
    "cat /etc/crypto-poli",
    "cat /etc/kdump.conf",
    "cat /proc/PID/limits",
    "cat /proc/net/tcp",
    "cat /proc/net/udp",
    "cat /proc/sys/net/nf",
    "cat /sys/fs/cgroup/m",
    "cmd",
    "count=1000",
    "date",
    "echo $((RANDOM %",
    "echo '3.14 * 2' | bc",
    "echo file{1..3}.txt",
    "echo {1..5}",
    "echo {a,b,c}.log",
    "emory/mygroup/memory",
    "fio",
    "fips-mode-setup",
    "gpg",
    "hwclock",
    "ip -s link show eth0",
    "ip netns add myns",
    "ip netns delete myns",
    "ip netns exec myns",
    "ip netns list",
    "kdump",
    "ls /sys/fs/cgroup/",
    "memory:mygroup",
    "mygroup",
    "ntsysv",
    "scap-workbench",
    "systemd-cgls",
    "systemd-cgtop",
    "t_in_bytes=512M",
    "update-alternatives",
    "update-crypto-polici",
    "valgrind",
    "wireshark"
  ],
  "e": [
    "ARRAY+=('e')",
    "e",
    "trwa■e)"
  ],
  "e-port": [
    "e-port=8080/tcp"
  ],
  "e-service": [
    "e-service=http"
  ],
  "echo": [
    "echo \"Value: $VAR\"",
    "echo $!",
    "echo $#",
    "echo $$",
    "echo $((RANDOM %",
    "echo $*",
    "echo $0",
    "echo $?",
    "echo $@",
    "echo $BASH_VERSION",
    "echo $HISTFILE",
    "echo $HISTFILESIZE",
    "echo $HISTSIZE",
    "echo $HOME",
    "echo $OLDPWD",
    "echo $PATH",
    "echo $PS1",
    "echo $PWD",
    "echo $SHELL",
    "echo $VARIABLE",
    "echo ${#ARRAY[@]}",
    "echo ${ARRAY[0]}",
    "echo ${ARRAY[@]}",
    "echo ${MAP[k1]}",
    "echo '3.14 * 2' | bc",
    "echo 'module_name' >",
    "echo 'net.ipv4.ip_fo",
    "echo file{1..3}.txt",
    "echo {1..5}",
    "echo {a,b,c}.log"
  ],
  "ed25519": [
    "ed25519"
  ],
  "edit": [
    "systemctl edit"
  ],
  "edytor": [
    "$",
    "*",
    "/pattern",
    "0",
    "10G",
    "5dd",
    "5yy",
    "?pattern",
    "A",
    "Ctrl+b",
    "Ctrl+d",
    "Ctrl+f",
    "Ctrl+r",
    "Ctrl+u",
    "Ctrl+v",
    "D",
    "Esc",
    "G",
    "I",
    "N",
    "O",
    "P",
    "R",
    "V",
    "X",
    "ZQ",
    "ZZ",
    "a",
    "b",
    "c$",
    "cat ~/.vimrc",
    "cc",
    "cw",
    "d$",
    "d0",
    "dd",
    "dw",
    "e",
    "gT",
    "gU",
    "gg",
    "gt",
    "gu",
    "i",
    "n",
    "o",
    "p",
    "q",
    "qa",
    "r",
    "u",
    "v",
    "vim +/pattern",
    "vim +10 file.txt",
    "vim -R file.txt",
    "vim -d file1 file2",
    "vim -u NONE file.txt",
    "vim file.txt",
    "x",
    "yy"
  ],
  "efault-zone": [
    "efault-zone=trusted"
  ],
  "else": [
    "else"
  ],
  "emergency": [
    "systemctl emergency"
  ],
  "emergency.target": [
    "emergency.target"
  ],
  "emory/mygroup/memory": [
    "emory/mygroup/memory"
  ],
  "enable": [
    "dnf module enable",
    "systemctl enable"
  ],
  "end{print": [
    "awk 'END{print NR}'"
  ],
  "env": [
    "env"
  ],
  "erase": [
    "dnf erase package"
  ],
  "err": [
    "--level=err,warn",
    "journalctl -p err"
  ],
  "esac": [
    "esac"
  ],
  "esc": [
    "Esc"
  ],
  "established": [
    "established"
  ],
  "eth0": [
    "ip -s link show eth0",
    "ip addr show eth0",
    "ip link set eth0 down",
    "ip link set eth0 mtu",
    "ip link set eth0 up"
  ],
  "exec": [
    "ip netns exec myns",
    "podman exec",
    "podman exec -it",
    "podman exec -u root"
  ],
  "exportfs": [
    "exportfs"
  ],
  "ext4": [
    "mount -t ext4"
  ],
  "extras": [
    "dnf list extras"
  ],
  "f": [
    "find . -type f -name",
    "find . -type f -newer",
    "find / -type f -name"
  ],
  "failed": [
    "grep 'Failed"
  ],
  "false": [
    "false"
  ],
  "fcontext": [
    "semanage fcontext -a",
    "semanage fcontext -d",
    "semanage fcontext -l",
    "semanage fcontext -m"
  ],
  "fi": [
    "fi"
  ],
  "file": [
    "awk '/pattern/' file",
    "awk 'NR==5' file",
    "chmod 4755 file",
    "chmod 600 file",
    "chmod 644 file",
    "chmod 755 file",
    "chmod 777 file",
    "chmod a+r file",
    "chmod g-w file",
    "chmod o-r file",
    "chmod u+s file",
    "chmod u+x file",
    "chown :group file",
    "chown user file",
    "file",
    "grep 'pattern' file",
    "grep -P '\\d+' file",
    "grep -w 'word' file",
    "ls -Z file",
    "rm -i file",
    "rm -v file"
  ],
  "file.tar": [
    "file.tar"
  ],
  "file.txt": [
    "cat -A file.txt",
    "cat -n file.txt",
    "cat file.txt",
    "rm -f file.txt",
    "rm file.txt",
    "touch file.txt",
    "vim +10 file.txt",
    "vim -R file.txt",
    "vim -u NONE file.txt",
    "vim file.txt"
  ],
  "file1": [
    "cat file1 file2",
    "vim -d file1 file2"
  ],
  "file2": [
    "cat file1 file2",
    "vim -d file1 file2"
  ],
  "file{1..3}.txt": [
    "echo file{1..3}.txt"
  ],
  "filtrowanie": [
    "/dir",
    "awk '/pattern/' file",
    "awk 'END{print NR}'",
    "awk 'NR==5' file",
    "awk 'NR>=5 &&",
    "awk '{print $1}'",
    "awk '{print $NF}'",
    "awk '{print NF}'",
    "awk '{sum+=$1}",
    "awk -F: '{print $1}'",
    "awk -v FS=':'",
    "file",
    "grep",
    "grep 'pattern' file",
    "grep -A 3 'pattern'",
    "grep -B 3 'pattern'",
    "grep -C 3 'pattern'",
    "grep -E 'pat1|pat2'",
    "grep -F 'literal'",
    "grep -P '\\d+' file",
    "grep -c 'pattern'",
    "grep -i 'pattern'",
    "grep -l 'pattern'",
    "grep -m 5 'pattern'",
    "grep -n 'pattern'",
    "grep -o 'pattern'",
    "grep -q 'pattern'",
    "grep -r 'pattern'",
    "grep -v 'pattern'",
    "grep -w 'word' file"
  ],
  "find": [
    "find . ! -name",
    "find . -atime -1",
    "find . -ctime -1",
    "find . -empty",
    "find . -gid 1000",
    "find . -group",
    "find . -iname",
    "find . -links +1",
    "find . -maxdepth 2",
    "find . -mindepth 2",
    "find . -mmin -60",
    "find . -mount -name",
    "find . -mtime +30",
    "find . -mtime -7",
    "find . -name",
    "find . -name '*.log'",
    "find . -name '*.py'",
    "find . -name '*.tmp'",
    "find . -name '*.txt'",
    "find . -newer",
    "find . -nogroup",
    "find . -nouser",
    "find . -perm -1000",
    "find . -perm -2000",
    "find . -perm -4000",
    "find . -perm -644",
    "find . -perm /644",
    "find . -perm 644",
    "find . -size +100M",
    "find . -size +1G",
    "find . -size -10k",
    "find . -size 512c",
    "find . -type f -name",
    "find . -type f -newer",
    "find . -uid 1000",
    "find . -user",
    "find . -xdev -name",
    "find / -inum 12345",
    "find / -name",
    "find / -perm -2000",
    "find / -perm -4000",
    "find / -perm -o+w",
    "find / -type b",
    "find / -type c",
    "find / -type d -name",
    "find / -type f -name",
    "find / -type l",
    "find /path -print |",
    "find /tmp -mtime +7"
  ],
  "findmnt": [
    "findmnt"
  ],
  "fio": [
    "fio"
  ],
  "fips-mode-setup": [
    "fips-mode-setup"
  ],
  "firewall-cmd": [
    "firewall-cmd",
    "firewall-cmd --add-f",
    "firewall-cmd --add-p",
    "firewall-cmd --add-r",
    "firewall-cmd --add-s",
    "firewall-cmd --remov",
    "firewall-cmd --runti",
    "firewall-cmd --set-d",
    "firewall-cmd --state"
  ],
  "firewalld": [
    "--add-port=8080/tcp",
    "--add-service=http",
    "--add-service=https",
    "--complete-reload",
    "--get-active-zones",
    "--get-default-zone",
    "--get-zones",
    "--list-all",
    "--list-ports",
    "--list-rich-rules",
    "--list-services",
    "--zone=public",
    "e-port=8080/tcp",
    "e-service=http",
    "efault-zone=trusted",
    "firewall-cmd",
    "firewall-cmd --add-f",
    "firewall-cmd --add-p",
    "firewall-cmd --add-r",
    "firewall-cmd --remov",
    "firewall-cmd --runti",
    "firewall-cmd --set-d",
    "firewall-cmd --state",
    "firewalld",
    "w■■czona"
  ],
  "flush": [
    "ip neigh flush all"
  ],
  "fs": [
    "awk -v FS=':'"
  ],
  "full": [
    "--leak-check=full"
  ],
  "g": [
    "G",
    "chmod u=rwx,g=rx,o=r"
  ],
  "g+s": [
    "chmod g+s dir"
  ],
  "g-w": [
    "chmod g-w file"
  ],
  "g1": [
    "useradd -G g1,g2",
    "usermod -G g1,g2"
  ],
  "g2": [
    "useradd -G g1,g2",
    "usermod -G g1,g2"
  ],
  "general": [
    "nmcli general"
  ],
  "generate": [
    "podman generate",
    "podman generate kube"
  ],
  "get": [
    "ip route get 8.8.8.8"
  ],
  "get-default": [
    "get-default"
  ],
  "getenforce": [
    "getenforce"
  ],
  "gg": [
    "gg"
  ],
  "gpg": [
    "gpg"
  ],
  "grep": [
    "grep",
    "grep 'Accepted'",
    "grep 'Failed",
    "grep 'denied' /var/l",
    "grep 'pattern' file",
    "grep -A 3 'pattern'",
    "grep -B 3 'pattern'",
    "grep -C 3 'pattern'",
    "grep -E 'pat1|pat2'",
    "grep -F 'literal'",
    "grep -P '\\d+' file",
    "grep -c 'pattern'",
    "grep -i 'pattern'",
    "grep -l 'pattern'",
    "grep -m 5 'pattern'",
    "grep -n 'pattern'",
    "grep -o 'pattern'",
    "grep -q 'pattern'",
    "grep -r 'pattern'",
    "grep -v 'pattern'",
    "grep -w 'word' file",
    "grep cifs"
  ],
  "group": [
    "chown -R user:group",
    "chown :group file",
    "chown user:group",
    "dnf groupinfo 'Group",
    "group",
    "useradd -g group",
    "usermod -aG group",
    "usermod -g group"
  ],
  "groupinfo": [
    "dnf groupinfo 'Group"
  ],
  "groupinstall": [
    "dnf groupinstall"
  ],
  "grouplist": [
    "dnf grouplist"
  ],
  "groupremove": [
    "dnf groupremove"
  ],
  "grpck": [
    "grpck"
  ],
  "grub": [
    "--target=x86_64-efi",
    "/boot/grub2/grub.cfg",
    "/boot/initramfs*",
    "GRUB",
    "cat /etc/modprobe.d/",
    "cat /etc/sysctl.conf",
    "cat /etc/sysctl.d/",
    "cat /proc/cmdline",
    "cat /proc/sys/kernel",
    "cat /proc/version",
    "dnf install kernel",
    "dnf remove",
    "echo 'module_name' >",
    "echo 'net.ipv4.ip_fo",
    "grub2-install",
    "grub2-set-default",
    "halt",
    "insmod",
    "kernel",
    "ls /boot/",
    "ls /boot/grub2/",
    "lsmod",
    "poweroff",
    "reboot",
    "rpm -qa kernel",
    "sync",
    "sysctl",
    "systemctl emergency",
    "systemctl rescue"
  ],
  "grub2-install": [
    "grub2-install"
  ],
  "grub2-set-default": [
    "grub2-set-default"
  ],
  "grupami": [
    "group",
    "usermod -aG docker",
    "usermod -aG wheel"
  ],
  "gt": [
    "gT",
    "gt"
  ],
  "gu": [
    "gU",
    "gu"
  ],
  "halt": [
    "halt",
    "systemctl halt"
  ],
  "harmonogramowanie": [
    "/etc/cron.daily",
    "atq",
    "batch",
    "cat /etc/anacrontab",
    "cat /etc/at.allow",
    "cat /etc/at.deny",
    "cat /etc/cron.allow",
    "cat /etc/cron.deny",
    "cat /etc/crontab",
    "cat /etc/systemd/sys",
    "cat /var/spool/cron/",
    "list-timers",
    "ls /etc/cron.d/",
    "ls /etc/cron.daily/",
    "ls /etc/cron.hourly/",
    "ls /etc/cron.weekly/",
    "myapp.timer",
    "run-parts",
    "systemd-run",
    "tem/myapp.timer",
    "timer-name.timer"
  ],
  "hash": [
    "hash"
  ],
  "head": [
    "ls /etc | head -20"
  ],
  "hibernate": [
    "systemctl hibernate"
  ],
  "history": [
    "dnf history",
    "dnf history info 5",
    "dnf history redo 5",
    "dnf history rollback",
    "dnf history undo 5",
    "history",
    "podman image history"
  ],
  "horized_keys": [
    "horized_keys"
  ],
  "host": [
    "ssh -A user@host",
    "ssh -X user@host",
    "ssh -t user@host",
    "ssh -v user@host",
    "ssh -vvv user@host",
    "user@host"
  ],
  "hostname": [
    "hostname",
    "ssh user@hostname",
    "user@hostname"
  ],
  "hostnamectl": [
    "hostnamectl"
  ],
  "htop": [
    "htop"
  ],
  "http": [
    "--add-service=http",
    "e-service=http"
  ],
  "httpd_c": [
    "setsebool -P httpd_c"
  ],
  "httpd_can_": [
    "setsebool httpd_can_"
  ],
  "httpd_sys_content_t": [
    "httpd_sys_content_t"
  ],
  "https": [
    "--add-service=https"
  ],
  "hwclock": [
    "hwclock"
  ],
  "i": [
    "--disk-usage",
    "--filename=/tmp/test",
    "--leak-check=full",
    "--level=err,warn",
    "--newer-mtime='2023-",
    "--target=x86_64-efi",
    "--type=service",
    "--vacuum-size=500M",
    "//server",
    "/boot/grub2/grub.cfg",
    "/boot/initramfs*",
    "/dev/sdb1",
    "/dir",
    "/etc/cron.daily",
    "/mnt",
    "/var/log/messages",
    "/var/log/sa/saDD",
    "4096",
    "8080:localhost:80",
    "9000",
    "Checking=no",
    "ConnectTimeout=10",
    "Ctrl+R",
    "GRUB",
    "I",
    "PID",
    "alias",
    "alias ll='ls -alh'",
    "archive.tar.bz2",
    "archive.tar.gz",
    "archive.tar.xz",
    "atq",
    "aureport",
    "awk '/pattern/' file",
    "awk 'END{print NR}'",
    "awk 'NR==5' file",
    "awk 'NR>=5 &&",
    "awk '{print $1}'",
    "awk '{print $NF}'",
    "awk '{print NF}'",
    "awk '{sum+=$1}",
    "awk -F: '{print $1}'",
    "awk -v FS=':'",
    "batch",
    "blkid",
    "bonnie++",
    "cat /etc/anacrontab",
    "cat /etc/at.allow",
    "cat /etc/at.deny",
    "cat /etc/audit/audit",
    "cat /etc/auto.master",
    "cat /etc/auto.misc",
    "cat /etc/bashrc",
    "cat /etc/cron.allow",
    "cat /etc/cron.deny",
    "cat /etc/crontab",
    "cat /etc/exports",
    "cat /etc/fstab",
    "cat /etc/fstab |",
    "cat /etc/hostname",
    "cat /etc/hosts",
    "cat /etc/kdump.conf",
    "cat /etc/modprobe.d/",
    "cat /etc/profile",
    "cat /etc/resolv.conf",
    "cat /etc/sysconfig/n",
    "cat /etc/sysctl.conf",
    "cat /etc/sysctl.d/",
    "cat /etc/systemd/sys",
    "cat /proc/PID/limits",
    "cat /proc/cmdline",
    "cat /proc/mounts",
    "cat /proc/net/tcp",
    "cat /proc/net/udp",
    "cat /proc/sys/kernel",
    "cat /proc/sys/net/nf",
    "cat /proc/version",
    "cat /var/log/cron",
    "cat /var/log/maillog",
    "cat /var/log/secure",
    "cat /var/spool/cron/",
    "cat ~/.bash_logout",
    "cat ~/.bash_profile",
    "cat ~/.bashrc",
    "cat ~/.ssh/config",
    "chmod",
    "chmod +t dir",
    "chmod -R 755 dir/",
    "chmod 1755 dir",
    "chmod 2755 dir",
    "chmod 4755 file",
    "chmod 600 file",
    "chmod 600 ~/.ssh/aut",
    "chmod 644 file",
    "chmod 700 ~/.ssh/",
    "chmod 755 file",
    "chmod 777 file",
    "chmod a+r file",
    "chmod g+s dir",
    "chmod g-w file",
    "chmod o-r file",
    "chmod u+s file",
    "chmod u+x file",
    "chmod u=rwx,g=rx,o=r",
    "chown",
    "chown -R user:group",
    "chown :group file",
    "chown user file",
    "chown user:group",
    "cmd",
    "complete",
    "count=1000",
    "cp --backup src dst",
    "cp -a src/ dst/",
    "cp -i src dst",
    "cp -p src dst",
    "cp -r src/ dst/",
    "cp -u src dst",
    "cp -v src dst",
    "cp source dest",
    "curl",
    "daemon-reexec",
    "daemon-reload",
    "dir/",
    "dmesg",
    "dnf install kernel",
    "dnf remove",
    "dysków",
    "echo $!",
    "echo $#",
    "echo $$",
    "echo $*",
    "echo $0",
    "echo $?",
    "echo $@",
    "echo $BASH_VERSION",
    "echo $HISTFILE",
    "echo $HISTFILESIZE",
    "echo $HISTSIZE",
    "echo $PS1",
    "echo $SHELL",
    "echo $VARIABLE",
    "echo ${#ARRAY[@]}",
    "echo ${ARRAY[0]}",
    "echo ${ARRAY[@]}",
    "echo 'module_name' >",
    "echo 'net.ipv4.ip_fo",
    "ed25519",
    "emergency.target",
    "env",
    "established",
    "exportfs",
    "false",
    "file",
    "find / -perm -2000",
    "find / -perm -4000",
    "find / -perm -o+w",
    "find /path -print |",
    "findmnt",
    "fio",
    "firewall-cmd --add-s",
    "get-default",
    "grep",
    "grep 'Accepted'",
    "grep 'Failed",
    "grep 'pattern' file",
    "grep -A 3 'pattern'",
    "grep -B 3 'pattern'",
    "grep -C 3 'pattern'",
    "grep -E 'pat1|pat2'",
    "grep -F 'literal'",
    "grep -P '\\d+' file",
    "grep -c 'pattern'",
    "grep -i 'pattern'",
    "grep -l 'pattern'",
    "grep -m 5 'pattern'",
    "grep -n 'pattern'",
    "grep -o 'pattern'",
    "grep -q 'pattern'",
    "grep -r 'pattern'",
    "grep -v 'pattern'",
    "grep -w 'word' file",
    "grep cifs",
    "grub2-install",
    "grub2-set-default",
    "halt",
    "hash",
    "history",
    "horized_keys",
    "hostname",
    "hostnamectl",
    "i",
    "insmod",
    "ip -6 addr show",
    "ip -6 route show",
    "ip -s link show eth0",
    "ip addr",
    "ip addr add",
    "ip addr del",
    "ip addr show",
    "ip addr show eth0",
    "ip link set eth0 down",
    "ip link set eth0 mtu",
    "ip link set eth0 up",
    "ip link show",
    "ip neigh flush all",
    "ip neigh show",
    "ip route add",
    "ip route add default",
    "ip route del",
    "ip route del default",
    "ip route get 8.8.8.8",
    "ip route show",
    "journalctl",
    "journalctl --since",
    "journalctl --until",
    "journalctl -b",
    "journalctl -b -1",
    "journalctl -f",
    "journalctl -f -u",
    "journalctl -k",
    "journalctl -n 50",
    "journalctl -o",
    "journalctl -o json",
    "journalctl -p",
    "journalctl -p err",
    "journalctl -u",
    "journalctl -u sshd",
    "journalctl -xe",
    "katalogu",
    "kdump",
    "kernel",
    "list-dependencies",
    "list-timers",
    "list-unit-files",
    "localectl",
    "loginctl",
    "ls -Z file",
    "ls /boot/",
    "ls /boot/grub2/",
    "ls /etc/cron.d/",
    "ls /etc/cron.daily/",
    "ls /etc/cron.hourly/",
    "ls /etc/cron.weekly/",
    "ls /etc/logrotate.d/",
    "ls /etc/profile.d/",
    "ls /mnt/nfs/share",
    "lsblk",
    "lsmod",
    "mkdir -m 755 dirname",
    "mkdir -p a/b/c",
    "mkdir -v dirname",
    "mkdir dirname",
    "montowania",
    "mount -a",
    "mount -o",
    "mount -o remount,ro",
    "mount -o remount,rw",
    "mount -o ro",
    "mount -o ro,soft",
    "mount -o rw,noexec",
    "mount -t cifs",
    "mount -t ext4",
    "mount -t nfs",
    "mount -t nfs4",
    "mount -t xfs",
    "mount /dev/sdb1 /mnt",
    "mount LABEL=mylabel",
    "mount UUID=xxx /mnt",
    "mount | column -t",
    "myapp.timer",
    "nadpisaniem",
    "newfile",
    "nfs-server",
    "nfsstat",
    "nmcli connection",
    "nmcli connection add",
    "nmcli connection up",
    "nmcli device show",
    "nmcli device status",
    "nmcli general",
    "nmcli radio wifi off",
    "nmtui",
    "nosuid,noexec",
    "ntication=no",
    "partprobe",
    "poweroff",
    "print",
    "printenv",
    "procesami",
    "reboot",
    "rescue.target",
    "rm -f file.txt",
    "rm -i file",
    "rm -r dir/",
    "rm -rf dir/",
    "rm -v file",
    "rm file.txt",
    "rpm -qa kernel",
    "rsync",
    "rsync --delete src/",
    "rsync -av src/ dst/",
    "rsync -avz",
    "rsync -avz -e ssh",
    "rsync -avz src/",
    "rsync -n src/ dst/",
    "run-parts",
    "scp",
    "server:/share",
    "service",
    "set",
    "set-default",
    "smbclient",
    "source",
    "ssh -A user@host",
    "ssh -D 1080",
    "ssh -J jumphost",
    "ssh -L",
    "ssh -N -f -L",
    "ssh -R",
    "ssh -X user@host",
    "ssh -i",
    "ssh -o",
    "ssh -o BatchMode=yes",
    "ssh -o PasswordAuthe",
    "ssh -o PreferredAuth",
    "ssh -o StrictHostKey",
    "ssh -p 2222",
    "ssh -t user@host",
    "ssh -v user@host",
    "ssh -vvv user@host",
    "ssh user@hostname",
    "ssh-add",
    "ssh-copy-id",
    "sync",
    "sysctl",
    "systemctl",
    "systemctl --user",
    "systemctl cat",
    "systemctl disable",
    "systemctl edit",
    "systemctl emergency",
    "systemctl enable",
    "systemctl halt",
    "systemctl hibernate",
    "systemctl is-active",
    "systemctl is-enabled",
    "systemctl is-failed",
    "systemctl isolate",
    "systemctl list-units",
    "systemctl mask",
    "systemctl poweroff",
    "systemctl reboot",
    "systemctl reload",
    "systemctl rescue",
    "systemctl restart",
    "systemctl show",
    "systemctl show -p",
    "systemctl start",
    "systemctl status",
    "systemctl stop",
    "systemctl suspend",
    "systemctl unmask",
    "systemd-analyze",
    "systemd-run",
    "tar",
    "tar --delete -f",
    "tar --exclude-vcs",
    "tar -cvJf",
    "tar -cvf archive.tar",
    "tar -cvjf",
    "tar -cvzf",
    "tar -czf - /path |",
    "tar -czf arch.tar.gz",
    "tar -rvf archive.tar",
    "tar -tvf archive.tar",
    "tar -tvzf",
    "tar -uvf archive.tar",
    "tar -xvJf",
    "tar -xvf archive.tar",
    "tar -xvjf",
    "tar -xvzf",
    "tem/myapp.timer",
    "testparm",
    "timedatectl",
    "timer-name.timer",
    "touch -d",
    "touch -t",
    "touch file.txt",
    "true",
    "udit.log",
    "umask",
    "user@host",
    "user@hostname",
    "valgrind",
    "w■a■ciciel)",
    "w■a■ciciela",
    "~/.ssh/id_rsa",
    "~/.ssh/id_rsa.pub",
    "~/.ssh/key.pem",
    "~/.ssh/mykey"
  ],
  "id": [
    "id"
  ],
  "image": [
    "image",
    "image:tag",
    "podman image history",
    "podman image inspect",
    "podman image prune",
    "podman rmi -f image",
    "podman rmi image",
    "podman run -d image",
    "podman run -it image",
    "podman run image",
    "podman save image -o"
  ],
  "images": [
    "podman images",
    "podman images -a"
  ],
  "imi": [
    "useradd -c 'Imi■"
  ],
  "info": [
    "dnf history info 5",
    "dnf info package",
    "dnf module info",
    "podman info"
  ],
  "informacje": [
    "baseboard",
    "cat /etc/os-release",
    "cat /proc/cpuinfo",
    "cat /proc/uptime",
    "cat /sys/block/sda/q",
    "cat /sys/class/dmi/i",
    "iostat",
    "lscpu",
    "lshw",
    "lsmem",
    "lsnuma",
    "lspci",
    "lsusb",
    "nproc",
    "sensors",
    "sensors-detect",
    "vmstat"
  ],
  "init": [
    "podman machine init"
  ],
  "insmod": [
    "insmod"
  ],
  "inspect": [
    "podman image inspect",
    "podman inspect",
    "podman inspect -f",
    "podman pod inspect"
  ],
  "install": [
    "dnf install -y",
    "dnf install kernel",
    "dnf install package",
    "dnf module install m"
  ],
  "installed": [
    "dnf list installed"
  ],
  "iostat": [
    "iostat"
  ],
  "ip": [
    "ip -6 addr show",
    "ip -6 route show",
    "ip -s link show eth0",
    "ip addr",
    "ip addr add",
    "ip addr del",
    "ip addr show",
    "ip addr show eth0",
    "ip link set eth0 down",
    "ip link set eth0 mtu",
    "ip link set eth0 up",
    "ip link show",
    "ip neigh flush all",
    "ip neigh show",
    "ip netns add myns",
    "ip netns delete myns",
    "ip netns exec myns",
    "ip netns list",
    "ip route add",
    "ip route add default",
    "ip route del",
    "ip route del default",
    "ip route get 8.8.8.8",
    "ip route show"
  ],
  "is-active": [
    "systemctl is-active"
  ],
  "is-enabled": [
    "systemctl is-enabled"
  ],
  "is-failed": [
    "systemctl is-failed"
  ],
  "isolate": [
    "systemctl isolate"
  ],
  "jobs": [
    "jobs"
  ],
  "journalctl": [
    "journalctl",
    "journalctl --since",
    "journalctl --until",
    "journalctl -b",
    "journalctl -b -1",
    "journalctl -f",
    "journalctl -f -u",
    "journalctl -k",
    "journalctl -n 50",
    "journalctl -o",
    "journalctl -o json",
    "journalctl -p",
    "journalctl -p err",
    "journalctl -t",
    "journalctl -u",
    "journalctl -u sshd",
    "journalctl -xe"
  ],
  "json": [
    "journalctl -o json"
  ],
  "jumphost": [
    "ssh -J jumphost"
  ],
  "k1": [
    "echo ${MAP[k1]}"
  ],
  "katalogach": [
    "cp --backup src dst",
    "cp -a src/ dst/",
    "cp -i src dst",
    "cp -p src dst",
    "cp -r src/ dst/",
    "cp -u src dst",
    "cp -v src dst",
    "cp source dest",
    "mkdir -m 755 dirname",
    "mkdir -p a/b/c",
    "mkdir -v dirname",
    "mkdir dirname",
    "nadpisaniem",
    "rm -f file.txt",
    "rm -i file",
    "rm -r dir/",
    "rm -rf dir/",
    "rm -v file",
    "rm file.txt",
    "rsync",
    "rsync --delete src/",
    "rsync -av src/ dst/",
    "rsync -avz src/",
    "rsync -n src/ dst/",
    "touch -d",
    "touch -t",
    "touch file.txt"
  ],
  "katalogu": [
    "katalogu"
  ],
  "kdump": [
    "kdump"
  ],
  "kernel": [
    "dnf install kernel",
    "kernel",
    "rpm -qa kernel"
  ],
  "keyword": [
    "dnf search keyword"
  ],
  "kill": [
    "podman kill",
    "podman kill -s"
  ],
  "klient": [
    "//server",
    "cat /etc/fstab |",
    "grep cifs",
    "mount -t cifs",
    "smbclient",
    "testparm"
  ],
  "kompresja": [
    "--newer-mtime='2023-",
    "archive.tar.bz2",
    "archive.tar.gz",
    "archive.tar.xz",
    "find /path -print |",
    "newfile",
    "tar",
    "tar --delete -f",
    "tar --exclude-vcs",
    "tar -cvJf",
    "tar -cvf archive.tar",
    "tar -cvjf",
    "tar -cvzf",
    "tar -czf - /path |",
    "tar -czf arch.tar.gz",
    "tar -rvf archive.tar",
    "tar -tvf archive.tar",
    "tar -tvzf",
    "tar -uvf archive.tar",
    "tar -xvJf",
    "tar -xvf archive.tar",
    "tar -xvjf",
    "tar -xvzf"
  ],
  "konfiguracja": [
    "9000",
    "PID",
    "cat /etc/hostname",
    "cat /etc/hosts",
    "cat /etc/resolv.conf",
    "cat /etc/sysconfig/n",
    "curl",
    "established",
    "hostname",
    "ip -6 addr show",
    "ip -6 route show",
    "ip addr",
    "ip addr add",
    "ip addr del",
    "ip addr show",
    "ip addr show eth0",
    "ip link set eth0 down",
    "ip link set eth0 mtu",
    "ip link set eth0 up",
    "ip link show",
    "ip neigh flush all",
    "ip neigh show",
    "ip route add",
    "ip route add default",
    "ip route del",
    "ip route del default",
    "ip route get 8.8.8.8",
    "ip route show",
    "nmcli connection",
    "nmcli connection add",
    "nmcli connection up",
    "nmcli device show",
    "nmcli device status",
    "nmcli general",
    "nmcli radio wifi off",
    "nmtui",
    "procesami"
  ],
  "kontenery": [
    "--list-tags",
    "--restart=always",
    "-a",
    ".access.redhat.com/u",
    "/bin/bash",
    "/host:/container",
    "cat /etc/containers/",
    "cat Containerfile",
    "container",
    "dst:tag",
    "file.tar",
    "image",
    "image:tag",
    "podman --version",
    "podman build",
    "podman build -f",
    "podman build -t",
    "podman commit",
    "podman container",
    "podman cp",
    "podman cp src",
    "podman diff",
    "podman exec",
    "podman exec -it",
    "podman exec -u root",
    "podman generate",
    "podman generate kube",
    "podman image history",
    "podman image inspect",
    "podman image prune",
    "podman images",
    "podman images -a",
    "podman info",
    "podman inspect",
    "podman inspect -f",
    "podman kill",
    "podman kill -s",
    "podman load -i",
    "podman login",
    "podman logout",
    "podman logs",
    "podman logs --tail",
    "podman logs -f",
    "podman machine init",
    "podman machine start",
    "podman network",
    "podman network ls",
    "podman network rm",
    "podman pause",
    "podman play kube",
    "podman pod create",
    "podman pod inspect",
    "podman pod ls",
    "podman pod rm mypod",
    "podman pod start",
    "podman pod stats",
    "podman pod stop",
    "podman port",
    "podman ps",
    "podman ps --format",
    "podman ps -a",
    "podman ps -q",
    "podman ps -qa",
    "podman pull",
    "podman pull registry",
    "podman push",
    "podman rename",
    "podman restart",
    "podman rm -a",
    "podman rm -f",
    "podman rm container",
    "podman rmi -a",
    "podman rmi -f image",
    "podman rmi image",
    "podman run",
    "podman run --cap-add",
    "podman run --cpus",
    "podman run --memory",
    "podman run --name",
    "podman run --network",
    "podman run --pod",
    "podman run --restart",
    "podman run --rm",
    "podman run -d image",
    "podman run -e",
    "podman run -it image",
    "podman run -p",
    "podman run -u user",
    "podman run -v",
    "podman run image",
    "podman save image -o",
    "podman search",
    "podman search nginx",
    "podman start",
    "podman stats",
    "podman stop",
    "podman stop -t 0",
    "podman system df",
    "podman system prune",
    "podman system reset",
    "podman tag src:tag",
    "podman top container",
    "podman unpause",
    "podman unshare",
    "podman volume",
    "podman volume create",
    "podman volume ls",
    "podman volume prune",
    "podman volume rm"
  ],
  "kube": [
    "podman generate kube",
    "podman play kube"
  ],
  "l": [
    "find / -type l"
  ],
  "label": [
    "mount LABEL=mylabel"
  ],
  "last": [
    "last"
  ],
  "lastb": [
    "lastb"
  ],
  "lastlog": [
    "lastlog"
  ],
  "link": [
    "ip -s link show eth0",
    "ip link set eth0 down",
    "ip link set eth0 mtu",
    "ip link set eth0 up",
    "ip link show"
  ],
  "list": [
    "dnf list available",
    "dnf list extras",
    "dnf list installed",
    "dnf list obsoletes",
    "dnf list updates",
    "dnf module list",
    "dnf updateinfo list",
    "ip netns list"
  ],
  "list-dependencies": [
    "list-dependencies"
  ],
  "list-timers": [
    "list-timers"
  ],
  "list-unit-files": [
    "list-unit-files"
  ],
  "list-units": [
    "systemctl list-units"
  ],
  "literal": [
    "grep -F 'literal'"
  ],
  "ll": [
    "alias ll='ls -alh'"
  ],
  "load": [
    "podman load -i"
  ],
  "localectl": [
    "localectl"
  ],
  "localhost": [
    "8080:localhost:80"
  ],
  "logical": [
    "/dev/sdb",
    "/dev/sdc",
    "lvdisplay",
    "lvmdiskscan",
    "lvremove",
    "lvs",
    "lvscan",
    "newname",
    "partycji)",
    "pvdisplay",
    "pvs",
    "pvscan",
    "vgdisplay",
    "vgs",
    "vgscan"
  ],
  "login": [
    "podman login",
    "semanage login -a -s",
    "semanage login -l"
  ],
  "loginctl": [
    "loginctl"
  ],
  "logout": [
    "podman logout"
  ],
  "logowanie": [
    "--disk-usage",
    "--level=err,warn",
    "/var/log/messages",
    "aureport",
    "cat /etc/audit/audit",
    "cat /var/log/cron",
    "cat /var/log/maillog",
    "cat /var/log/secure",
    "dmesg",
    "grep 'Accepted'",
    "grep 'Failed",
    "journalctl -o",
    "journalctl -u sshd",
    "journalctl -xe",
    "ls /etc/logrotate.d/",
    "udit.log"
  ],
  "logs": [
    "podman logs",
    "podman logs --tail",
    "podman logs -f"
  ],
  "ls": [
    "alias ll='ls -alh'",
    "ls",
    "ls --color=auto",
    "ls -R",
    "ls -Z dir/",
    "ls -Z file",
    "ls -d */",
    "ls -dZ dir/",
    "ls -i",
    "ls -l",
    "ls -lS",
    "ls -la",
    "ls -lh",
    "ls -lt",
    "ls /boot/",
    "ls /boot/grub2/",
    "ls /etc | head -20",
    "ls /etc/cron.d/",
    "ls /etc/cron.daily/",
    "ls /etc/cron.hourly/",
    "ls /etc/cron.weekly/",
    "ls /etc/logrotate.d/",
    "ls /etc/profile.d/",
    "ls /mnt/nfs/share",
    "ls /proc | wc -l",
    "ls /sys/fs/cgroup/",
    "podman network ls",
    "podman pod ls",
    "podman volume ls"
  ],
  "lsblk": [
    "lsblk"
  ],
  "lscpu": [
    "lscpu"
  ],
  "lshw": [
    "lshw"
  ],
  "lslogins": [
    "lslogins"
  ],
  "lsmem": [
    "lsmem"
  ],
  "lsmod": [
    "lsmod"
  ],
  "lsnuma": [
    "lsnuma"
  ],
  "lsof": [
    "lsof"
  ],
  "lspci": [
    "lspci"
  ],
  "lsusb": [
    "lsusb"
  ],
  "lvdisplay": [
    "lvdisplay"
  ],
  "lvm": [
    "/dev/sdb",
    "/dev/sdc",
    "lvdisplay",
    "lvmdiskscan",
    "lvremove",
    "lvs",
    "lvscan",
    "newname",
    "partycji)",
    "pvdisplay",
    "pvs",
    "pvscan",
    "vgdisplay",
    "vgs",
    "vgscan"
  ],
  "lvmdiskscan": [
    "lvmdiskscan"
  ],
  "lvremove": [
    "lvremove"
  ],
  "lvs": [
    "lvs"
  ],
  "lvscan": [
    "lvscan"
  ],
  "m": [
    "dnf module install m"
  ],
  "machine": [
    "podman machine init",
    "podman machine start"
  ],
  "makecache": [
    "dnf makecache"
  ],
  "manager": [
    "/dev/sdb",
    "/dev/sdc",
    "lvdisplay",
    "lvmdiskscan",
    "lvremove",
    "lvs",
    "lvscan",
    "newname",
    "partycji)",
    "pvdisplay",
    "pvs",
    "pvscan",
    "vgdisplay",
    "vgs",
    "vgscan"
  ],
  "mask": [
    "systemctl mask"
  ],
  "matchpathcon": [
    "matchpathcon"
  ],
  "mdadm": [
    "mdadm"
  ],
  "memory": [
    "memory:mygroup"
  ],
  "metadata": [
    "dnf clean metadata"
  ],
  "mkdir": [
    "mkdir -m 755 dirname",
    "mkdir -p a/b/c",
    "mkdir -v dirname",
    "mkdir dirname"
  ],
  "mktemp": [
    "TMPFILE=$(mktemp)",
    "mktemp"
  ],
  "module": [
    "dnf module disable",
    "dnf module enable",
    "dnf module info",
    "dnf module install m",
    "dnf module list",
    "dnf module reset"
  ],
  "module_name": [
    "echo 'module_name' >"
  ],
  "monitorowanie": [
    "--disk-usage",
    "--level=err,warn",
    "/var/log/messages",
    "aureport",
    "cat /etc/audit/audit",
    "cat /var/log/cron",
    "cat /var/log/maillog",
    "cat /var/log/secure",
    "dmesg",
    "grep 'Accepted'",
    "grep 'Failed",
    "journalctl -o",
    "journalctl -u sshd",
    "journalctl -xe",
    "ls /etc/logrotate.d/",
    "udit.log"
  ],
  "montowania": [
    "montowania"
  ],
  "montowanie": [
    "/dev/sdb1",
    "/mnt",
    "cat /etc/fstab",
    "cat /proc/mounts",
    "findmnt",
    "montowania",
    "mount -a",
    "mount -o remount,ro",
    "mount -o remount,rw",
    "mount -o ro",
    "mount -o rw,noexec",
    "mount -t ext4",
    "mount -t xfs",
    "mount /dev/sdb1 /mnt",
    "mount LABEL=mylabel",
    "mount UUID=xxx /mnt",
    "mount | column -t"
  ],
  "mount": [
    "mount -a",
    "mount -o",
    "mount -o remount,ro",
    "mount -o remount,rw",
    "mount -o ro",
    "mount -o ro,soft",
    "mount -o rw,noexec",
    "mount -t cifs",
    "mount -t ext4",
    "mount -t nfs",
    "mount -t nfs4",
    "mount -t xfs",
    "mount /dev/sdb1 /mnt",
    "mount LABEL=mylabel",
    "mount UUID=xxx /mnt",
    "mount | column -t"
  ],
  "mtu": [
    "ip link set eth0 mtu"
  ],
  "myapp.timer": [
    "myapp.timer"
  ],
  "mygroup": [
    "memory:mygroup",
    "mygroup"
  ],
  "mylabel": [
    "mount LABEL=mylabel"
  ],
  "myns": [
    "ip netns add myns",
    "ip netns delete myns",
    "ip netns exec myns"
  ],
  "mypod": [
    "podman pod rm mypod"
  ],
  "n": [
    "N",
    "n"
  ],
  "na": [
    "cp --backup src dst",
    "cp -a src/ dst/",
    "cp -i src dst",
    "cp -p src dst",
    "cp -r src/ dst/",
    "cp -u src dst",
    "cp -v src dst",
    "cp source dest",
    "mkdir -m 755 dirname",
    "mkdir -p a/b/c",
    "mkdir -v dirname",
    "mkdir dirname",
    "nadpisaniem",
    "rm -f file.txt",
    "rm -i file",
    "rm -r dir/",
    "rm -rf dir/",
    "rm -v file",
    "rm file.txt",
    "rsync",
    "rsync --delete src/",
    "rsync -av src/ dst/",
    "rsync -avz src/",
    "rsync -n src/ dst/",
    "touch -d",
    "touch -t",
    "touch file.txt"
  ],
  "nadpisaniem": [
    "nadpisaniem"
  ],
  "name": [
    "Name'"
  ],
  "narz": [
    "--filename=/tmp/test",
    "--leak-check=full",
    "--zone=drop",
    "/tmp/cap.pcap",
    "/var/log/sa/saDD",
    "100))",
    "32",
    "alternatives",
    "authselect",
    "bash",
    "bonnie++",
    "cat /etc/chrony.conf",
    "cat /etc/crypto-poli",
    "cat /etc/kdump.conf",
    "cat /proc/PID/limits",
    "cat /proc/net/tcp",
    "cat /proc/net/udp",
    "cat /proc/sys/net/nf",
    "cat /sys/fs/cgroup/m",
    "cmd",
    "count=1000",
    "date",
    "echo $((RANDOM %",
    "echo '3.14 * 2' | bc",
    "echo file{1..3}.txt",
    "echo {1..5}",
    "echo {a,b,c}.log",
    "emory/mygroup/memory",
    "fio",
    "fips-mode-setup",
    "gpg",
    "hwclock",
    "ip -s link show eth0",
    "ip netns add myns",
    "ip netns delete myns",
    "ip netns exec myns",
    "ip netns list",
    "kdump",
    "ls /sys/fs/cgroup/",
    "memory:mygroup",
    "mygroup",
    "ntsysv",
    "scap-workbench",
    "systemd-cgls",
    "systemd-cgtop",
    "t_in_bytes=512M",
    "update-alternatives",
    "update-crypto-polici",
    "valgrind",
    "wireshark"
  ],
  "nawigacja": [
    "basename",
    "cd -",
    "cd /",
    "cd /path/to/dir",
    "cd ~",
    "dirname",
    "dirs",
    "echo $HOME",
    "echo $OLDPWD",
    "echo $PATH",
    "echo $PWD",
    "ls",
    "ls --color=auto",
    "ls -R",
    "ls -d */",
    "ls -i",
    "ls -l",
    "ls -lS",
    "ls -la",
    "ls -lh",
    "ls -lt",
    "ls /etc | head -20",
    "ls /proc | wc -l",
    "popd",
    "pwd",
    "tree"
  ],
  "neigh": [
    "ip neigh flush all",
    "ip neigh show"
  ],
  "net.ipv4.ip_fo": [
    "echo 'net.ipv4.ip_fo"
  ],
  "netns": [
    "ip netns add myns",
    "ip netns delete myns",
    "ip netns exec myns",
    "ip netns list"
  ],
  "network": [
    "podman network",
    "podman network ls",
    "podman network rm"
  ],
  "newfile": [
    "newfile"
  ],
  "newname": [
    "newname",
    "usermod -l newname"
  ],
  "nf": [
    "awk '{print NF}'"
  ],
  "nfs": [
    "//server",
    "cat /etc/auto.master",
    "cat /etc/auto.misc",
    "cat /etc/exports",
    "cat /etc/fstab |",
    "exportfs",
    "firewall-cmd --add-s",
    "grep cifs",
    "ls /mnt/nfs/share",
    "mount -o",
    "mount -o ro,soft",
    "mount -t cifs",
    "mount -t nfs",
    "mount -t nfs4",
    "nfs-server",
    "nfsstat",
    "nosuid,noexec",
    "server:/share",
    "smbclient",
    "testparm"
  ],
  "nfs-server": [
    "nfs-server"
  ],
  "nfs4": [
    "mount -t nfs4"
  ],
  "nfsstat": [
    "nfsstat"
  ],
  "nginx": [
    "podman search nginx"
  ],
  "nmcli": [
    "nmcli connection",
    "nmcli connection add",
    "nmcli connection up",
    "nmcli device show",
    "nmcli device status",
    "nmcli general",
    "nmcli radio wifi off"
  ],
  "nmtui": [
    "nmtui"
  ],
  "no": [
    "Checking=no",
    "ntication=no"
  ],
  "noexec": [
    "mount -o rw,noexec",
    "nosuid,noexec"
  ],
  "none": [
    "vim -u NONE file.txt"
  ],
  "nosuid": [
    "nosuid,noexec"
  ],
  "nowy": [
    "usermod -c 'Nowy"
  ],
  "nproc": [
    "nproc"
  ],
  "nr": [
    "awk 'END{print NR}'",
    "awk 'NR==5' file",
    "awk 'NR>=5 &&"
  ],
  "ntication": [
    "ntication=no"
  ],
  "ntsysv": [
    "ntsysv"
  ],
  "o": [
    "O",
    "baseboard",
    "cat /etc/os-release",
    "cat /proc/cpuinfo",
    "cat /proc/uptime",
    "cat /sys/block/sda/q",
    "cat /sys/class/dmi/i",
    "chmod u=rwx,g=rx,o=r",
    "iostat",
    "lscpu",
    "lshw",
    "lsmem",
    "lsnuma",
    "lspci",
    "lsusb",
    "nproc",
    "o",
    "sensors",
    "sensors-detect",
    "vmstat"
  ],
  "o-r": [
    "chmod o-r file"
  ],
  "obsoletes": [
    "dnf list obsoletes"
  ],
  "off": [
    "nmcli radio wifi off"
  ],
  "ogniowa": [
    "--add-port=8080/tcp",
    "--add-service=http",
    "--add-service=https",
    "--complete-reload",
    "--get-active-zones",
    "--get-default-zone",
    "--get-zones",
    "--list-all",
    "--list-ports",
    "--list-rich-rules",
    "--list-services",
    "--zone=public",
    "e-port=8080/tcp",
    "e-service=http",
    "efault-zone=trusted",
    "firewall-cmd",
    "firewall-cmd --add-f",
    "firewall-cmd --add-p",
    "firewall-cmd --add-r",
    "firewall-cmd --remov",
    "firewall-cmd --runti",
    "firewall-cmd --set-d",
    "firewall-cmd --state",
    "firewalld",
    "w■■czona"
  ],
  "oka": [
    "Ctrl+R",
    "alias",
    "alias ll='ls -alh'",
    "cat /etc/bashrc",
    "cat /etc/profile",
    "cat ~/.bash_logout",
    "cat ~/.bash_profile",
    "cat ~/.bashrc",
    "complete",
    "echo $!",
    "echo $#",
    "echo $$",
    "echo $*",
    "echo $0",
    "echo $?",
    "echo $@",
    "echo $BASH_VERSION",
    "echo $HISTFILE",
    "echo $HISTFILESIZE",
    "echo $HISTSIZE",
    "echo $PS1",
    "echo $SHELL",
    "echo $VARIABLE",
    "echo ${#ARRAY[@]}",
    "echo ${ARRAY[0]}",
    "echo ${ARRAY[@]}",
    "env",
    "false",
    "hash",
    "history",
    "ls /etc/profile.d/",
    "printenv",
    "set",
    "source",
    "true"
  ],
  "operacje": [
    "cp --backup src dst",
    "cp -a src/ dst/",
    "cp -i src dst",
    "cp -p src dst",
    "cp -r src/ dst/",
    "cp -u src dst",
    "cp -v src dst",
    "cp source dest",
    "mkdir -m 755 dirname",
    "mkdir -p a/b/c",
    "mkdir -v dirname",
    "mkdir dirname",
    "nadpisaniem",
    "rm -f file.txt",
    "rm -i file",
    "rm -r dir/",
    "rm -rf dir/",
    "rm -v file",
    "rm file.txt",
    "rsync",
    "rsync --delete src/",
    "rsync -av src/ dst/",
    "rsync -avz src/",
    "rsync -n src/ dst/",
    "touch -d",
    "touch -t",
    "touch file.txt"
  ],
  "p": [
    "4096",
    "8080:localhost:80",
    "Checking=no",
    "ConnectTimeout=10",
    "P",
    "cat ~/.ssh/config",
    "chmod 600 ~/.ssh/aut",
    "chmod 700 ~/.ssh/",
    "ed25519",
    "horized_keys",
    "ntication=no",
    "p",
    "rsync -avz",
    "rsync -avz -e ssh",
    "scp",
    "ssh -A user@host",
    "ssh -D 1080",
    "ssh -J jumphost",
    "ssh -L",
    "ssh -N -f -L",
    "ssh -R",
    "ssh -X user@host",
    "ssh -i",
    "ssh -o",
    "ssh -o BatchMode=yes",
    "ssh -o PasswordAuthe",
    "ssh -o PreferredAuth",
    "ssh -o StrictHostKey",
    "ssh -p 2222",
    "ssh -t user@host",
    "ssh -v user@host",
    "ssh -vvv user@host",
    "ssh user@hostname",
    "ssh-add",
    "ssh-copy-id",
    "user@host",
    "user@hostname",
    "~/.ssh/id_rsa",
    "~/.ssh/id_rsa.pub",
    "~/.ssh/key.pem",
    "~/.ssh/mykey"
  ],
  "package": [
    "dnf erase package",
    "dnf info package",
    "dnf install package",
    "dnf remove package",
    "dnf update package",
    "package",
    "rpm -V package",
    "rpm -e package",
    "rpm -qR package",
    "rpm -qc package",
    "rpm -qd package",
    "rpm -qi package",
    "rpm -ql package"
  ],
  "package.rpm": [
    "rpm -Fvh package.rpm",
    "rpm -K package.rpm",
    "rpm -Uvh package.rpm",
    "rpm -ivh package.rpm",
    "rpm -qip package.rpm"
  ],
  "packages": [
    "dnf clean packages"
  ],
  "pakietami": [
    "Name'",
    "aktualizacjami",
    "dnf autoremove",
    "dnf check-update",
    "dnf clean all",
    "dnf clean metadata",
    "dnf clean packages",
    "dnf config-manager",
    "dnf distro-sync",
    "dnf downgrade",
    "dnf erase package",
    "dnf groupinfo 'Group",
    "dnf groupinstall",
    "dnf grouplist",
    "dnf groupremove",
    "dnf history",
    "dnf history info 5",
    "dnf history redo 5",
    "dnf history rollback",
    "dnf history undo 5",
    "dnf info package",
    "dnf install -y",
    "dnf install package",
    "dnf list available",
    "dnf list extras",
    "dnf list installed",
    "dnf list obsoletes",
    "dnf list updates",
    "dnf makecache",
    "dnf module disable",
    "dnf module enable",
    "dnf module info",
    "dnf module install m",
    "dnf module list",
    "dnf module reset",
    "dnf provides",
    "dnf reinstall",
    "dnf remove package",
    "dnf repoinfo repo-id",
    "dnf repolist",
    "dnf repolist all",
    "dnf search keyword",
    "dnf security update",
    "dnf update",
    "dnf update package",
    "dnf updateinfo list",
    "dnf upgrade",
    "dnf upgrade-minimal",
    "dnf whatprovides",
    "package",
    "rpm --import",
    "rpm -Fvh package.rpm",
    "rpm -K package.rpm",
    "rpm -Uvh package.rpm",
    "rpm -V package",
    "rpm -Va",
    "rpm -e package",
    "rpm -ivh package.rpm",
    "rpm -q --changelog",
    "rpm -q --scripts",
    "rpm -qR package",
    "rpm -qa",
    "rpm -qc package",
    "rpm -qd package",
    "rpm -qf",
    "rpm -qi package",
    "rpm -qip package.rpm",
    "rpm -ql package",
    "rpm -qp --scripts",
    "subscription-manager"
  ],
  "partprobe": [
    "partprobe"
  ],
  "partycje": [
    "blkid",
    "dysków",
    "lsblk",
    "partprobe",
    "print"
  ],
  "partycji": [
    "partycji)"
  ],
  "passwordauthe": [
    "ssh -o PasswordAuthe"
  ],
  "pat1": [
    "grep -E 'pat1|pat2'"
  ],
  "pat2": [
    "grep -E 'pat1|pat2'"
  ],
  "pattern": [
    "grep 'pattern' file",
    "grep -A 3 'pattern'",
    "grep -B 3 'pattern'",
    "grep -C 3 'pattern'",
    "grep -c 'pattern'",
    "grep -i 'pattern'",
    "grep -l 'pattern'",
    "grep -m 5 'pattern'",
    "grep -n 'pattern'",
    "grep -o 'pattern'",
    "grep -q 'pattern'",
    "grep -r 'pattern'",
    "grep -v 'pattern'"
  ],
  "pause": [
    "podman pause"
  ],
  "pid": [
    "PID"
  ],
  "play": [
    "podman play kube"
  ],
  "plikach": [
    "cp --backup src dst",
    "cp -a src/ dst/",
    "cp -i src dst",
    "cp -p src dst",
    "cp -r src/ dst/",
    "cp -u src dst",
    "cp -v src dst",
    "cp source dest",
    "mkdir -m 755 dirname",
    "mkdir -p a/b/c",
    "mkdir -v dirname",
    "mkdir dirname",
    "nadpisaniem",
    "rm -f file.txt",
    "rm -i file",
    "rm -r dir/",
    "rm -rf dir/",
    "rm -v file",
    "rm file.txt",
    "rsync",
    "rsync --delete src/",
    "rsync -av src/ dst/",
    "rsync -avz src/",
    "rsync -n src/ dst/",
    "touch -d",
    "touch -t",
    "touch file.txt"
  ],
  "plików": [
    "/dev/sdb1",
    "/mnt",
    "basename",
    "cat -A file.txt",
    "cat -n file.txt",
    "cat /etc/fstab",
    "cat /proc/mounts",
    "cat file.txt",
    "cat file1 file2",
    "cd -",
    "cd /",
    "cd /path/to/dir",
    "cd ~",
    "chmod",
    "chmod +t dir",
    "chmod -R 755 dir/",
    "chmod 1755 dir",
    "chmod 2755 dir",
    "chmod 4755 file",
    "chmod 600 file",
    "chmod 644 file",
    "chmod 755 file",
    "chmod 777 file",
    "chmod a+r file",
    "chmod g+s dir",
    "chmod g-w file",
    "chmod o-r file",
    "chmod u+s file",
    "chmod u+x file",
    "chmod u=rwx,g=rx,o=r",
    "chown",
    "chown -R user:group",
    "chown :group file",
    "chown user file",
    "chown user:group",
    "dir/",
    "dirname",
    "dirs",
    "echo $HOME",
    "echo $OLDPWD",
    "echo $PATH",
    "echo $PWD",
    "find . ! -name",
    "find . -atime -1",
    "find . -ctime -1",
    "find . -empty",
    "find . -gid 1000",
    "find . -group",
    "find . -iname",
    "find . -links +1",
    "find . -maxdepth 2",
    "find . -mindepth 2",
    "find . -mmin -60",
    "find . -mount -name",
    "find . -mtime +30",
    "find . -mtime -7",
    "find . -name",
    "find . -name '*.log'",
    "find . -name '*.py'",
    "find . -name '*.tmp'",
    "find . -name '*.txt'",
    "find . -newer",
    "find . -nogroup",
    "find . -nouser",
    "find . -perm -1000",
    "find . -perm -2000",
    "find . -perm -4000",
    "find . -perm -644",
    "find . -perm /644",
    "find . -perm 644",
    "find . -size +100M",
    "find . -size +1G",
    "find . -size -10k",
    "find . -size 512c",
    "find . -type f -name",
    "find . -type f -newer",
    "find . -uid 1000",
    "find . -user",
    "find . -xdev -name",
    "find / -inum 12345",
    "find / -name",
    "find / -perm -2000",
    "find / -perm -4000",
    "find / -perm -o+w",
    "find / -type b",
    "find / -type c",
    "find / -type d -name",
    "find / -type f -name",
    "find / -type l",
    "find /tmp -mtime +7",
    "findmnt",
    "katalogu",
    "ls",
    "ls --color=auto",
    "ls -R",
    "ls -Z file",
    "ls -d */",
    "ls -i",
    "ls -l",
    "ls -lS",
    "ls -la",
    "ls -lh",
    "ls -lt",
    "ls /etc | head -20",
    "ls /proc | wc -l",
    "montowania",
    "mount -a",
    "mount -o remount,ro",
    "mount -o remount,rw",
    "mount -o ro",
    "mount -o rw,noexec",
    "mount -t ext4",
    "mount -t xfs",
    "mount /dev/sdb1 /mnt",
    "mount LABEL=mylabel",
    "mount UUID=xxx /mnt",
    "mount | column -t",
    "popd",
    "pwd",
    "reference_file",
    "tree",
    "umask",
    "updatedb",
    "w■a■ciciel)",
    "w■a■ciciela"
  ],
  "po": [
    "basename",
    "cd -",
    "cd /",
    "cd /path/to/dir",
    "cd ~",
    "dirname",
    "dirs",
    "echo $HOME",
    "echo $OLDPWD",
    "echo $PATH",
    "echo $PWD",
    "ls",
    "ls --color=auto",
    "ls -R",
    "ls -d */",
    "ls -i",
    "ls -l",
    "ls -lS",
    "ls -la",
    "ls -lh",
    "ls -lt",
    "ls /etc | head -20",
    "ls /proc | wc -l",
    "popd",
    "pwd",
    "tree"
  ],
  "pod": [
    "podman pod create",
    "podman pod inspect",
    "podman pod ls",
    "podman pod rm mypod",
    "podman pod start",
    "podman pod stats",
    "podman pod stop"
  ],
  "podman": [
    "--list-tags",
    "--restart=always",
    "-a",
    ".access.redhat.com/u",
    "/bin/bash",
    "/host:/container",
    "cat /etc/containers/",
    "cat Containerfile",
    "container",
    "dst:tag",
    "file.tar",
    "image",
    "image:tag",
    "podman --version",
    "podman build",
    "podman build -f",
    "podman build -t",
    "podman commit",
    "podman container",
    "podman cp",
    "podman cp src",
    "podman diff",
    "podman exec",
    "podman exec -it",
    "podman exec -u root",
    "podman generate",
    "podman generate kube",
    "podman image history",
    "podman image inspect",
    "podman image prune",
    "podman images",
    "podman images -a",
    "podman info",
    "podman inspect",
    "podman inspect -f",
    "podman kill",
    "podman kill -s",
    "podman load -i",
    "podman login",
    "podman logout",
    "podman logs",
    "podman logs --tail",
    "podman logs -f",
    "podman machine init",
    "podman machine start",
    "podman network",
    "podman network ls",
    "podman network rm",
    "podman pause",
    "podman play kube",
    "podman pod create",
    "podman pod inspect",
    "podman pod ls",
    "podman pod rm mypod",
    "podman pod start",
    "podman pod stats",
    "podman pod stop",
    "podman port",
    "podman ps",
    "podman ps --format",
    "podman ps -a",
    "podman ps -q",
    "podman ps -qa",
    "podman pull",
    "podman pull registry",
    "podman push",
    "podman rename",
    "podman restart",
    "podman rm -a",
    "podman rm -f",
    "podman rm container",
    "podman rmi -a",
    "podman rmi -f image",
    "podman rmi image",
    "podman run",
    "podman run --cap-add",
    "podman run --cpus",
    "podman run --memory",
    "podman run --name",
    "podman run --network",
    "podman run --pod",
    "podman run --restart",
    "podman run --rm",
    "podman run -d image",
    "podman run -e",
    "podman run -it image",
    "podman run -p",
    "podman run -u user",
    "podman run -v",
    "podman run image",
    "podman save image -o",
    "podman search",
    "podman search nginx",
    "podman start",
    "podman stats",
    "podman stop",
    "podman stop -t 0",
    "podman system df",
    "podman system prune",
    "podman system reset",
    "podman tag src:tag",
    "podman top container",
    "podman unpause",
    "podman unshare",
    "podman volume",
    "podman volume create",
    "podman volume ls",
    "podman volume prune",
    "podman volume rm"
  ],
  "podstawy": [
    "$#",
    "$$",
    "$0",
    "$?",
    "$@",
    "./script.sh",
    "1>/dev/null",
    "2>/dev/null",
    "ARRAY+=('e')",
    "TMPFILE=$(mktemp)",
    "VAR=$(command)",
    "VAR='value'",
    "break",
    "chmod +x script.sh",
    "continue",
    "do",
    "done",
    "echo \"Value: $VAR\"",
    "echo ${MAP[k1]}",
    "else",
    "esac",
    "fi",
    "mktemp",
    "then",
    "}"
  ],
  "popd": [
    "popd"
  ],
  "port": [
    "podman port",
    "semanage port -a -t",
    "semanage port -d -t",
    "semanage port -l",
    "semanage port -l |",
    "semanage port -m -t"
  ],
  "pow": [
    "Ctrl+R",
    "alias",
    "alias ll='ls -alh'",
    "cat /etc/bashrc",
    "cat /etc/profile",
    "cat ~/.bash_logout",
    "cat ~/.bash_profile",
    "cat ~/.bashrc",
    "complete",
    "echo $!",
    "echo $#",
    "echo $$",
    "echo $*",
    "echo $0",
    "echo $?",
    "echo $@",
    "echo $BASH_VERSION",
    "echo $HISTFILE",
    "echo $HISTFILESIZE",
    "echo $HISTSIZE",
    "echo $PS1",
    "echo $SHELL",
    "echo $VARIABLE",
    "echo ${#ARRAY[@]}",
    "echo ${ARRAY[0]}",
    "echo ${ARRAY[@]}",
    "env",
    "false",
    "hash",
    "history",
    "ls /etc/profile.d/",
    "printenv",
    "set",
    "source",
    "true"
  ],
  "poweroff": [
    "poweroff",
    "systemctl poweroff"
  ],
  "preferredauth": [
    "ssh -o PreferredAuth"
  ],
  "print": [
    "awk '{print $1}'",
    "awk '{print $NF}'",
    "awk '{print NF}'",
    "awk -F: '{print $1}'",
    "print"
  ],
  "printenv": [
    "printenv"
  ],
  "procesami": [
    "Ctrl+C",
    "Ctrl+D",
    "Ctrl+Z",
    "cat /proc/PID/maps",
    "cat /proc/PID/status",
    "cat /proc/loadavg",
    "cat /proc/meminfo",
    "htop",
    "jobs",
    "lsof",
    "procesami",
    "ps",
    "pstree",
    "top",
    "uptime",
    "u■ytkownika",
    "wait"
  ],
  "provides": [
    "dnf provides"
  ],
  "prune": [
    "podman image prune",
    "podman system prune",
    "podman volume prune"
  ],
  "przechowywanie": [
    "blkid",
    "dysków",
    "lsblk",
    "partprobe",
    "print"
  ],
  "przegl": [
    "cat -A file.txt",
    "cat -n file.txt",
    "cat file.txt",
    "cat file1 file2"
  ],
  "ps": [
    "podman ps",
    "podman ps --format",
    "podman ps -a",
    "podman ps -q",
    "podman ps -qa",
    "ps"
  ],
  "pstree": [
    "pstree"
  ],
  "public": [
    "--zone=public"
  ],
  "pull": [
    "podman pull",
    "podman pull registry"
  ],
  "push": [
    "podman push"
  ],
  "pvdisplay": [
    "pvdisplay"
  ],
  "pvs": [
    "pvs"
  ],
  "pvscan": [
    "pvscan"
  ],
  "pwck": [
    "pwck"
  ],
  "pwd": [
    "pwd"
  ],
  "q": [
    "q"
  ],
  "qa": [
    "qa"
  ],
  "r": [
    "R",
    "chmod u=rwx,g=rx,o=r",
    "r"
  ],
  "radio": [
    "nmcli radio wifi off"
  ],
  "raid": [
    "--raid-devices=2",
    "--scan",
    "/dev/md0",
    "/dev/sdd",
    "cat /etc/mdadm.conf",
    "cat /proc/mdstat",
    "mdadm"
  ],
  "random": [
    "echo $((RANDOM %"
  ],
  "reboot": [
    "reboot",
    "systemctl reboot"
  ],
  "redo": [
    "dnf history redo 5"
  ],
  "reference_file": [
    "reference_file"
  ],
  "registry": [
    "podman pull registry"
  ],
  "reinstall": [
    "dnf reinstall"
  ],
  "reload": [
    "systemctl reload"
  ],
  "remount": [
    "mount -o remount,ro",
    "mount -o remount,rw"
  ],
  "remove": [
    "dnf remove",
    "dnf remove package"
  ],
  "rename": [
    "podman rename"
  ],
  "repo-id": [
    "dnf repoinfo repo-id"
  ],
  "repoinfo": [
    "dnf repoinfo repo-id"
  ],
  "repolist": [
    "dnf repolist",
    "dnf repolist all"
  ],
  "rescue": [
    "systemctl rescue"
  ],
  "rescue.target": [
    "rescue.target"
  ],
  "reset": [
    "dnf module reset",
    "podman system reset"
  ],
  "restart": [
    "podman restart",
    "systemctl restart"
  ],
  "restorecon": [
    "restorecon",
    "restorecon -F /path/",
    "restorecon -R",
    "restorecon -Rv"
  ],
  "rm": [
    "podman network rm",
    "podman pod rm mypod",
    "podman rm -a",
    "podman rm -f",
    "podman rm container",
    "podman volume rm",
    "rm -f file.txt",
    "rm -i file",
    "rm -r dir/",
    "rm -rf dir/",
    "rm -v file",
    "rm file.txt"
  ],
  "rmi": [
    "podman rmi -a",
    "podman rmi -f image",
    "podman rmi image"
  ],
  "ro": [
    "mount -o remount,ro",
    "mount -o ro",
    "mount -o ro,soft"
  ],
  "rodowiskowe": [
    "Ctrl+R",
    "alias",
    "alias ll='ls -alh'",
    "cat /etc/bashrc",
    "cat /etc/profile",
    "cat ~/.bash_logout",
    "cat ~/.bash_profile",
    "cat ~/.bashrc",
    "complete",
    "echo $!",
    "echo $#",
    "echo $$",
    "echo $*",
    "echo $0",
    "echo $?",
    "echo $@",
    "echo $BASH_VERSION",
    "echo $HISTFILE",
    "echo $HISTFILESIZE",
    "echo $HISTSIZE",
    "echo $PS1",
    "echo $SHELL",
    "echo $VARIABLE",
    "echo ${#ARRAY[@]}",
    "echo ${ARRAY[0]}",
    "echo ${ARRAY[@]}",
    "env",
    "false",
    "hash",
    "history",
    "ls /etc/profile.d/",
    "printenv",
    "set",
    "source",
    "true"
  ],
  "rollback": [
    "dnf history rollback"
  ],
  "root": [
    "podman exec -u root"
  ],
  "route": [
    "ip -6 route show",
    "ip route add",
    "ip route add default",
    "ip route del",
    "ip route del default",
    "ip route get 8.8.8.8",
    "ip route show"
  ],
  "rpm": [
    "rpm --import",
    "rpm -Fvh package.rpm",
    "rpm -K package.rpm",
    "rpm -Uvh package.rpm",
    "rpm -V package",
    "rpm -Va",
    "rpm -e package",
    "rpm -ivh package.rpm",
    "rpm -q --changelog",
    "rpm -q --scripts",
    "rpm -qR package",
    "rpm -qa",
    "rpm -qa kernel",
    "rpm -qc package",
    "rpm -qd package",
    "rpm -qf",
    "rpm -qi package",
    "rpm -qip package.rpm",
    "rpm -ql package",
    "rpm -qp --scripts"
  ],
  "rsync": [
    "rsync",
    "rsync --delete src/",
    "rsync -av src/ dst/",
    "rsync -avz",
    "rsync -avz -e ssh",
    "rsync -avz src/",
    "rsync -n src/ dst/"
  ],
  "run": [
    "podman run",
    "podman run --cap-add",
    "podman run --cpus",
    "podman run --memory",
    "podman run --name",
    "podman run --network",
    "podman run --pod",
    "podman run --restart",
    "podman run --rm",
    "podman run -d image",
    "podman run -e",
    "podman run -it image",
    "podman run -p",
    "podman run -u user",
    "podman run -v",
    "podman run image"
  ],
  "run-parts": [
    "run-parts"
  ],
  "rw": [
    "mount -o remount,rw",
    "mount -o rw,noexec"
  ],
  "rwx": [
    "chmod u=rwx,g=rx,o=r"
  ],
  "rx": [
    "chmod u=rwx,g=rx,o=r"
  ],
  "samba": [
    "//server",
    "cat /etc/fstab |",
    "grep cifs",
    "mount -t cifs",
    "smbclient",
    "testparm"
  ],
  "samba_e": [
    "setsebool -P samba_e"
  ],
  "save": [
    "podman save image -o"
  ],
  "scap-workbench": [
    "scap-workbench"
  ],
  "scp": [
    "scp"
  ],
  "script.sh": [
    "chmod +x script.sh"
  ],
  "search": [
    "dnf search keyword",
    "podman search",
    "podman search nginx"
  ],
  "security": [
    "dnf security update"
  ],
  "selinux": [
    "-t",
    "/etc/selinux/config",
    "/path/to/file",
    "SELinux",
    "cat",
    "cat /var/log/audit/a",
    "getenforce",
    "grep 'denied' /var/l",
    "httpd_sys_content_t",
    "journalctl -t",
    "ls -Z dir/",
    "ls -dZ dir/",
    "matchpathcon",
    "restorecon",
    "restorecon -F /path/",
    "restorecon -R",
    "restorecon -Rv",
    "semanage boolean -l",
    "semanage fcontext -a",
    "semanage fcontext -d",
    "semanage fcontext -l",
    "semanage fcontext -m",
    "semanage login -a -s",
    "semanage login -l",
    "semanage port -a -t",
    "semanage port -d -t",
    "semanage port -l",
    "semanage port -l |",
    "semanage port -m -t",
    "semanage user -l",
    "sestatus",
    "setsebool -P",
    "setsebool -P httpd_c",
    "setsebool -P samba_e",
    "setsebool httpd_can_",
    "touch /.autorelabel"
  ],
  "semanage": [
    "semanage boolean -l",
    "semanage fcontext -a",
    "semanage fcontext -d",
    "semanage fcontext -l",
    "semanage fcontext -m",
    "semanage login -a -s",
    "semanage login -l",
    "semanage port -a -t",
    "semanage port -d -t",
    "semanage port -l",
    "semanage port -l |",
    "semanage port -m -t",
    "semanage user -l"
  ],
  "sensors": [
    "sensors"
  ],
  "sensors-detect": [
    "sensors-detect"
  ],
  "server": [
    "server:/share"
  ],
  "service": [
    "--type=service",
    "service"
  ],
  "sestatus": [
    "sestatus"
  ],
  "set": [
    "ip link set eth0 down",
    "ip link set eth0 mtu",
    "ip link set eth0 up",
    "set"
  ],
  "set-default": [
    "set-default"
  ],
  "setsebool": [
    "setsebool -P",
    "setsebool -P httpd_c",
    "setsebool -P samba_e",
    "setsebool httpd_can_"
  ],
  "show": [
    "ip -6 addr show",
    "ip -6 route show",
    "ip -s link show eth0",
    "ip addr show",
    "ip addr show eth0",
    "ip link show",
    "ip neigh show",
    "ip route show",
    "nmcli device show",
    "systemctl show",
    "systemctl show -p"
  ],
  "sie": [
    "9000",
    "PID",
    "cat /etc/hostname",
    "cat /etc/hosts",
    "cat /etc/resolv.conf",
    "cat /etc/sysconfig/n",
    "curl",
    "established",
    "hostname",
    "ip -6 addr show",
    "ip -6 route show",
    "ip addr",
    "ip addr add",
    "ip addr del",
    "ip addr show",
    "ip addr show eth0",
    "ip link set eth0 down",
    "ip link set eth0 mtu",
    "ip link set eth0 up",
    "ip link show",
    "ip neigh flush all",
    "ip neigh show",
    "ip route add",
    "ip route add default",
    "ip route del",
    "ip route del default",
    "ip route get 8.8.8.8",
    "ip route show",
    "nmcli connection",
    "nmcli connection add",
    "nmcli connection up",
    "nmcli device show",
    "nmcli device status",
    "nmcli general",
    "nmcli radio wifi off",
    "nmtui",
    "procesami"
  ],
  "skrypty": [
    "$#",
    "$$",
    "$0",
    "$?",
    "$@",
    "./script.sh",
    "1>/dev/null",
    "2>/dev/null",
    "ARRAY+=('e')",
    "TMPFILE=$(mktemp)",
    "VAR=$(command)",
    "VAR='value'",
    "break",
    "chmod +x script.sh",
    "continue",
    "do",
    "done",
    "echo \"Value: $VAR\"",
    "echo ${MAP[k1]}",
    "else",
    "esac",
    "fi",
    "mktemp",
    "then",
    "}"
  ],
  "smbclient": [
    "smbclient"
  ],
  "soft": [
    "mount -o ro,soft"
  ],
  "source": [
    "cp source dest",
    "source"
  ],
  "src": [
    "cp --backup src dst",
    "cp -i src dst",
    "cp -p src dst",
    "cp -u src dst",
    "cp -v src dst",
    "podman cp src",
    "podman tag src:tag"
  ],
  "src/": [
    "cp -a src/ dst/",
    "cp -r src/ dst/",
    "rsync --delete src/",
    "rsync -av src/ dst/",
    "rsync -avz src/",
    "rsync -n src/ dst/"
  ],
  "ssh": [
    "4096",
    "8080:localhost:80",
    "Checking=no",
    "ConnectTimeout=10",
    "cat ~/.ssh/config",
    "chmod 600 ~/.ssh/aut",
    "chmod 700 ~/.ssh/",
    "ed25519",
    "horized_keys",
    "ntication=no",
    "rsync -avz",
    "rsync -avz -e ssh",
    "scp",
    "ssh -A user@host",
    "ssh -D 1080",
    "ssh -J jumphost",
    "ssh -L",
    "ssh -N -f -L",
    "ssh -R",
    "ssh -X user@host",
    "ssh -i",
    "ssh -o",
    "ssh -o BatchMode=yes",
    "ssh -o PasswordAuthe",
    "ssh -o PreferredAuth",
    "ssh -o StrictHostKey",
    "ssh -p 2222",
    "ssh -t user@host",
    "ssh -v user@host",
    "ssh -vvv user@host",
    "ssh user@hostname",
    "ssh-add",
    "ssh-copy-id",
    "user@host",
    "user@hostname",
    "~/.ssh/id_rsa",
    "~/.ssh/id_rsa.pub",
    "~/.ssh/key.pem",
    "~/.ssh/mykey"
  ],
  "ssh-add": [
    "ssh-add"
  ],
  "ssh-copy-id": [
    "ssh-copy-id"
  ],
  "sshd": [
    "journalctl -u sshd"
  ],
  "start": [
    "podman machine start",
    "podman pod start",
    "podman start",
    "systemctl start"
  ],
  "stats": [
    "podman pod stats",
    "podman stats"
  ],
  "status": [
    "nmcli device status",
    "systemctl status"
  ],
  "stop": [
    "podman pod stop",
    "podman stop",
    "podman stop -t 0",
    "systemctl stop"
  ],
  "stricthostkey": [
    "ssh -o StrictHostKey"
  ],
  "subscription-manager": [
    "subscription-manager"
  ],
  "sum+": [
    "awk '{sum+=$1}"
  ],
  "suspend": [
    "systemctl suspend"
  ],
  "sync": [
    "sync"
  ],
  "sysctl": [
    "sysctl"
  ],
  "system": [
    "podman system df",
    "podman system prune",
    "podman system reset"
  ],
  "systemctl": [
    "systemctl",
    "systemctl --user",
    "systemctl cat",
    "systemctl disable",
    "systemctl edit",
    "systemctl emergency",
    "systemctl enable",
    "systemctl halt",
    "systemctl hibernate",
    "systemctl is-active",
    "systemctl is-enabled",
    "systemctl is-failed",
    "systemctl isolate",
    "systemctl list-units",
    "systemctl mask",
    "systemctl poweroff",
    "systemctl reboot",
    "systemctl reload",
    "systemctl rescue",
    "systemctl restart",
    "systemctl show",
    "systemctl show -p",
    "systemctl start",
    "systemctl status",
    "systemctl stop",
    "systemctl suspend",
    "systemctl unmask"
  ],
  "systemd": [
    "--type=service",
    "--vacuum-size=500M",
    "daemon-reexec",
    "daemon-reload",
    "emergency.target",
    "get-default",
    "hostnamectl",
    "journalctl",
    "journalctl --since",
    "journalctl --until",
    "journalctl -b",
    "journalctl -b -1",
    "journalctl -f",
    "journalctl -f -u",
    "journalctl -k",
    "journalctl -n 50",
    "journalctl -o json",
    "journalctl -p",
    "journalctl -p err",
    "journalctl -u",
    "list-dependencies",
    "list-unit-files",
    "localectl",
    "loginctl",
    "rescue.target",
    "service",
    "set-default",
    "systemctl",
    "systemctl --user",
    "systemctl cat",
    "systemctl disable",
    "systemctl edit",
    "systemctl enable",
    "systemctl halt",
    "systemctl hibernate",
    "systemctl is-active",
    "systemctl is-enabled",
    "systemctl is-failed",
    "systemctl isolate",
    "systemctl list-units",
    "systemctl mask",
    "systemctl poweroff",
    "systemctl reboot",
    "systemctl reload",
    "systemctl restart",
    "systemctl show",
    "systemctl show -p",
    "systemctl start",
    "systemctl status",
    "systemctl stop",
    "systemctl suspend",
    "systemctl unmask",
    "systemd-analyze",
    "timedatectl"
  ],
  "systemd-analyze": [
    "systemd-analyze"
  ],
  "systemd-cgls": [
    "systemd-cgls"
  ],
  "systemd-cgtop": [
    "systemd-cgtop"
  ],
  "systemd-run": [
    "systemd-run"
  ],
  "systemie": [
    "baseboard",
    "basename",
    "cat /etc/os-release",
    "cat /proc/cpuinfo",
    "cat /proc/uptime",
    "cat /sys/block/sda/q",
    "cat /sys/class/dmi/i",
    "cd -",
    "cd /",
    "cd /path/to/dir",
    "cd ~",
    "dirname",
    "dirs",
    "echo $HOME",
    "echo $OLDPWD",
    "echo $PATH",
    "echo $PWD",
    "iostat",
    "ls",
    "ls --color=auto",
    "ls -R",
    "ls -d */",
    "ls -i",
    "ls -l",
    "ls -lS",
    "ls -la",
    "ls -lh",
    "ls -lt",
    "ls /etc | head -20",
    "ls /proc | wc -l",
    "lscpu",
    "lshw",
    "lsmem",
    "lsnuma",
    "lspci",
    "lsusb",
    "nproc",
    "popd",
    "pwd",
    "sensors",
    "sensors-detect",
    "tree",
    "vmstat"
  ],
  "systemowe": [
    "--filename=/tmp/test",
    "--leak-check=full",
    "/var/log/sa/saDD",
    "bonnie++",
    "cat /etc/kdump.conf",
    "cat /proc/PID/limits",
    "cat /proc/net/tcp",
    "cat /proc/net/udp",
    "cat /proc/sys/net/nf",
    "cmd",
    "count=1000",
    "fio",
    "ip -s link show eth0",
    "kdump",
    "valgrind"
  ],
  "systemu": [
    "--disk-usage",
    "--level=err,warn",
    "/var/log/messages",
    "aureport",
    "cat /etc/audit/audit",
    "cat /var/log/cron",
    "cat /var/log/maillog",
    "cat /var/log/secure",
    "dmesg",
    "grep 'Accepted'",
    "grep 'Failed",
    "journalctl -o",
    "journalctl -u sshd",
    "journalctl -xe",
    "ls /etc/logrotate.d/",
    "udit.log"
  ],
  "systemy": [
    "/dev/sdb1",
    "/mnt",
    "cat /etc/fstab",
    "cat /proc/mounts",
    "findmnt",
    "montowania",
    "mount -a",
    "mount -o remount,ro",
    "mount -o remount,rw",
    "mount -o ro",
    "mount -o rw,noexec",
    "mount -t ext4",
    "mount -t xfs",
    "mount /dev/sdb1 /mnt",
    "mount LABEL=mylabel",
    "mount UUID=xxx /mnt",
    "mount | column -t"
  ],
  "sysuser": [
    "useradd -r sysuser"
  ],
  "t_in_bytes": [
    "t_in_bytes=512M"
  ],
  "tag": [
    "dst:tag",
    "image:tag",
    "podman tag src:tag"
  ],
  "tar": [
    "tar",
    "tar --delete -f",
    "tar --exclude-vcs",
    "tar -cvJf",
    "tar -cvf archive.tar",
    "tar -cvjf",
    "tar -cvzf",
    "tar -czf - /path |",
    "tar -czf arch.tar.gz",
    "tar -rvf archive.tar",
    "tar -tvf archive.tar",
    "tar -tvzf",
    "tar -uvf archive.tar",
    "tar -xvJf",
    "tar -xvf archive.tar",
    "tar -xvjf",
    "tar -xvzf"
  ],
  "tekstowe": [
    "100))",
    "32",
    "cat /etc/chrony.conf",
    "date",
    "echo $((RANDOM %",
    "echo '3.14 * 2' | bc",
    "echo file{1..3}.txt",
    "echo {1..5}",
    "echo {a,b,c}.log",
    "gpg",
    "hwclock"
  ],
  "tekstu": [
    "/dir",
    "awk '/pattern/' file",
    "awk 'END{print NR}'",
    "awk 'NR==5' file",
    "awk 'NR>=5 &&",
    "awk '{print $1}'",
    "awk '{print $NF}'",
    "awk '{print NF}'",
    "awk '{sum+=$1}",
    "awk -F: '{print $1}'",
    "awk -v FS=':'",
    "file",
    "grep",
    "grep 'pattern' file",
    "grep -A 3 'pattern'",
    "grep -B 3 'pattern'",
    "grep -C 3 'pattern'",
    "grep -E 'pat1|pat2'",
    "grep -F 'literal'",
    "grep -P '\\d+' file",
    "grep -c 'pattern'",
    "grep -i 'pattern'",
    "grep -l 'pattern'",
    "grep -m 5 'pattern'",
    "grep -n 'pattern'",
    "grep -o 'pattern'",
    "grep -q 'pattern'",
    "grep -r 'pattern'",
    "grep -v 'pattern'",
    "grep -w 'word' file"
  ],
  "tem/myapp.timer": [
    "tem/myapp.timer"
  ],
  "testparm": [
    "testparm"
  ],
  "then": [
    "then"
  ],
  "timedatectl": [
    "timedatectl"
  ],
  "timer-name.timer": [
    "timer-name.timer"
  ],
  "tmpfile": [
    "TMPFILE=$(mktemp)"
  ],
  "top": [
    "podman top container",
    "top"
  ],
  "touch": [
    "touch -d",
    "touch -t",
    "touch /.autorelabel",
    "touch file.txt"
  ],
  "tree": [
    "tree"
  ],
  "true": [
    "true"
  ],
  "trusted": [
    "efault-zone=trusted"
  ],
  "trwa": [
    "trwa■e)"
  ],
  "u": [
    "cat /etc/group",
    "cat /etc/gshadow",
    "cat /etc/passwd",
    "cat /etc/shadow",
    "chmod u=rwx,g=rx,o=r",
    "dniach",
    "grpck",
    "id",
    "last",
    "lastb",
    "lastlog",
    "lslogins",
    "pwck",
    "trwa■e)",
    "u",
    "user",
    "useradd -G g1,g2",
    "useradd -M user",
    "useradd -N user",
    "useradd -c 'Imi■",
    "useradd -d",
    "useradd -e",
    "useradd -f 30 user",
    "useradd -g group",
    "useradd -m -s",
    "useradd -m username",
    "useradd -r sysuser",
    "useradd -u 1500 user",
    "useradd username",
    "usermod -G g1,g2",
    "usermod -L user",
    "usermod -U user",
    "usermod -aG group",
    "usermod -c 'Nowy",
    "usermod -d /new/home",
    "usermod -e",
    "usermod -e '' user",
    "usermod -g group",
    "usermod -l newname",
    "usermod -s /bin/zsh",
    "usermod -u 1600 user",
    "u■ytkownika",
    "vigr",
    "vipw",
    "visudo",
    "w",
    "who",
    "whoami",
    "zalogowanego"
  ],
  "u+s": [
    "chmod u+s file"
  ],
  "u+x": [
    "chmod u+x file"
  ],
  "udit.log": [
    "udit.log"
  ],
  "ugami": [
    "--type=service",
    "--vacuum-size=500M",
    "daemon-reexec",
    "daemon-reload",
    "emergency.target",
    "get-default",
    "hostnamectl",
    "journalctl",
    "journalctl --since",
    "journalctl --until",
    "journalctl -b",
    "journalctl -b -1",
    "journalctl -f",
    "journalctl -f -u",
    "journalctl -k",
    "journalctl -n 50",
    "journalctl -o json",
    "journalctl -p",
    "journalctl -p err",
    "journalctl -u",
    "list-dependencies",
    "list-unit-files",
    "localectl",
    "loginctl",
    "rescue.target",
    "service",
    "set-default",
    "systemctl",
    "systemctl --user",
    "systemctl cat",
    "systemctl disable",
    "systemctl edit",
    "systemctl enable",
    "systemctl halt",
    "systemctl hibernate",
    "systemctl is-active",
    "systemctl is-enabled",
    "systemctl is-failed",
    "systemctl isolate",
    "systemctl list-units",
    "systemctl mask",
    "systemctl poweroff",
    "systemctl reboot",
    "systemctl reload",
    "systemctl restart",
    "systemctl show",
    "systemctl show -p",
    "systemctl start",
    "systemctl status",
    "systemctl stop",
    "systemctl suspend",
    "systemctl unmask",
    "systemd-analyze",
    "timedatectl"
  ],
  "umask": [
    "umask"
  ],
  "undo": [
    "dnf history undo 5"
  ],
  "unmask": [
    "systemctl unmask"
  ],
  "unpause": [
    "podman unpause"
  ],
  "unshare": [
    "podman unshare"
  ],
  "up": [
    "ip link set eth0 up",
    "nmcli connection up"
  ],
  "update": [
    "dnf security update",
    "dnf update",
    "dnf update package"
  ],
  "update-alternatives": [
    "update-alternatives"
  ],
  "update-crypto-polici": [
    "update-crypto-polici"
  ],
  "updatedb": [
    "updatedb"
  ],
  "updateinfo": [
    "dnf updateinfo list"
  ],
  "updates": [
    "dnf list updates"
  ],
  "upgrade": [
    "dnf upgrade"
  ],
  "upgrade-minimal": [
    "dnf upgrade-minimal"
  ],
  "uprawnienia": [
    "chmod",
    "chmod +t dir",
    "chmod -R 755 dir/",
    "chmod 1755 dir",
    "chmod 2755 dir",
    "chmod 4755 file",
    "chmod 600 file",
    "chmod 644 file",
    "chmod 755 file",
    "chmod 777 file",
    "chmod a+r file",
    "chmod g+s dir",
    "chmod g-w file",
    "chmod o-r file",
    "chmod u+s file",
    "chmod u+x file",
    "chmod u=rwx,g=rx,o=r",
    "chown",
    "chown -R user:group",
    "chown :group file",
    "chown user file",
    "chown user:group",
    "dir/",
    "find / -perm -2000",
    "find / -perm -4000",
    "find / -perm -o+w",
    "katalogu",
    "ls -Z file",
    "umask",
    "w■a■ciciel)",
    "w■a■ciciela"
  ],
  "uptime": [
    "uptime"
  ],
  "us": [
    "--type=service",
    "--vacuum-size=500M",
    "daemon-reexec",
    "daemon-reload",
    "emergency.target",
    "get-default",
    "hostnamectl",
    "journalctl",
    "journalctl --since",
    "journalctl --until",
    "journalctl -b",
    "journalctl -b -1",
    "journalctl -f",
    "journalctl -f -u",
    "journalctl -k",
    "journalctl -n 50",
    "journalctl -o json",
    "journalctl -p",
    "journalctl -p err",
    "journalctl -u",
    "list-dependencies",
    "list-unit-files",
    "localectl",
    "loginctl",
    "rescue.target",
    "service",
    "set-default",
    "systemctl",
    "systemctl --user",
    "systemctl cat",
    "systemctl disable",
    "systemctl edit",
    "systemctl enable",
    "systemctl halt",
    "systemctl hibernate",
    "systemctl is-active",
    "systemctl is-enabled",
    "systemctl is-failed",
    "systemctl isolate",
    "systemctl list-units",
    "systemctl mask",
    "systemctl poweroff",
    "systemctl reboot",
    "systemctl reload",
    "systemctl restart",
    "systemctl show",
    "systemctl show -p",
    "systemctl start",
    "systemctl status",
    "systemctl stop",
    "systemctl suspend",
    "systemctl unmask",
    "systemd-analyze",
    "timedatectl"
  ],
  "user": [
    "chown -R user:group",
    "chown user file",
    "chown user:group",
    "podman run -u user",
    "semanage user -l",
    "ssh -A user@host",
    "ssh -X user@host",
    "ssh -t user@host",
    "ssh -v user@host",
    "ssh -vvv user@host",
    "ssh user@hostname",
    "user",
    "user@host",
    "user@hostname",
    "useradd -M user",
    "useradd -N user",
    "useradd -f 30 user",
    "useradd -u 1500 user",
    "usermod -L user",
    "usermod -U user",
    "usermod -e '' user",
    "usermod -u 1600 user"
  ],
  "useradd": [
    "useradd -G g1,g2",
    "useradd -M user",
    "useradd -N user",
    "useradd -c 'Imi■",
    "useradd -d",
    "useradd -e",
    "useradd -f 30 user",
    "useradd -g group",
    "useradd -m -s",
    "useradd -m username",
    "useradd -r sysuser",
    "useradd -u 1500 user",
    "useradd username"
  ],
  "usermod": [
    "usermod -G g1,g2",
    "usermod -L user",
    "usermod -U user",
    "usermod -aG docker",
    "usermod -aG group",
    "usermod -aG wheel",
    "usermod -c 'Nowy",
    "usermod -d /new/home",
    "usermod -e",
    "usermod -e '' user",
    "usermod -g group",
    "usermod -l newname",
    "usermod -s /bin/zsh",
    "usermod -u 1600 user"
  ],
  "username": [
    "useradd -m username",
    "useradd username"
  ],
  "uuid": [
    "mount UUID=xxx /mnt"
  ],
  "v": [
    "V",
    "v"
  ],
  "valgrind": [
    "valgrind"
  ],
  "value": [
    "VAR='value'",
    "echo \"Value: $VAR\""
  ],
  "var": [
    "VAR=$(command)",
    "VAR='value'"
  ],
  "vgdisplay": [
    "vgdisplay"
  ],
  "vgs": [
    "vgs"
  ],
  "vgscan": [
    "vgscan"
  ],
  "vigr": [
    "vigr"
  ],
  "vim": [
    "$",
    "*",
    "/pattern",
    "0",
    "10G",
    "5dd",
    "5yy",
    "?pattern",
    "A",
    "Ctrl+b",
    "Ctrl+d",
    "Ctrl+f",
    "Ctrl+r",
    "Ctrl+u",
    "Ctrl+v",
    "D",
    "Esc",
    "G",
    "I",
    "N",
    "O",
    "P",
    "R",
    "V",
    "X",
    "ZQ",
    "ZZ",
    "a",
    "b",
    "c$",
    "cat ~/.vimrc",
    "cc",
    "cw",
    "d$",
    "d0",
    "dd",
    "dw",
    "e",
    "gT",
    "gU",
    "gg",
    "gt",
    "gu",
    "i",
    "n",
    "o",
    "p",
    "q",
    "qa",
    "r",
    "u",
    "v",
    "vim +/pattern",
    "vim +10 file.txt",
    "vim -R file.txt",
    "vim -d file1 file2",
    "vim -u NONE file.txt",
    "vim file.txt",
    "x",
    "yy"
  ],
  "vipw": [
    "vipw"
  ],
  "visudo": [
    "visudo"
  ],
  "vmstat": [
    "vmstat"
  ],
  "volume": [
    "/dev/sdb",
    "/dev/sdc",
    "lvdisplay",
    "lvmdiskscan",
    "lvremove",
    "lvs",
    "lvscan",
    "newname",
    "partycji)",
    "podman volume",
    "podman volume create",
    "podman volume ls",
    "podman volume prune",
    "podman volume rm",
    "pvdisplay",
    "pvs",
    "pvscan",
    "vgdisplay",
    "vgs",
    "vgscan"
  ],
  "w": [
    "chmod",
    "chmod +t dir",
    "chmod -R 755 dir/",
    "chmod 1755 dir",
    "chmod 2755 dir",
    "chmod 4755 file",
    "chmod 600 file",
    "chmod 644 file",
    "chmod 755 file",
    "chmod 777 file",
    "chmod a+r file",
    "chmod g+s dir",
    "chmod g-w file",
    "chmod o-r file",
    "chmod u+s file",
    "chmod u+x file",
    "chmod u=rwx,g=rx,o=r",
    "chown",
    "chown -R user:group",
    "chown :group file",
    "chown user file",
    "chown user:group",
    "dir/",
    "find / -perm -2000",
    "find / -perm -4000",
    "find / -perm -o+w",
    "katalogu",
    "ls -Z file",
    "umask",
    "w",
    "w■a■ciciel)",
    "w■a■ciciela",
    "w■■czona"
  ],
  "wait": [
    "wait"
  ],
  "warn": [
    "--level=err,warn"
  ],
  "wc": [
    "ls /proc | wc -l"
  ],
  "whatprovides": [
    "dnf whatprovides"
  ],
  "wheel": [
    "usermod -aG wheel"
  ],
  "who": [
    "who"
  ],
  "whoami": [
    "whoami"
  ],
  "wifi": [
    "nmcli radio wifi off"
  ],
  "wireshark": [
    "wireshark"
  ],
  "word": [
    "grep -w 'word' file"
  ],
  "wyszukiwanie": [
    "/dir",
    "awk '/pattern/' file",
    "awk 'END{print NR}'",
    "awk 'NR==5' file",
    "awk 'NR>=5 &&",
    "awk '{print $1}'",
    "awk '{print $NF}'",
    "awk '{print NF}'",
    "awk '{sum+=$1}",
    "awk -F: '{print $1}'",
    "awk -v FS=':'",
    "file",
    "find . ! -name",
    "find . -atime -1",
    "find . -ctime -1",
    "find . -empty",
    "find . -gid 1000",
    "find . -group",
    "find . -iname",
    "find . -links +1",
    "find . -maxdepth 2",
    "find . -mindepth 2",
    "find . -mmin -60",
    "find . -mount -name",
    "find . -mtime +30",
    "find . -mtime -7",
    "find . -name",
    "find . -name '*.log'",
    "find . -name '*.py'",
    "find . -name '*.tmp'",
    "find . -name '*.txt'",
    "find . -newer",
    "find . -nogroup",
    "find . -nouser",
    "find . -perm -1000",
    "find . -perm -2000",
    "find . -perm -4000",
    "find . -perm -644",
    "find . -perm /644",
    "find . -perm 644",
    "find . -size +100M",
    "find . -size +1G",
    "find . -size -10k",
    "find . -size 512c",
    "find . -type f -name",
    "find . -type f -newer",
    "find . -uid 1000",
    "find . -user",
    "find . -xdev -name",
    "find / -inum 12345",
    "find / -name",
    "find / -type b",
    "find / -type c",
    "find / -type d -name",
    "find / -type f -name",
    "find / -type l",
    "find /tmp -mtime +7",
    "grep",
    "grep 'pattern' file",
    "grep -A 3 'pattern'",
    "grep -B 3 'pattern'",
    "grep -C 3 'pattern'",
    "grep -E 'pat1|pat2'",
    "grep -F 'literal'",
    "grep -P '\\d+' file",
    "grep -c 'pattern'",
    "grep -i 'pattern'",
    "grep -l 'pattern'",
    "grep -m 5 'pattern'",
    "grep -n 'pattern'",
    "grep -o 'pattern'",
    "grep -q 'pattern'",
    "grep -r 'pattern'",
    "grep -v 'pattern'",
    "grep -w 'word' file",
    "reference_file",
    "updatedb"
  ],
  "x": [
    "X",
    "x"
  ],
  "x86_64-efi": [
    "--target=x86_64-efi"
  ],
  "xfs": [
    "mount -t xfs"
  ],
  "xxx": [
    "mount UUID=xxx /mnt"
  ],
  "yes": [
    "ssh -o BatchMode=yes"
  ],
  "ytkownika": [
    "u■ytkownika"
  ],
  "ytkownikami": [
    "cat /etc/group",
    "cat /etc/gshadow",
    "cat /etc/passwd",
    "cat /etc/shadow",
    "dniach",
    "grpck",
    "id",
    "last",
    "lastb",
    "lastlog",
    "lslogins",
    "pwck",
    "trwa■e)",
    "user",
    "useradd -G g1,g2",
    "useradd -M user",
    "useradd -N user",
    "useradd -c 'Imi■",
    "useradd -d",
    "useradd -e",
    "useradd -f 30 user",
    "useradd -g group",
    "useradd -m -s",
    "useradd -m username",
    "useradd -r sysuser",
    "useradd -u 1500 user",
    "useradd username",
    "usermod -G g1,g2",
    "usermod -L user",
    "usermod -U user",
    "usermod -aG group",
    "usermod -c 'Nowy",
    "usermod -d /new/home",
    "usermod -e",
    "usermod -e '' user",
    "usermod -g group",
    "usermod -l newname",
    "usermod -s /bin/zsh",
    "usermod -u 1600 user",
    "vigr",
    "vipw",
    "visudo",
    "w",
    "who",
    "whoami",
    "zalogowanego"
  ],
  "yy": [
    "yy"
  ],
  "zaawansowane": [
    "100))",
    "32",
    "cat /etc/chrony.conf",
    "date",
    "echo $((RANDOM %",
    "echo '3.14 * 2' | bc",
    "echo file{1..3}.txt",
    "echo {1..5}",
    "echo {a,b,c}.log",
    "gpg",
    "hwclock"
  ],
  "zada": [
    "/etc/cron.daily",
    "atq",
    "batch",
    "cat /etc/anacrontab",
    "cat /etc/at.allow",
    "cat /etc/at.deny",
    "cat /etc/cron.allow",
    "cat /etc/cron.deny",
    "cat /etc/crontab",
    "cat /etc/systemd/sys",
    "cat /var/spool/cron/",
    "list-timers",
    "ls /etc/cron.d/",
    "ls /etc/cron.daily/",
    "ls /etc/cron.hourly/",
    "ls /etc/cron.weekly/",
    "myapp.timer",
    "run-parts",
    "systemd-run",
    "tem/myapp.timer",
    "timer-name.timer"
  ],
  "zalogowanego": [
    "zalogowanego"
  ],
  "zapora": [
    "--add-port=8080/tcp",
    "--add-service=http",
    "--add-service=https",
    "--complete-reload",
    "--get-active-zones",
    "--get-default-zone",
    "--get-zones",
    "--list-all",
    "--list-ports",
    "--list-rich-rules",
    "--list-services",
    "--zone=public",
    "e-port=8080/tcp",
    "e-service=http",
    "efault-zone=trusted",
    "firewall-cmd",
    "firewall-cmd --add-f",
    "firewall-cmd --add-p",
    "firewall-cmd --add-r",
    "firewall-cmd --remov",
    "firewall-cmd --runti",
    "firewall-cmd --set-d",
    "firewall-cmd --state",
    "firewalld",
    "w■■czona"
  ],
  "zarz": [
    "--raid-devices=2",
    "--scan",
    "--type=service",
    "--vacuum-size=500M",
    "/dev/md0",
    "/dev/sdd",
    "Ctrl+C",
    "Ctrl+D",
    "Ctrl+Z",
    "Name'",
    "aktualizacjami",
    "cat /etc/group",
    "cat /etc/gshadow",
    "cat /etc/mdadm.conf",
    "cat /etc/passwd",
    "cat /etc/shadow",
    "cat /proc/PID/maps",
    "cat /proc/PID/status",
    "cat /proc/loadavg",
    "cat /proc/mdstat",
    "cat /proc/meminfo",
    "daemon-reexec",
    "daemon-reload",
    "dnf autoremove",
    "dnf check-update",
    "dnf clean all",
    "dnf clean metadata",
    "dnf clean packages",
    "dnf config-manager",
    "dnf distro-sync",
    "dnf downgrade",
    "dnf erase package",
    "dnf groupinfo 'Group",
    "dnf groupinstall",
    "dnf grouplist",
    "dnf groupremove",
    "dnf history",
    "dnf history info 5",
    "dnf history redo 5",
    "dnf history rollback",
    "dnf history undo 5",
    "dnf info package",
    "dnf install -y",
    "dnf install package",
    "dnf list available",
    "dnf list extras",
    "dnf list installed",
    "dnf list obsoletes",
    "dnf list updates",
    "dnf makecache",
    "dnf module disable",
    "dnf module enable",
    "dnf module info",
    "dnf module install m",
    "dnf module list",
    "dnf module reset",
    "dnf provides",
    "dnf reinstall",
    "dnf remove package",
    "dnf repoinfo repo-id",
    "dnf repolist",
    "dnf repolist all",
    "dnf search keyword",
    "dnf security update",
    "dnf update",
    "dnf update package",
    "dnf updateinfo list",
    "dnf upgrade",
    "dnf upgrade-minimal",
    "dnf whatprovides",
    "dniach",
    "emergency.target",
    "get-default",
    "group",
    "grpck",
    "hostnamectl",
    "htop",
    "id",
    "jobs",
    "journalctl",
    "journalctl --since",
    "journalctl --until",
    "journalctl -b",
    "journalctl -b -1",
    "journalctl -f",
    "journalctl -f -u",
    "journalctl -k",
    "journalctl -n 50",
    "journalctl -o json",
    "journalctl -p",
    "journalctl -p err",
    "journalctl -u",
    "last",
    "lastb",
    "lastlog",
    "list-dependencies",
    "list-unit-files",
    "localectl",
    "loginctl",
    "lslogins",
    "lsof",
    "mdadm",
    "package",
    "ps",
    "pstree",
    "pwck",
    "rescue.target",
    "rpm --import",
    "rpm -Fvh package.rpm",
    "rpm -K package.rpm",
    "rpm -Uvh package.rpm",
    "rpm -V package",
    "rpm -Va",
    "rpm -e package",
    "rpm -ivh package.rpm",
    "rpm -q --changelog",
    "rpm -q --scripts",
    "rpm -qR package",
    "rpm -qa",
    "rpm -qc package",
    "rpm -qd package",
    "rpm -qf",
    "rpm -qi package",
    "rpm -qip package.rpm",
    "rpm -ql package",
    "rpm -qp --scripts",
    "service",
    "set-default",
    "subscription-manager",
    "systemctl",
    "systemctl --user",
    "systemctl cat",
    "systemctl disable",
    "systemctl edit",
    "systemctl enable",
    "systemctl halt",
    "systemctl hibernate",
    "systemctl is-active",
    "systemctl is-enabled",
    "systemctl is-failed",
    "systemctl isolate",
    "systemctl list-units",
    "systemctl mask",
    "systemctl poweroff",
    "systemctl reboot",
    "systemctl reload",
    "systemctl restart",
    "systemctl show",
    "systemctl show -p",
    "systemctl start",
    "systemctl status",
    "systemctl stop",
    "systemctl suspend",
    "systemctl unmask",
    "systemd-analyze",
    "timedatectl",
    "top",
    "trwa■e)",
    "uptime",
    "user",
    "useradd -G g1,g2",
    "useradd -M user",
    "useradd -N user",
    "useradd -c 'Imi■",
    "useradd -d",
    "useradd -e",
    "useradd -f 30 user",
    "useradd -g group",
    "useradd -m -s",
    "useradd -m username",
    "useradd -r sysuser",
    "useradd -u 1500 user",
    "useradd username",
    "usermod -G g1,g2",
    "usermod -L user",
    "usermod -U user",
    "usermod -aG docker",
    "usermod -aG group",
    "usermod -aG wheel",
    "usermod -c 'Nowy",
    "usermod -d /new/home",
    "usermod -e",
    "usermod -e '' user",
    "usermod -g group",
    "usermod -l newname",
    "usermod -s /bin/zsh",
    "usermod -u 1600 user",
    "u■ytkownika",
    "vigr",
    "vipw",
    "visudo",
    "w",
    "wait",
    "who",
    "whoami",
    "zalogowanego"
  ],
  "zawarto": [
    "cat -A file.txt",
    "cat -n file.txt",
    "cat file.txt",
    "cat file1 file2"
  ],
  "zdalny": [
    "4096",
    "8080:localhost:80",
    "Checking=no",
    "ConnectTimeout=10",
    "cat ~/.ssh/config",
    "chmod 600 ~/.ssh/aut",
    "chmod 700 ~/.ssh/",
    "ed25519",
    "horized_keys",
    "ntication=no",
    "rsync -avz",
    "rsync -avz -e ssh",
    "scp",
    "ssh -A user@host",
    "ssh -D 1080",
    "ssh -J jumphost",
    "ssh -L",
    "ssh -N -f -L",
    "ssh -R",
    "ssh -X user@host",
    "ssh -i",
    "ssh -o",
    "ssh -o BatchMode=yes",
    "ssh -o PasswordAuthe",
    "ssh -o PreferredAuth",
    "ssh -o StrictHostKey",
    "ssh -p 2222",
    "ssh -t user@host",
    "ssh -v user@host",
    "ssh -vvv user@host",
    "ssh user@hostname",
    "ssh-add",
    "ssh-copy-id",
    "user@host",
    "user@hostname",
    "~/.ssh/id_rsa",
    "~/.ssh/id_rsa.pub",
    "~/.ssh/key.pem",
    "~/.ssh/mykey"
  ],
  "zmienne": [
    "Ctrl+R",
    "alias",
    "alias ll='ls -alh'",
    "cat /etc/bashrc",
    "cat /etc/profile",
    "cat ~/.bash_logout",
    "cat ~/.bash_profile",
    "cat ~/.bashrc",
    "complete",
    "echo $!",
    "echo $#",
    "echo $$",
    "echo $*",
    "echo $0",
    "echo $?",
    "echo $@",
    "echo $BASH_VERSION",
    "echo $HISTFILE",
    "echo $HISTFILESIZE",
    "echo $HISTSIZE",
    "echo $PS1",
    "echo $SHELL",
    "echo $VARIABLE",
    "echo ${#ARRAY[@]}",
    "echo ${ARRAY[0]}",
    "echo ${ARRAY[@]}",
    "env",
    "false",
    "hash",
    "history",
    "ls /etc/profile.d/",
    "printenv",
    "set",
    "source",
    "true"
  ],
  "zq": [
    "ZQ"
  ],
  "zz": [
    "ZZ"
  ],
  "~": [
    "cd ~"
  ],
  "~/.bash_logout": [
    "cat ~/.bash_logout"
  ],
  "~/.bash_profile": [
    "cat ~/.bash_profile"
  ],
  "~/.bashrc": [
    "cat ~/.bashrc"
  ],
  "~/.ssh/": [
    "chmod 700 ~/.ssh/"
  ],
  "~/.ssh/aut": [
    "chmod 600 ~/.ssh/aut"
  ],
  "~/.ssh/config": [
    "cat ~/.ssh/config"
  ],
  "~/.ssh/id_rsa": [
    "~/.ssh/id_rsa"
  ],
  "~/.ssh/id_rsa.pub": [
    "~/.ssh/id_rsa.pub"
  ],
  "~/.ssh/key.pem": [
    "~/.ssh/key.pem"
  ],
  "~/.ssh/mykey": [
    "~/.ssh/mykey"
  ],
  "~/.vimrc": [
    "cat ~/.vimrc"
  ]
}
```

## `runtime/knowledge/index/command_index_template.csv`

- size: 92 bytes
- sha256: `adf4f5cd15ee04a69c738d181744a06c5f21667d62c638e7ef580d2658e8bec1`
- category: knowledge

```csv
command,category,description,difficulty,tags,source_page,canonical_source,confidence,status
```

## `runtime/knowledge/injection/injected_context.json`

- size: 202 bytes
- sha256: `66cf4fd7c08590cefe6af64ddb9ed90581e7b9999d76b3ff606168ad28e7e1c6`
- category: knowledge

```json
[
  {
    "query": "network ports",
    "static_context": [
      "Use: podman network",
      "Use: podman network ls",
      "Use: podman network rm"
    ],
    "source": "RHCSA knowledge pack"
  }
]
```

## `runtime/knowledge/lvm/README.md`

- size: 317 bytes
- sha256: `42a87388664e11e3a511741820ab50239feff10f0ca47922a8f1115ba8989137`
- category: knowledge

```markdown
# Lvm

Logical Volume Manager concepts and operational commands.

## Modules

- `lvm/lvm-logical-volume-manager.md`: 15 imported commands from `LVM — Logical Volume Manager`

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
```

## `runtime/knowledge/lvm/lvm-logical-volume-manager.md`

- size: 5854 bytes
- sha256: `8a630a9fcd450aaaba99cf21d247bb8aa74367630aaf797726368d31f66a9b6c`
- category: knowledge

```markdown
---
title: LVM — Logical Volume Manager
topic: lvm
source_section: LVM — Logical Volume Manager
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [linux, lvdisplay, lvm, lvm-logical-volume-manager, lvmdiskscan, lvremove, lvs, lvscan, newname, pvdisplay, pvs, pvscan, rhcsa, vgdisplay, vgs, vgscan]
---

# LVM — Logical Volume Manager

Imported RHCSA material for 15 commands. Primary command families: lvdisplay, lvmdiskscan, lvremove, lvs, lvscan, newname, pvdisplay, pvs.

## Tags

linux, lvdisplay, lvm, lvm-logical-volume-manager, lvmdiskscan, lvremove, lvs, lvscan, newname, pvdisplay, pvs, pvscan, rhcsa, vgdisplay, vgs, vgscan

## Examples

- `pvs`
- `lvs`
- `pvdisplay`
- `lvdisplay`
- `/dev/sdc`
- `partycji)`
- `pvscan`
- `vgs`
- `vgdisplay`
- `lvremove`

## Troubleshooting

- Validate PV/VG/LV layout with `pvs`, `vgs`, and `lvs` before resizing storage.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `LVM — Logical Volume Manager`

## Commands

### `pvs`

- Category: `LVM — Logical Volume Manager`
- Risk: `unclassified`
- Tags: `lvm`, `pvs`
- Examples:
  - `pvs`
- Troubleshooting hint:
  - Validate PV/VG/LV layout with `pvs`, `vgs`, and `lvs` before resizing storage.
- Provenance:
  - RHCSA section: `LVM — Logical Volume Manager`

### `lvs`

- Category: `LVM — Logical Volume Manager`
- Risk: `unclassified`
- Tags: `lvm`, `lvs`
- Examples:
  - `lvs`
- Troubleshooting hint:
  - Validate PV/VG/LV layout with `pvs`, `vgs`, and `lvs` before resizing storage.
- Provenance:
  - RHCSA section: `LVM — Logical Volume Manager`

### `pvdisplay`

- Category: `LVM — Logical Volume Manager`
- Risk: `unclassified`
- Tags: `lvm`, `pvdisplay`
- Examples:
  - `pvdisplay`
- Troubleshooting hint:
  - Validate PV/VG/LV layout with `pvs`, `vgs`, and `lvs` before resizing storage.
- Provenance:
  - RHCSA section: `LVM — Logical Volume Manager`

### `lvdisplay`

- Category: `LVM — Logical Volume Manager`
- Risk: `unclassified`
- Tags: `lvm`, `lvdisplay`
- Examples:
  - `lvdisplay`
- Troubleshooting hint:
  - Validate PV/VG/LV layout with `pvs`, `vgs`, and `lvs` before resizing storage.
- Provenance:
  - RHCSA section: `LVM — Logical Volume Manager`

### `/dev/sdc`

- Category: `LVM — Logical Volume Manager`
- Risk: `unclassified`
- Tags: `lvm`, `dev-sdc`
- Examples:
  - `/dev/sdc`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `LVM — Logical Volume Manager`

### `partycji)`

- Category: `LVM — Logical Volume Manager`
- Risk: `unclassified`
- Tags: `lvm`, `partycji`
- Examples:
  - `partycji)`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `LVM — Logical Volume Manager`

### `pvscan`

- Category: `LVM — Logical Volume Manager`
- Risk: `unclassified`
- Tags: `lvm`, `pvscan`
- Examples:
  - `pvscan`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `LVM — Logical Volume Manager`

### `vgs`

- Category: `LVM — Logical Volume Manager`
- Risk: `unclassified`
- Tags: `lvm`, `vgs`
- Examples:
  - `vgs`
- Troubleshooting hint:
  - Validate PV/VG/LV layout with `pvs`, `vgs`, and `lvs` before resizing storage.
- Provenance:
  - RHCSA section: `LVM — Logical Volume Manager`

### `vgdisplay`

- Category: `LVM — Logical Volume Manager`
- Risk: `unclassified`
- Tags: `lvm`, `vgdisplay`
- Examples:
  - `vgdisplay`
- Troubleshooting hint:
  - Validate PV/VG/LV layout with `pvs`, `vgs`, and `lvs` before resizing storage.
- Provenance:
  - RHCSA section: `LVM — Logical Volume Manager`

### `lvremove`

- Category: `LVM — Logical Volume Manager`
- Risk: `unclassified`
- Tags: `lvm`, `lvremove`
- Examples:
  - `lvremove`
- Troubleshooting hint:
  - Validate PV/VG/LV layout with `pvs`, `vgs`, and `lvs` before resizing storage.
- Provenance:
  - RHCSA section: `LVM — Logical Volume Manager`

### `/dev/sdb`

- Category: `LVM — Logical Volume Manager`
- Risk: `unclassified`
- Tags: `lvm`, `dev-sdb`
- Examples:
  - `/dev/sdb`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `LVM — Logical Volume Manager`

### `newname`

- Category: `LVM — Logical Volume Manager`
- Risk: `unclassified`
- Tags: `lvm`, `newname`
- Examples:
  - `newname`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `LVM — Logical Volume Manager`

### `vgscan`

- Category: `LVM — Logical Volume Manager`
- Risk: `unclassified`
- Tags: `lvm`, `vgscan`
- Examples:
  - `vgscan`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `LVM — Logical Volume Manager`

### `lvscan`

- Category: `LVM — Logical Volume Manager`
- Risk: `unclassified`
- Tags: `lvm`, `lvscan`
- Examples:
  - `lvscan`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `LVM — Logical Volume Manager`

### `lvmdiskscan`

- Category: `LVM — Logical Volume Manager`
- Risk: `unclassified`
- Tags: `lvm`, `lvmdiskscan`
- Examples:
  - `lvmdiskscan`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `LVM — Logical Volume Manager`
```

## `runtime/knowledge/manifests/library_manifest.yaml`

- size: 995 bytes
- sha256: `bdf0a14e5460c31013e519824a2ad7f03d527dafec90def78ec53f77452d4e90`
- category: knowledge

```yaml
library_name: Linux Engineering Knowledge Library
version: 1.0.0
canonical_source: runtime/knowledge/source/linux_master_library_v1.pdf
canonical_source_sha256: 7eab9450dd15cc5e1607c29d9fe3b19c4cf9854bb702f113534b6ec34a34dc03
legacy_source:
  path: runtime/knowledge/source/RHCSA_Command_Library (1).pdf
  sha256: b8092eeabbfd80489d9e5ce8b49ba4d822aa83cc360da0a8f3c76276ac21d6b7
scope:
  - RHCSA
  - RHCE
  - Linux administration
  - Linux engineering
status: canonical master
deterministic_retrieval: planned
provenance_tracking: enabled
update_policy: append-only, deduplicate, versioned
target_future_size: 10000+ commands
storage_decision: reused existing runtime/knowledge structure; no parallel knowledge/linux-engineering tree created
extracted_text:
  txt: runtime/knowledge/extracted/linux_master_library_v1.txt
  md: runtime/knowledge/extracted/linux_master_library_v1.md
index_template: runtime/knowledge/index/command_index_template.csv
notes: imported safely after repository audit
```

## `runtime/knowledge/networking/README.md`

- size: 705 bytes
- sha256: `e2b83637740505d7107bee7223adacf117942644575865ca887f04e64b9f88b8`
- category: knowledge

```markdown
# Networking

Networking, SSH, firewall, remote access, and shared-service connectivity.

## Modules

- `networking/nfs-i-autofs.md`: 14 imported commands from `NFS i Autofs`
- `networking/ssh-i-dostp-zdalny.md`: 39 imported commands from `SSH i dost■p zdalny`
- `networking/samba-i-nfs-klient.md`: 6 imported commands from `Samba i NFS (klient)`
- `networking/sie-konfiguracja-i-diagnostyka.md`: 37 imported commands from `Sie■ — konfiguracja i diagnostyka`
- `networking/zapora-ogniowa-firewalld.md`: 25 imported commands from `Zapora ogniowa (firewalld)`

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
```

## `runtime/knowledge/networking/nfs-i-autofs.md`

- size: 5447 bytes
- sha256: `d0119593a840d2d52ffbf85d70dc1e22e6a1b0702c35b660fa491898fccba574`
- category: knowledge

```markdown
---
title: NFS i Autofs
topic: networking
source_section: NFS i Autofs
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [cat, exportfs, firewall-cmd, linux, ls, mount, networking, nfs-i-autofs, nfs-server, nfsstat, rhcsa]
---

# NFS i Autofs

Imported RHCSA material for 14 commands. Primary command families: cat, exportfs, firewall-cmd, ls, mount, nfs-server, nfsstat.

## Tags

cat, exportfs, firewall-cmd, linux, ls, mount, networking, nfs-i-autofs, nfs-server, nfsstat, rhcsa

## Examples

- `nfsstat`
- `mount -t nfs`
- `mount -t nfs4`
- `mount -o ro,soft`
- `firewall-cmd --add-s`
- `mount -o`
- `nosuid,noexec`
- `cat /etc/auto.master`
- `cat /etc/exports`
- `cat /etc/auto.misc`

## Troubleshooting

- Check interface state, service state, and firewall exposure together during network diagnostics.
- Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `NFS i Autofs`

## Commands

### `nfsstat`

- Category: `NFS i Autofs`
- Risk: `unclassified`
- Tags: `networking`, `nfsstat`
- Examples:
  - `nfsstat`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `NFS i Autofs`

### `mount -t nfs`

- Category: `NFS i Autofs`
- Risk: `unclassified`
- Tags: `networking`, `mount`
- Examples:
  - `mount -t nfs`
- Troubleshooting hint:
  - Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.
- Provenance:
  - RHCSA section: `NFS i Autofs`

### `mount -t nfs4`

- Category: `NFS i Autofs`
- Risk: `unclassified`
- Tags: `networking`, `mount`
- Examples:
  - `mount -t nfs4`
- Troubleshooting hint:
  - Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.
- Provenance:
  - RHCSA section: `NFS i Autofs`

### `mount -o ro,soft`

- Category: `NFS i Autofs`
- Risk: `unclassified`
- Tags: `networking`, `mount`
- Examples:
  - `mount -o ro,soft`
- Troubleshooting hint:
  - Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.
- Provenance:
  - RHCSA section: `NFS i Autofs`

### `firewall-cmd --add-s`

- Category: `NFS i Autofs`
- Risk: `unclassified`
- Tags: `networking`, `firewall-cmd`
- Examples:
  - `firewall-cmd --add-s`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `NFS i Autofs`

### `mount -o`

- Category: `NFS i Autofs`
- Risk: `unclassified`
- Tags: `networking`, `mount`
- Examples:
  - `mount -o`
- Troubleshooting hint:
  - Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.
- Provenance:
  - RHCSA section: `NFS i Autofs`

### `nosuid,noexec`

- Category: `NFS i Autofs`
- Risk: `unclassified`
- Tags: `networking`, `nosuid-noexec`
- Examples:
  - `nosuid,noexec`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `NFS i Autofs`

### `cat /etc/auto.master`

- Category: `NFS i Autofs`
- Risk: `unclassified`
- Tags: `networking`, `cat`
- Examples:
  - `cat /etc/auto.master`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `NFS i Autofs`

### `cat /etc/exports`

- Category: `NFS i Autofs`
- Risk: `unclassified`
- Tags: `networking`, `cat`
- Examples:
  - `cat /etc/exports`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `NFS i Autofs`

### `cat /etc/auto.misc`

- Category: `NFS i Autofs`
- Risk: `unclassified`
- Tags: `networking`, `cat`
- Examples:
  - `cat /etc/auto.misc`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `NFS i Autofs`

### `ls /mnt/nfs/share`

- Category: `NFS i Autofs`
- Risk: `unclassified`
- Tags: `networking`, `ls`
- Examples:
  - `ls /mnt/nfs/share`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `NFS i Autofs`

### `exportfs`

- Category: `NFS i Autofs`
- Risk: `unclassified`
- Tags: `networking`, `exportfs`
- Examples:
  - `exportfs`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `NFS i Autofs`

### `server:/share`

- Category: `NFS i Autofs`
- Risk: `unclassified`
- Tags: `networking`, `server-share`
- Examples:
  - `server:/share`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `NFS i Autofs`

### `nfs-server`

- Category: `NFS i Autofs`
- Risk: `unclassified`
- Tags: `networking`, `nfs-server`
- Examples:
  - `nfs-server`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `NFS i Autofs`
```

## `runtime/knowledge/networking/samba-i-nfs-klient.md`

- size: 2878 bytes
- sha256: `bae608de9b12eed297e23d6f89c47f0163c977e2677b2e3996a029b7bf16c29b`
- category: knowledge

```markdown
---
title: Samba i NFS (klient)
topic: networking
source_section: Samba i NFS (klient)
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [cat, grep, linux, mount, networking, rhcsa, samba-i-nfs-klient, smbclient, testparm]
---

# Samba i NFS (klient)

Imported RHCSA material for 6 commands. Primary command families: cat, grep, mount, smbclient, testparm.

## Tags

cat, grep, linux, mount, networking, rhcsa, samba-i-nfs-klient, smbclient, testparm

## Examples

- `smbclient`
- `//server`
- `testparm`
- `mount -t cifs`
- `cat /etc/fstab |`
- `grep cifs`

## Troubleshooting

- Quote patterns explicitly to avoid shell expansion when matching text.
- Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Samba i NFS (klient)`

## Commands

### `smbclient`

- Category: `Samba i NFS (klient)`
- Risk: `unclassified`
- Tags: `networking`, `smbclient`
- Examples:
  - `smbclient`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Samba i NFS (klient)`

### `//server`

- Category: `Samba i NFS (klient)`
- Risk: `unclassified`
- Tags: `networking`, `server`
- Examples:
  - `//server`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Samba i NFS (klient)`

### `testparm`

- Category: `Samba i NFS (klient)`
- Risk: `unclassified`
- Tags: `networking`, `testparm`
- Examples:
  - `testparm`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Samba i NFS (klient)`

### `mount -t cifs`

- Category: `Samba i NFS (klient)`
- Risk: `unclassified`
- Tags: `networking`, `mount`
- Examples:
  - `mount -t cifs`
- Troubleshooting hint:
  - Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.
- Provenance:
  - RHCSA section: `Samba i NFS (klient)`

### `cat /etc/fstab |`

- Category: `Samba i NFS (klient)`
- Risk: `unclassified`
- Tags: `networking`, `cat`
- Examples:
  - `cat /etc/fstab |`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Samba i NFS (klient)`

### `grep cifs`

- Category: `Samba i NFS (klient)`
- Risk: `unclassified`
- Tags: `networking`, `grep`
- Examples:
  - `grep cifs`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Samba i NFS (klient)`
```

## `runtime/knowledge/networking/sie-konfiguracja-i-diagnostyka.md`

- size: 14374 bytes
- sha256: `2251c1dbbc3d074414c34582bfaf5aebdffdfb2f9dd91630bb158ae81f5faeb6`
- category: knowledge

```markdown
---
title: Sie■ — konfiguracja i diagnostyka
topic: networking
source_section: Sie■ — konfiguracja i diagnostyka
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [cat, curl, established, hostname, ip, linux, networking, nmcli, nmtui, pid, procesami, rhcsa, sie-konfiguracja-i-diagnostyka]
---

# Sie■ — konfiguracja i diagnostyka

Imported RHCSA material for 37 commands. Primary command families: cat, curl, established, hostname, ip, nmcli, nmtui, pid.

## Tags

cat, curl, established, hostname, ip, linux, networking, nmcli, nmtui, pid, procesami, rhcsa, sie-konfiguracja-i-diagnostyka

## Examples

- `ip addr`
- `ip addr show`
- `ip addr show eth0`
- `ip addr add`
- `ip addr del`
- `ip link show`
- `ip link set eth0 up`
- `ip link set eth0 down`
- `curl`
- `ip link set eth0 mtu`

## Troubleshooting

- Check interface state, service state, and firewall exposure together during network diagnostics.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Sie■ — konfiguracja i diagnostyka`

## Commands

### `ip addr`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `ip`
- Examples:
  - `ip addr`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `ip addr show`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `ip`
- Examples:
  - `ip addr show`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `ip addr show eth0`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `ip`
- Examples:
  - `ip addr show eth0`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `ip addr add`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `ip`
- Examples:
  - `ip addr add`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `ip addr del`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `ip`
- Examples:
  - `ip addr del`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `ip link show`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `ip`
- Examples:
  - `ip link show`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `ip link set eth0 up`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `ip`
- Examples:
  - `ip link set eth0 up`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `ip link set eth0 down`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `ip`
- Examples:
  - `ip link set eth0 down`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `curl`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `curl`
- Examples:
  - `curl`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `ip link set eth0 mtu`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `ip`
- Examples:
  - `ip link set eth0 mtu`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `9000`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `9000`
- Examples:
  - `9000`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `ip route show`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `ip`
- Examples:
  - `ip route show`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `ip route add default`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `ip`
- Examples:
  - `ip route add default`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `ip route add`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `ip`
- Examples:
  - `ip route add`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `ip route del default`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `ip`
- Examples:
  - `ip route del default`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `nmcli device show`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `nmcli`
- Examples:
  - `nmcli device show`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `ip route del`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `ip`
- Examples:
  - `ip route del`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `nmcli device status`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `nmcli`
- Examples:
  - `nmcli device status`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `ip route get 8.8.8.8`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `ip`
- Examples:
  - `ip route get 8.8.8.8`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `nmcli connection`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `nmcli`
- Examples:
  - `nmcli connection`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `ip neigh show`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `ip`
- Examples:
  - `ip neigh show`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `ip neigh flush all`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `ip`
- Examples:
  - `ip neigh flush all`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `nmcli connection up`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `nmcli`
- Examples:
  - `nmcli connection up`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `ip -6 addr show`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `ip`
- Examples:
  - `ip -6 addr show`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `ip -6 route show`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `ip`
- Examples:
  - `ip -6 route show`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `nmcli connection add`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `nmcli`
- Examples:
  - `nmcli connection add`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `PID`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `pid`
- Examples:
  - `PID`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `established`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `established`
- Examples:
  - `established`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `procesami`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `procesami`
- Examples:
  - `procesami`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `nmcli general`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `nmcli`
- Examples:
  - `nmcli general`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `nmcli radio wifi off`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `nmcli`
- Examples:
  - `nmcli radio wifi off`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `nmtui`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `nmtui`
- Examples:
  - `nmtui`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `cat /etc/hosts`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `cat`
- Examples:
  - `cat /etc/hosts`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `cat /etc/resolv.conf`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `cat`
- Examples:
  - `cat /etc/resolv.conf`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `cat /etc/hostname`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `cat`
- Examples:
  - `cat /etc/hostname`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `cat /etc/sysconfig/n`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `cat`
- Examples:
  - `cat /etc/sysconfig/n`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`

### `hostname`

- Category: `Sie■ — konfiguracja i diagnostyka`
- Risk: `unclassified`
- Tags: `networking`, `hostname`
- Examples:
  - `hostname`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Sie■ — konfiguracja i diagnostyka`
```

## `runtime/knowledge/networking/ssh-i-dostp-zdalny.md`

- size: 13850 bytes
- sha256: `099ff2ae2228859628c3501f394ebf676057276e130b0839dd145cc76e2447e4`
- category: knowledge

```markdown
---
title: SSH i dost■p zdalny
topic: networking
source_section: SSH i dost■p zdalny
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [cat, chmod, ed25519, horized_keys, linux, networking, rhcsa, rsync, scp, ssh, ssh-add, ssh-copy-id, ssh-i-dostp-zdalny]
---

# SSH i dost■p zdalny

Imported RHCSA material for 39 commands. Primary command families: cat, chmod, ed25519, horized_keys, rsync, scp, ssh, ssh-add.

## Tags

cat, chmod, ed25519, horized_keys, linux, networking, rhcsa, rsync, scp, ssh, ssh-add, ssh-copy-id, ssh-i-dostp-zdalny

## Examples

- `ssh user@hostname`
- `ssh -p 2222`
- `user@hostname`
- `ssh -i`
- `~/.ssh/key.pem`
- `user@host`
- `ssh -v user@host`
- `chmod 600 ~/.ssh/aut`
- `horized_keys`
- `ssh -vvv user@host`

## Troubleshooting

- Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Check interface state, service state, and firewall exposure together during network diagnostics.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `SSH i dost■p zdalny`

## Commands

### `ssh user@hostname`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh`
- Examples:
  - `ssh user@hostname`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ssh -p 2222`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh`
- Examples:
  - `ssh -p 2222`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `user@hostname`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `user-hostname`
- Examples:
  - `user@hostname`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ssh -i`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh`
- Examples:
  - `ssh -i`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `~/.ssh/key.pem`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh-key-pem`
- Examples:
  - `~/.ssh/key.pem`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `user@host`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `user-host`
- Examples:
  - `user@host`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ssh -v user@host`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh`
- Examples:
  - `ssh -v user@host`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `chmod 600 ~/.ssh/aut`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `chmod`
- Examples:
  - `chmod 600 ~/.ssh/aut`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `horized_keys`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `horized_keys`
- Examples:
  - `horized_keys`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ssh -vvv user@host`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh`
- Examples:
  - `ssh -vvv user@host`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `chmod 700 ~/.ssh/`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `chmod`
- Examples:
  - `chmod 700 ~/.ssh/`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ssh -X user@host`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh`
- Examples:
  - `ssh -X user@host`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ssh -A user@host`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh`
- Examples:
  - `ssh -A user@host`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ssh -L`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh`
- Examples:
  - `ssh -L`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ssh -R`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh`
- Examples:
  - `ssh -R`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ssh -D 1080`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh`
- Examples:
  - `ssh -D 1080`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ssh -N -f -L`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh`
- Examples:
  - `ssh -N -f -L`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `8080:localhost:80`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `8080-localhost-80`
- Examples:
  - `8080:localhost:80`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ssh -t user@host`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh`
- Examples:
  - `ssh -t user@host`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `scp`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `scp`
- Examples:
  - `scp`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ssh -o StrictHostKey`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh`
- Examples:
  - `ssh -o StrictHostKey`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `Checking=no`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `checking-no`
- Examples:
  - `Checking=no`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ssh -o`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh`
- Examples:
  - `ssh -o`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ConnectTimeout=10`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `connecttimeout-10`
- Examples:
  - `ConnectTimeout=10`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ssh -o PasswordAuthe`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh`
- Examples:
  - `ssh -o PasswordAuthe`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ntication=no`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ntication-no`
- Examples:
  - `ntication=no`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ssh -J jumphost`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh`
- Examples:
  - `ssh -J jumphost`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `4096`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `4096`
- Examples:
  - `4096`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ed25519`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ed25519`
- Examples:
  - `ed25519`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `rsync -avz -e ssh`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `rsync`
- Examples:
  - `rsync -avz -e ssh`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `rsync -avz`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `rsync`
- Examples:
  - `rsync -avz`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `~/.ssh/mykey`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh-mykey`
- Examples:
  - `~/.ssh/mykey`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `~/.ssh/id_rsa`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh-id-rsa`
- Examples:
  - `~/.ssh/id_rsa`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ssh -o BatchMode=yes`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh`
- Examples:
  - `ssh -o BatchMode=yes`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ssh -o PreferredAuth`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh`
- Examples:
  - `ssh -o PreferredAuth`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `~/.ssh/id_rsa.pub`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh-id-rsa-pub`
- Examples:
  - `~/.ssh/id_rsa.pub`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ssh-copy-id`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh-copy-id`
- Examples:
  - `ssh-copy-id`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `cat ~/.ssh/config`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `cat`
- Examples:
  - `cat ~/.ssh/config`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`

### `ssh-add`

- Category: `SSH i dost■p zdalny`
- Risk: `unclassified`
- Tags: `networking`, `ssh-add`
- Examples:
  - `ssh-add`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `SSH i dost■p zdalny`
```

## `runtime/knowledge/networking/zapora-ogniowa-firewalld.md`

- size: 9674 bytes
- sha256: `ed795b68cd50a2da83e7c750a3b232bc04804c40724b649c4129b8f6f963910e`
- category: knowledge

```markdown
---
title: Zapora ogniowa (firewalld)
topic: networking
source_section: Zapora ogniowa (firewalld)
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [firewall-cmd, firewalld, linux, networking, rhcsa, zapora-ogniowa-firewalld]
---

# Zapora ogniowa (firewalld)

Imported RHCSA material for 25 commands. Primary command families: firewall-cmd, firewalld.

## Tags

firewall-cmd, firewalld, linux, networking, rhcsa, zapora-ogniowa-firewalld

## Examples

- `firewall-cmd --state`
- `firewall-cmd --runti`
- `firewall-cmd`
- `firewalld`
- `--get-zones`
- `--get-active-zones`
- `--get-default-zone`
- `firewall-cmd --set-d`
- `efault-zone=trusted`
- `w■■czona`

## Troubleshooting

- Check interface state, service state, and firewall exposure together during network diagnostics.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Zapora ogniowa (firewalld)`

## Commands

### `firewall-cmd --state`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `firewall-cmd`
- Examples:
  - `firewall-cmd --state`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `firewall-cmd --runti`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `firewall-cmd`
- Examples:
  - `firewall-cmd --runti`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `firewall-cmd`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `firewall-cmd`
- Examples:
  - `firewall-cmd`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `firewalld`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `firewalld`
- Examples:
  - `firewalld`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `--get-zones`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `get-zones`
- Examples:
  - `--get-zones`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `--get-active-zones`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `get-active-zones`
- Examples:
  - `--get-active-zones`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `--get-default-zone`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `get-default-zone`
- Examples:
  - `--get-default-zone`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `firewall-cmd --set-d`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `firewall-cmd`
- Examples:
  - `firewall-cmd --set-d`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `efault-zone=trusted`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `efault-zone-trusted`
- Examples:
  - `efault-zone=trusted`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `w■■czona`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `wczona`
- Examples:
  - `w■■czona`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `firewall-cmd --add-f`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `firewall-cmd`
- Examples:
  - `firewall-cmd --add-f`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `--list-all`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `list-all`
- Examples:
  - `--list-all`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `--zone=public`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `zone-public`
- Examples:
  - `--zone=public`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `--list-services`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `list-services`
- Examples:
  - `--list-services`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `--list-ports`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `list-ports`
- Examples:
  - `--list-ports`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `firewall-cmd --add-r`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `firewall-cmd`
- Examples:
  - `firewall-cmd --add-r`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `--list-rich-rules`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `list-rich-rules`
- Examples:
  - `--list-rich-rules`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `--add-service=http`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `add-service-http`
- Examples:
  - `--add-service=http`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `firewall-cmd --remov`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `firewall-cmd`
- Examples:
  - `firewall-cmd --remov`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `e-service=http`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `e-service-http`
- Examples:
  - `e-service=http`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `--add-service=https`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `add-service-https`
- Examples:
  - `--add-service=https`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `--add-port=8080/tcp`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `add-port-8080-tcp`
- Examples:
  - `--add-port=8080/tcp`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `e-port=8080/tcp`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `e-port-8080-tcp`
- Examples:
  - `e-port=8080/tcp`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `firewall-cmd --add-p`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `firewall-cmd`
- Examples:
  - `firewall-cmd --add-p`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`

### `--complete-reload`

- Category: `Zapora ogniowa (firewalld)`
- Risk: `unclassified`
- Tags: `networking`, `complete-reload`
- Examples:
  - `--complete-reload`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zapora ogniowa (firewalld)`
```

## `runtime/knowledge/parsed/rhcsa_sections.json`

- size: 48865 bytes
- sha256: `03615be0cd88162c1758d3fd6028d19aaa64efca7898298895b0c1f669fda9f6`
- category: knowledge

```json
[
  {
    "section": "Nawigacja po systemie plików",
    "commands": [
      "pwd",
      "tree",
      "ls",
      "ls -l",
      "ls -la",
      "ls -lh",
      "ls -lt",
      "ls -lS",
      "ls -R",
      "ls -d */",
      "basename",
      "ls -i",
      "dirname",
      "ls --color=auto",
      "cd /path/to/dir",
      "cd ~",
      "cd -",
      "echo $PATH",
      "echo $HOME",
      "echo $PWD",
      "cd /",
      "echo $OLDPWD",
      "ls /etc | head -20",
      "popd",
      "ls /proc | wc -l",
      "dirs"
    ],
    "examples": [
      "pwd",
      "tree",
      "ls",
      "ls -l",
      "ls -la",
      "ls -lh",
      "ls -lt",
      "ls -lS",
      "ls -R",
      "ls -d */",
      "basename",
      "ls -i",
      "dirname",
      "ls --color=auto",
      "cd /path/to/dir",
      "cd ~",
      "cd -",
      "echo $PATH",
      "echo $HOME",
      "echo $PWD",
      "cd /",
      "echo $OLDPWD",
      "ls /etc | head -20",
      "popd",
      "ls /proc | wc -l",
      "dirs"
    ]
  },
  {
    "section": "Operacje na plikach i katalogach",
    "commands": [
      "touch file.txt",
      "mkdir dirname",
      "touch -t",
      "mkdir -p a/b/c",
      "touch -d",
      "mkdir -m 755 dirname",
      "cp source dest",
      "mkdir -v dirname",
      "cp -r src/ dst/",
      "cp -p src dst",
      "cp -a src/ dst/",
      "cp -i src dst",
      "cp -u src dst",
      "cp -v src dst",
      "cp --backup src dst",
      "nadpisaniem",
      "rsync -av src/ dst/",
      "rsync -avz src/",
      "rsync --delete src/",
      "rsync -n src/ dst/",
      "rm file.txt",
      "rsync",
      "rm -f file.txt",
      "rm -r dir/",
      "rm -rf dir/",
      "rm -i file",
      "rm -v file"
    ],
    "examples": [
      "touch file.txt",
      "mkdir dirname",
      "touch -t",
      "mkdir -p a/b/c",
      "touch -d",
      "mkdir -m 755 dirname",
      "cp source dest",
      "mkdir -v dirname",
      "cp -r src/ dst/",
      "cp -p src dst",
      "cp -a src/ dst/",
      "cp -i src dst",
      "cp -u src dst",
      "cp -v src dst",
      "cp --backup src dst",
      "nadpisaniem",
      "rsync -av src/ dst/",
      "rsync -avz src/",
      "rsync --delete src/",
      "rsync -n src/ dst/",
      "rm file.txt",
      "rsync",
      "rm -f file.txt",
      "rm -r dir/",
      "rm -rf dir/",
      "rm -i file",
      "rm -v file"
    ]
  },
  {
    "section": "Przegl■danie zawarto■ci plików",
    "commands": [
      "cat file.txt",
      "cat -n file.txt",
      "cat -A file.txt",
      "cat file1 file2"
    ],
    "examples": [
      "cat file.txt",
      "cat -n file.txt",
      "cat -A file.txt",
      "cat file1 file2"
    ]
  },
  {
    "section": "Wyszukiwanie i filtrowanie tekstu",
    "commands": [
      "grep 'pattern' file",
      "grep -i 'pattern'",
      "file",
      "grep -r 'pattern'",
      "/dir",
      "grep -v 'pattern'",
      "grep -n 'pattern'",
      "grep -c 'pattern'",
      "grep -l 'pattern'",
      "grep -w 'word' file",
      "grep -A 3 'pattern'",
      "grep -B 3 'pattern'",
      "grep -C 3 'pattern'",
      "grep -E 'pat1|pat2'",
      "grep -P '\\d+' file",
      "grep -o 'pattern'",
      "grep -m 5 'pattern'",
      "grep -q 'pattern'",
      "grep -F 'literal'",
      "grep",
      "awk '{print $1}'",
      "awk -F: '{print $1}'",
      "awk 'NR==5' file",
      "awk 'NR>=5 &&",
      "awk '/pattern/' file",
      "awk '{sum+=$1}",
      "awk '{print NF}'",
      "awk 'END{print NR}'",
      "awk '{print $NF}'",
      "awk -v FS=':'"
    ],
    "examples": [
      "grep 'pattern' file",
      "grep -i 'pattern'",
      "file",
      "grep -r 'pattern'",
      "/dir",
      "grep -v 'pattern'",
      "grep -n 'pattern'",
      "grep -c 'pattern'",
      "grep -l 'pattern'",
      "grep -w 'word' file",
      "grep -A 3 'pattern'",
      "grep -B 3 'pattern'",
      "grep -C 3 'pattern'",
      "grep -E 'pat1|pat2'",
      "grep -P '\\d+' file",
      "grep -o 'pattern'",
      "grep -m 5 'pattern'",
      "grep -q 'pattern'",
      "grep -F 'literal'",
      "grep",
      "awk '{print $1}'",
      "awk -F: '{print $1}'",
      "awk 'NR==5' file",
      "awk 'NR>=5 &&",
      "awk '/pattern/' file",
      "awk '{sum+=$1}",
      "awk '{print NF}'",
      "awk 'END{print NR}'",
      "awk '{print $NF}'",
      "awk -v FS=':'"
    ]
  },
  {
    "section": "Uprawnienia i w■asno■■ plików",
    "commands": [
      "chmod 755 file",
      "chown",
      "chmod 644 file",
      "chmod 600 file",
      "chmod 777 file",
      "umask",
      "chmod u+x file",
      "w■a■ciciela",
      "chmod g-w file",
      "chmod o-r file",
      "chmod a+r file",
      "chmod u=rwx,g=rx,o=r",
      "file",
      "chmod -R 755 dir/",
      "katalogu",
      "chmod",
      "chmod 4755 file",
      "w■a■ciciel)",
      "chmod 2755 dir",
      "chmod 1755 dir",
      "chmod +t dir",
      "chmod u+s file",
      "chmod g+s dir",
      "ls -Z file",
      "chown user file",
      "chown user:group",
      "find / -perm -4000",
      "chown :group file",
      "find / -perm -2000",
      "chown -R user:group",
      "find / -perm -o+w",
      "dir/"
    ],
    "examples": [
      "chmod 755 file",
      "chown",
      "chmod 644 file",
      "chmod 600 file",
      "chmod 777 file",
      "umask",
      "chmod u+x file",
      "w■a■ciciela",
      "chmod g-w file",
      "chmod o-r file",
      "chmod a+r file",
      "chmod u=rwx,g=rx,o=r",
      "file",
      "chmod -R 755 dir/",
      "katalogu",
      "chmod",
      "chmod 4755 file",
      "w■a■ciciel)",
      "chmod 2755 dir",
      "chmod 1755 dir",
      "chmod +t dir",
      "chmod u+s file",
      "chmod g+s dir",
      "ls -Z file",
      "chown user file",
      "chown user:group",
      "find / -perm -4000",
      "chown :group file",
      "find / -perm -2000",
      "chown -R user:group",
      "find / -perm -o+w",
      "dir/"
    ]
  },
  {
    "section": "Zarz■dzanie u■ytkownikami",
    "commands": [
      "useradd username",
      "useradd -m username",
      "useradd -m -s",
      "useradd -u 1500 user",
      "useradd -g group",
      "user",
      "useradd -G g1,g2",
      "useradd -d",
      "useradd -c 'Imi■",
      "useradd -e",
      "id",
      "useradd -f 30 user",
      "whoami",
      "dniach",
      "useradd -r sysuser",
      "who",
      "useradd -M user",
      "w",
      "useradd -N user",
      "last",
      "usermod -l newname",
      "lastlog",
      "usermod -d /new/home",
      "lastb",
      "usermod -s /bin/zsh",
      "usermod -u 1600 user",
      "usermod -g group",
      "usermod -G g1,g2",
      "usermod -aG group",
      "usermod -c 'Nowy",
      "usermod -e",
      "usermod -L user",
      "visudo",
      "usermod -U user",
      "cat /etc/passwd",
      "usermod -e '' user",
      "cat /etc/shadow",
      "trwa■e)",
      "cat /etc/group",
      "cat /etc/gshadow",
      "zalogowanego",
      "vipw",
      "vigr",
      "pwck",
      "grpck",
      "lslogins"
    ],
    "examples": [
      "useradd username",
      "useradd -m username",
      "useradd -m -s",
      "useradd -u 1500 user",
      "useradd -g group",
      "user",
      "useradd -G g1,g2",
      "useradd -d",
      "useradd -c 'Imi■",
      "useradd -e",
      "id",
      "useradd -f 30 user",
      "whoami",
      "dniach",
      "useradd -r sysuser",
      "who",
      "useradd -M user",
      "w",
      "useradd -N user",
      "last",
      "usermod -l newname",
      "lastlog",
      "usermod -d /new/home",
      "lastb",
      "usermod -s /bin/zsh",
      "usermod -u 1600 user",
      "usermod -g group",
      "usermod -G g1,g2",
      "usermod -aG group",
      "usermod -c 'Nowy",
      "usermod -e",
      "usermod -L user",
      "visudo",
      "usermod -U user",
      "cat /etc/passwd",
      "usermod -e '' user",
      "cat /etc/shadow",
      "trwa■e)",
      "cat /etc/group",
      "cat /etc/gshadow",
      "zalogowanego",
      "vipw",
      "vigr",
      "pwck",
      "grpck",
      "lslogins"
    ]
  },
  {
    "section": "Zarz■dzanie grupami",
    "commands": [
      "group",
      "usermod -aG wheel",
      "usermod -aG docker"
    ],
    "examples": [
      "group",
      "usermod -aG wheel",
      "usermod -aG docker"
    ]
  },
  {
    "section": "Zarz■dzanie procesami",
    "commands": [
      "ps",
      "Ctrl+Z",
      "Ctrl+C",
      "Ctrl+D",
      "wait",
      "pstree",
      "lsof",
      "top",
      "htop",
      "u■ytkownika",
      "uptime",
      "jobs",
      "cat /proc/PID/status",
      "cat /proc/PID/maps",
      "cat /proc/loadavg",
      "cat /proc/meminfo"
    ],
    "examples": [
      "ps",
      "Ctrl+Z",
      "Ctrl+C",
      "Ctrl+D",
      "wait",
      "pstree",
      "lsof",
      "top",
      "htop",
      "u■ytkownika",
      "uptime",
      "jobs",
      "cat /proc/PID/status",
      "cat /proc/PID/maps",
      "cat /proc/loadavg",
      "cat /proc/meminfo"
    ]
  },
  {
    "section": "Systemd i zarz■dzanie us■ugami",
    "commands": [
      "systemctl status",
      "systemctl show",
      "service",
      "systemctl start",
      "systemctl show -p",
      "systemctl stop",
      "systemd-analyze",
      "systemctl restart",
      "systemctl reload",
      "systemctl enable",
      "systemctl disable",
      "journalctl",
      "journalctl -u",
      "journalctl -f",
      "systemctl is-active",
      "journalctl -f -u",
      "systemctl is-enabled",
      "journalctl -n 50",
      "systemctl is-failed",
      "journalctl --since",
      "systemctl list-units",
      "journalctl --until",
      "--type=service",
      "journalctl -p err",
      "systemctl",
      "journalctl -p",
      "list-unit-files",
      "journalctl -b",
      "journalctl -b -1",
      "list-dependencies",
      "systemctl mask",
      "journalctl -k",
      "systemctl unmask",
      "journalctl -o json",
      "daemon-reload",
      "daemon-reexec",
      "--vacuum-size=500M",
      "get-default",
      "systemctl --user",
      "set-default",
      "loginctl",
      "systemctl isolate",
      "rescue.target",
      "emergency.target",
      "hostnamectl",
      "systemctl poweroff",
      "systemctl reboot",
      "timedatectl",
      "systemctl halt",
      "systemctl suspend",
      "systemctl hibernate",
      "systemctl cat",
      "localectl",
      "systemctl edit"
    ],
    "examples": [
      "systemctl status",
      "systemctl show",
      "service",
      "systemctl start",
      "systemctl show -p",
      "systemctl stop",
      "systemd-analyze",
      "systemctl restart",
      "systemctl reload",
      "systemctl enable",
      "systemctl disable",
      "journalctl",
      "journalctl -u",
      "journalctl -f",
      "systemctl is-active",
      "journalctl -f -u",
      "systemctl is-enabled",
      "journalctl -n 50",
      "systemctl is-failed",
      "journalctl --since",
      "systemctl list-units",
      "journalctl --until",
      "--type=service",
      "journalctl -p err",
      "systemctl",
      "journalctl -p",
      "list-unit-files",
      "journalctl -b",
      "journalctl -b -1",
      "list-dependencies",
      "systemctl mask",
      "journalctl -k",
      "systemctl unmask",
      "journalctl -o json",
      "daemon-reload",
      "daemon-reexec",
      "--vacuum-size=500M",
      "get-default",
      "systemctl --user",
      "set-default",
      "loginctl",
      "systemctl isolate",
      "rescue.target",
      "emergency.target",
      "hostnamectl",
      "systemctl poweroff",
      "systemctl reboot",
      "timedatectl",
      "systemctl halt",
      "systemctl suspend",
      "systemctl hibernate",
      "systemctl cat",
      "localectl",
      "systemctl edit"
    ]
  },
  {
    "section": "Zarz■dzanie pakietami (DNF/RPM)",
    "commands": [
      "dnf install package",
      "dnf check-update",
      "dnf install -y",
      "dnf security update",
      "package",
      "dnf remove package",
      "dnf updateinfo list",
      "dnf erase package",
      "dnf update",
      "dnf distro-sync",
      "dnf update package",
      "dnf module list",
      "dnf upgrade",
      "dnf module enable",
      "dnf upgrade-minimal",
      "dnf module disable",
      "dnf downgrade",
      "dnf module install m",
      "dnf reinstall",
      "dnf module reset",
      "dnf autoremove",
      "dnf module info",
      "dnf clean all",
      "rpm -qa",
      "dnf clean packages",
      "rpm -qi package",
      "dnf clean metadata",
      "rpm -ql package",
      "dnf makecache",
      "rpm -qd package",
      "dnf search keyword",
      "rpm -qc package",
      "dnf info package",
      "rpm -qf",
      "dnf list installed",
      "rpm -qR package",
      "dnf list available",
      "rpm -q --scripts",
      "dnf list updates",
      "rpm -q --changelog",
      "aktualizacjami",
      "dnf list extras",
      "rpm -ivh package.rpm",
      "dnf list obsoletes",
      "rpm -Uvh package.rpm",
      "dnf provides",
      "rpm -Fvh package.rpm",
      "rpm -e package",
      "dnf whatprovides",
      "rpm -V package",
      "dnf repolist",
      "rpm -Va",
      "dnf repolist all",
      "rpm --import",
      "rpm -K package.rpm",
      "dnf repoinfo repo-id",
      "dnf config-manager",
      "rpm -qp --scripts",
      "rpm -qip package.rpm",
      "dnf grouplist",
      "subscription-manager",
      "dnf groupinstall",
      "dnf groupremove",
      "dnf groupinfo 'Group",
      "Name'",
      "dnf history",
      "dnf history info 5",
      "dnf history undo 5",
      "dnf history redo 5",
      "dnf history rollback"
    ],
    "examples": [
      "dnf install package",
      "dnf check-update",
      "dnf install -y",
      "dnf security update",
      "package",
      "dnf remove package",
      "dnf updateinfo list",
      "dnf erase package",
      "dnf update",
      "dnf distro-sync",
      "dnf update package",
      "dnf module list",
      "dnf upgrade",
      "dnf module enable",
      "dnf upgrade-minimal",
      "dnf module disable",
      "dnf downgrade",
      "dnf module install m",
      "dnf reinstall",
      "dnf module reset",
      "dnf autoremove",
      "dnf module info",
      "dnf clean all",
      "rpm -qa",
      "dnf clean packages",
      "rpm -qi package",
      "dnf clean metadata",
      "rpm -ql package",
      "dnf makecache",
      "rpm -qd package",
      "dnf search keyword",
      "rpm -qc package",
      "dnf info package",
      "rpm -qf",
      "dnf list installed",
      "rpm -qR package",
      "dnf list available",
      "rpm -q --scripts",
      "dnf list updates",
      "rpm -q --changelog",
      "aktualizacjami",
      "dnf list extras",
      "rpm -ivh package.rpm",
      "dnf list obsoletes",
      "rpm -Uvh package.rpm",
      "dnf provides",
      "rpm -Fvh package.rpm",
      "rpm -e package",
      "dnf whatprovides",
      "rpm -V package",
      "dnf repolist",
      "rpm -Va",
      "dnf repolist all",
      "rpm --import",
      "rpm -K package.rpm",
      "dnf repoinfo repo-id",
      "dnf config-manager",
      "rpm -qp --scripts",
      "rpm -qip package.rpm",
      "dnf grouplist",
      "subscription-manager",
      "dnf groupinstall",
      "dnf groupremove",
      "dnf groupinfo 'Group",
      "Name'",
      "dnf history",
      "dnf history info 5",
      "dnf history undo 5",
      "dnf history redo 5",
      "dnf history rollback"
    ]
  },
  {
    "section": "Sie■ — konfiguracja i diagnostyka",
    "commands": [
      "ip addr",
      "ip addr show",
      "ip addr show eth0",
      "ip addr add",
      "ip addr del",
      "ip link show",
      "ip link set eth0 up",
      "ip link set eth0 down",
      "curl",
      "ip link set eth0 mtu",
      "9000",
      "ip route show",
      "ip route add default",
      "ip route add",
      "ip route del default",
      "nmcli device show",
      "ip route del",
      "nmcli device status",
      "ip route get 8.8.8.8",
      "nmcli connection",
      "ip neigh show",
      "ip neigh flush all",
      "nmcli connection up",
      "ip -6 addr show",
      "ip -6 route show",
      "nmcli connection add",
      "PID",
      "established",
      "procesami",
      "nmcli general",
      "nmcli radio wifi off",
      "nmtui",
      "cat /etc/hosts",
      "cat /etc/resolv.conf",
      "cat /etc/hostname",
      "cat /etc/sysconfig/n",
      "hostname"
    ],
    "examples": [
      "ip addr",
      "ip addr show",
      "ip addr show eth0",
      "ip addr add",
      "ip addr del",
      "ip link show",
      "ip link set eth0 up",
      "ip link set eth0 down",
      "curl",
      "ip link set eth0 mtu",
      "9000",
      "ip route show",
      "ip route add default",
      "ip route add",
      "ip route del default",
      "nmcli device show",
      "ip route del",
      "nmcli device status",
      "ip route get 8.8.8.8",
      "nmcli connection",
      "ip neigh show",
      "ip neigh flush all",
      "nmcli connection up",
      "ip -6 addr show",
      "ip -6 route show",
      "nmcli connection add",
      "PID",
      "established",
      "procesami",
      "nmcli general",
      "nmcli radio wifi off",
      "nmtui",
      "cat /etc/hosts",
      "cat /etc/resolv.conf",
      "cat /etc/hostname",
      "cat /etc/sysconfig/n",
      "hostname"
    ]
  },
  {
    "section": "Zapora ogniowa (firewalld)",
    "commands": [
      "firewall-cmd --state",
      "firewall-cmd --runti",
      "systemctl status",
      "firewall-cmd",
      "firewalld",
      "systemctl enable",
      "--get-zones",
      "--get-active-zones",
      "--get-default-zone",
      "firewall-cmd --set-d",
      "efault-zone=trusted",
      "w■■czona",
      "firewall-cmd --add-f",
      "--list-all",
      "--zone=public",
      "--list-services",
      "--list-ports",
      "firewall-cmd --add-r",
      "--list-rich-rules",
      "--add-service=http",
      "firewall-cmd --remov",
      "e-service=http",
      "--add-service=https",
      "--add-port=8080/tcp",
      "e-port=8080/tcp",
      "firewall-cmd --add-p",
      "--complete-reload"
    ],
    "examples": [
      "firewall-cmd --state",
      "firewall-cmd --runti",
      "systemctl status",
      "firewall-cmd",
      "firewalld",
      "systemctl enable",
      "--get-zones",
      "--get-active-zones",
      "--get-default-zone",
      "firewall-cmd --set-d",
      "efault-zone=trusted",
      "w■■czona",
      "firewall-cmd --add-f",
      "--list-all",
      "--zone=public",
      "--list-services",
      "--list-ports",
      "firewall-cmd --add-r",
      "--list-rich-rules",
      "--add-service=http",
      "firewall-cmd --remov",
      "e-service=http",
      "--add-service=https",
      "--add-port=8080/tcp",
      "e-port=8080/tcp",
      "firewall-cmd --add-p",
      "--complete-reload"
    ]
  },
  {
    "section": "SELinux",
    "commands": [
      "getenforce",
      "setsebool httpd_can_",
      "sestatus",
      "setsebool -P httpd_c",
      "setsebool -P",
      "cat",
      "setsebool -P samba_e",
      "/etc/selinux/config",
      "ls -Z file",
      "ls -Z dir/",
      "semanage user -l",
      "ls -dZ dir/",
      "semanage login -l",
      "semanage login -a -s",
      "u■ytkownika",
      "SELinux",
      "httpd_sys_content_t",
      "restorecon",
      "/path/to/file",
      "restorecon -R",
      "restorecon -Rv",
      "restorecon -F /path/",
      "semanage fcontext -l",
      "semanage fcontext -a",
      "-t",
      "semanage fcontext -d",
      "journalctl -t",
      "semanage fcontext -m",
      "matchpathcon",
      "semanage port -l",
      "semanage port -l |",
      "semanage port -a -t",
      "semanage port -d -t",
      "cat /var/log/audit/a",
      "semanage port -m -t",
      "grep 'denied' /var/l",
      "semanage boolean -l",
      "touch /.autorelabel"
    ],
    "examples": [
      "getenforce",
      "setsebool httpd_can_",
      "sestatus",
      "setsebool -P httpd_c",
      "setsebool -P",
      "cat",
      "setsebool -P samba_e",
      "/etc/selinux/config",
      "ls -Z file",
      "ls -Z dir/",
      "semanage user -l",
      "ls -dZ dir/",
      "semanage login -l",
      "semanage login -a -s",
      "u■ytkownika",
      "SELinux",
      "httpd_sys_content_t",
      "restorecon",
      "/path/to/file",
      "restorecon -R",
      "restorecon -Rv",
      "restorecon -F /path/",
      "semanage fcontext -l",
      "semanage fcontext -a",
      "-t",
      "semanage fcontext -d",
      "journalctl -t",
      "semanage fcontext -m",
      "matchpathcon",
      "semanage port -l",
      "semanage port -l |",
      "semanage port -a -t",
      "semanage port -d -t",
      "cat /var/log/audit/a",
      "semanage port -m -t",
      "grep 'denied' /var/l",
      "semanage boolean -l",
      "touch /.autorelabel"
    ]
  },
  {
    "section": "Przechowywanie danych — dyski i partycje",
    "commands": [
      "lsblk",
      "print",
      "partprobe",
      "dysków",
      "blkid"
    ],
    "examples": [
      "lsblk",
      "print",
      "partprobe",
      "dysków",
      "blkid"
    ]
  },
  {
    "section": "LVM — Logical Volume Manager",
    "commands": [
      "pvs",
      "lvs",
      "pvdisplay",
      "lvdisplay",
      "/dev/sdc",
      "partycji)",
      "pvscan",
      "vgs",
      "vgdisplay",
      "lvremove",
      "/dev/sdb",
      "newname",
      "vgscan",
      "lvscan",
      "lvmdiskscan"
    ],
    "examples": [
      "pvs",
      "lvs",
      "pvdisplay",
      "lvdisplay",
      "/dev/sdc",
      "partycji)",
      "pvscan",
      "vgs",
      "vgdisplay",
      "lvremove",
      "/dev/sdb",
      "newname",
      "vgscan",
      "lvscan",
      "lvmdiskscan"
    ]
  },
  {
    "section": "Systemy plików i montowanie",
    "commands": [
      "cat /etc/fstab",
      "mount | column -t",
      "/dev/sdb1",
      "mount /dev/sdb1 /mnt",
      "mount -t ext4",
      "mount -t xfs",
      "mount -o ro",
      "mount -o rw,noexec",
      "mount -o remount,rw",
      "/mnt",
      "mount -o remount,ro",
      "mount UUID=xxx /mnt",
      "mount LABEL=mylabel",
      "mount -a",
      "findmnt",
      "montowania",
      "cat /proc/mounts"
    ],
    "examples": [
      "cat /etc/fstab",
      "mount | column -t",
      "/dev/sdb1",
      "mount /dev/sdb1 /mnt",
      "mount -t ext4",
      "mount -t xfs",
      "mount -o ro",
      "mount -o rw,noexec",
      "mount -o remount,rw",
      "/mnt",
      "mount -o remount,ro",
      "mount UUID=xxx /mnt",
      "mount LABEL=mylabel",
      "mount -a",
      "findmnt",
      "montowania",
      "cat /proc/mounts"
    ]
  },
  {
    "section": "Archiwizacja i kompresja",
    "commands": [
      "tar -cvf archive.tar",
      "tar -cvzf",
      "tar -cvjf",
      "tar -cvJf",
      "tar -xvf archive.tar",
      "tar -xvzf",
      "archive.tar.gz",
      "tar -xvjf",
      "archive.tar.bz2",
      "tar -xvJf",
      "archive.tar.xz",
      "tar -tvf archive.tar",
      "tar -tvzf",
      "tar -rvf archive.tar",
      "newfile",
      "tar -uvf archive.tar",
      "tar --delete -f",
      "tar",
      "tar --exclude-vcs",
      "tar -czf - /path |",
      "tar -czf arch.tar.gz",
      "--newer-mtime='2023-",
      "find /path -print |"
    ],
    "examples": [
      "tar -cvf archive.tar",
      "tar -cvzf",
      "tar -cvjf",
      "tar -cvJf",
      "tar -xvf archive.tar",
      "tar -xvzf",
      "archive.tar.gz",
      "tar -xvjf",
      "archive.tar.bz2",
      "tar -xvJf",
      "archive.tar.xz",
      "tar -tvf archive.tar",
      "tar -tvzf",
      "tar -rvf archive.tar",
      "newfile",
      "tar -uvf archive.tar",
      "tar --delete -f",
      "tar",
      "tar --exclude-vcs",
      "tar -czf - /path |",
      "tar -czf arch.tar.gz",
      "--newer-mtime='2023-",
      "find /path -print |"
    ]
  },
  {
    "section": "SSH i dost■p zdalny",
    "commands": [
      "ssh user@hostname",
      "ssh -p 2222",
      "user@hostname",
      "ssh -i",
      "cat",
      "~/.ssh/key.pem",
      "user@host",
      "ssh -v user@host",
      "chmod 600 ~/.ssh/aut",
      "horized_keys",
      "ssh -vvv user@host",
      "chmod 700 ~/.ssh/",
      "ssh -X user@host",
      "ssh -A user@host",
      "ssh -L",
      "ssh -R",
      "ssh -D 1080",
      "ssh -N -f -L",
      "8080:localhost:80",
      "ssh -t user@host",
      "scp",
      "ssh -o StrictHostKey",
      "Checking=no",
      "ssh -o",
      "ConnectTimeout=10",
      "ssh -o PasswordAuthe",
      "ntication=no",
      "ssh -J jumphost",
      "4096",
      "ed25519",
      "rsync -avz -e ssh",
      "rsync -avz",
      "~/.ssh/mykey",
      "~/.ssh/id_rsa",
      "ssh -o BatchMode=yes",
      "ssh -o PreferredAuth",
      "~/.ssh/id_rsa.pub",
      "systemctl reload",
      "hostname",
      "ssh-copy-id",
      "systemctl restart",
      "cat ~/.ssh/config",
      "ssh-add"
    ],
    "examples": [
      "ssh user@hostname",
      "ssh -p 2222",
      "user@hostname",
      "ssh -i",
      "cat",
      "~/.ssh/key.pem",
      "user@host",
      "ssh -v user@host",
      "chmod 600 ~/.ssh/aut",
      "horized_keys",
      "ssh -vvv user@host",
      "chmod 700 ~/.ssh/",
      "ssh -X user@host",
      "ssh -A user@host",
      "ssh -L",
      "ssh -R",
      "ssh -D 1080",
      "ssh -N -f -L",
      "8080:localhost:80",
      "ssh -t user@host",
      "scp",
      "ssh -o StrictHostKey",
      "Checking=no",
      "ssh -o",
      "ConnectTimeout=10",
      "ssh -o PasswordAuthe",
      "ntication=no",
      "ssh -J jumphost",
      "4096",
      "ed25519",
      "rsync -avz -e ssh",
      "rsync -avz",
      "~/.ssh/mykey",
      "~/.ssh/id_rsa",
      "ssh -o BatchMode=yes",
      "ssh -o PreferredAuth",
      "~/.ssh/id_rsa.pub",
      "systemctl reload",
      "hostname",
      "ssh-copy-id",
      "systemctl restart",
      "cat ~/.ssh/config",
      "ssh-add"
    ]
  },
  {
    "section": "Cron i harmonogramowanie zada■",
    "commands": [
      "systemd-run",
      "u■ytkownika",
      "cat /etc/crontab",
      "atq",
      "ls /etc/cron.d/",
      "ls /etc/cron.daily/",
      "ls /etc/cron.weekly/",
      "ls",
      "batch",
      "ls /etc/cron.hourly/",
      "cat /etc/at.allow",
      "cat /var/spool/cron/",
      "cat /etc/at.deny",
      "cat /etc/cron.allow",
      "cat /etc/cron.deny",
      "run-parts",
      "/etc/cron.daily",
      "cat /etc/anacrontab",
      "systemctl",
      "list-timers",
      "systemctl status",
      "timer-name.timer",
      "systemctl enable",
      "myapp.timer",
      "systemctl start",
      "systemctl stop",
      "cat /etc/systemd/sys",
      "tem/myapp.timer"
    ],
    "examples": [
      "systemd-run",
      "u■ytkownika",
      "cat /etc/crontab",
      "atq",
      "ls /etc/cron.d/",
      "ls /etc/cron.daily/",
      "ls /etc/cron.weekly/",
      "ls",
      "batch",
      "ls /etc/cron.hourly/",
      "cat /etc/at.allow",
      "cat /var/spool/cron/",
      "cat /etc/at.deny",
      "cat /etc/cron.allow",
      "cat /etc/cron.deny",
      "run-parts",
      "/etc/cron.daily",
      "cat /etc/anacrontab",
      "systemctl",
      "list-timers",
      "systemctl status",
      "timer-name.timer",
      "systemctl enable",
      "myapp.timer",
      "systemctl start",
      "systemctl stop",
      "cat /etc/systemd/sys",
      "tem/myapp.timer"
    ]
  },
  {
    "section": "Logowanie i monitorowanie systemu",
    "commands": [
      "journalctl",
      "journalctl -xe",
      "journalctl -b",
      "journalctl -u sshd",
      "aureport",
      "journalctl -f",
      "journalctl -p err",
      "journalctl --since",
      "journalctl -o",
      "systemctl status",
      "--disk-usage",
      "dmesg",
      "cat /etc/audit/audit",
      "--level=err,warn",
      "cat",
      "/var/log/messages",
      "cat /var/log/secure",
      "ls /etc/logrotate.d/",
      "cat /var/log/cron",
      "cat /var/log/maillog",
      "cat /var/log/audit/a",
      "systemctl restart",
      "udit.log",
      "grep 'Failed",
      "grep 'Accepted'"
    ],
    "examples": [
      "journalctl",
      "journalctl -xe",
      "journalctl -b",
      "journalctl -u sshd",
      "aureport",
      "journalctl -f",
      "journalctl -p err",
      "journalctl --since",
      "journalctl -o",
      "systemctl status",
      "--disk-usage",
      "dmesg",
      "cat /etc/audit/audit",
      "--level=err,warn",
      "cat",
      "/var/log/messages",
      "cat /var/log/secure",
      "ls /etc/logrotate.d/",
      "cat /var/log/cron",
      "cat /var/log/maillog",
      "cat /var/log/audit/a",
      "systemctl restart",
      "udit.log",
      "grep 'Failed",
      "grep 'Accepted'"
    ]
  },
  {
    "section": "Boot i GRUB",
    "commands": [
      "cat",
      "/boot/grub2/grub.cfg",
      "cat /etc/sysctl.conf",
      "grub2-install",
      "cat /etc/sysctl.d/",
      "echo 'net.ipv4.ip_fo",
      "--target=x86_64-efi",
      "grub2-set-default",
      "GRUB",
      "lsmod",
      "ls /boot/grub2/",
      "ls /boot/",
      "insmod",
      "ls -la",
      "/boot/initramfs*",
      "echo 'module_name' >",
      "cat /etc/modprobe.d/",
      "systemctl",
      "rpm -qa kernel",
      "dnf list installed",
      "kernel",
      "dnf install kernel",
      "systemctl rescue",
      "dnf remove",
      "systemctl emergency",
      "cat /proc/cmdline",
      "cat /proc/version",
      "cat /proc/sys/kernel",
      "reboot",
      "poweroff",
      "halt",
      "sysctl",
      "sync"
    ],
    "examples": [
      "cat",
      "/boot/grub2/grub.cfg",
      "cat /etc/sysctl.conf",
      "grub2-install",
      "cat /etc/sysctl.d/",
      "echo 'net.ipv4.ip_fo",
      "--target=x86_64-efi",
      "grub2-set-default",
      "GRUB",
      "lsmod",
      "ls /boot/grub2/",
      "ls /boot/",
      "insmod",
      "ls -la",
      "/boot/initramfs*",
      "echo 'module_name' >",
      "cat /etc/modprobe.d/",
      "systemctl",
      "rpm -qa kernel",
      "dnf list installed",
      "kernel",
      "dnf install kernel",
      "systemctl rescue",
      "dnf remove",
      "systemctl emergency",
      "cat /proc/cmdline",
      "cat /proc/version",
      "cat /proc/sys/kernel",
      "reboot",
      "poweroff",
      "halt",
      "sysctl",
      "sync"
    ]
  },
  {
    "section": "NFS i Autofs",
    "commands": [
      "nfsstat",
      "mount -t nfs",
      "mount -t nfs4",
      "firewall-cmd",
      "mount -o ro,soft",
      "firewall-cmd --add-s",
      "mount -o",
      "nosuid,noexec",
      "cat /etc/auto.master",
      "cat /etc/exports",
      "cat /etc/auto.misc",
      "systemctl enable",
      "systemctl restart",
      "ls /mnt/nfs/share",
      "exportfs",
      "server:/share",
      "systemctl status",
      "nfs-server"
    ],
    "examples": [
      "nfsstat",
      "mount -t nfs",
      "mount -t nfs4",
      "firewall-cmd",
      "mount -o ro,soft",
      "firewall-cmd --add-s",
      "mount -o",
      "nosuid,noexec",
      "cat /etc/auto.master",
      "cat /etc/exports",
      "cat /etc/auto.misc",
      "systemctl enable",
      "systemctl restart",
      "ls /mnt/nfs/share",
      "exportfs",
      "server:/share",
      "systemctl status",
      "nfs-server"
    ]
  },
  {
    "section": "Kontenery Podman",
    "commands": [
      "podman --version",
      "podman exec",
      "podman info",
      "podman exec -u root",
      "podman images",
      "podman logs",
      "podman images -a",
      "podman logs -f",
      "podman pull",
      "podman logs --tail",
      "image:tag",
      "podman pull registry",
      "podman inspect",
      ".access.redhat.com/u",
      "podman push",
      "podman inspect -f",
      "podman rmi image",
      "podman top container",
      "podman rmi -a",
      "podman stats",
      "podman rmi -f image",
      "podman image inspect",
      "podman diff",
      "image",
      "podman image history",
      "podman commit",
      "podman image prune",
      "podman cp src",
      "podman cp",
      "-a",
      "podman tag src:tag",
      "podman pause",
      "dst:tag",
      "podman save image -o",
      "podman unpause",
      "file.tar",
      "podman load -i",
      "podman rename",
      "podman search nginx",
      "podman port",
      "podman search",
      "podman network ls",
      "podman network",
      "--list-tags",
      "podman run image",
      "podman network rm",
      "podman run -it image",
      "/bin/bash",
      "podman run -d image",
      "podman run --name",
      "podman run -p",
      "podman volume ls",
      "podman run -v",
      "podman volume create",
      "/host:/container",
      "podman volume rm",
      "podman run -e",
      "podman volume",
      "podman run",
      "podman volume prune",
      "podman run --rm",
      "podman build -t",
      "podman build -f",
      "--restart=always",
      "podman run --restart",
      "podman build",
      "podman run -u user",
      "cat Containerfile",
      "podman run --cap-add",
      "podman generate",
      "podman run --memory",
      "podman play kube",
      "podman run --cpus",
      "podman generate kube",
      "podman run --network",
      "podman pod ls",
      "podman pod create",
      "podman pod rm mypod",
      "podman ps",
      "podman pod start",
      "podman ps -a",
      "podman pod stop",
      "podman ps -q",
      "podman pod stats",
      "podman ps -qa",
      "podman pod inspect",
      "podman ps --format",
      "podman run --pod",
      "podman stop",
      "podman system prune",
      "podman stop -t 0",
      "container",
      "podman start",
      "podman system df",
      "podman restart",
      "podman system reset",
      "podman kill",
      "podman login",
      "podman kill -s",
      "podman logout",
      "podman rm container",
      "cat /etc/containers/",
      "podman rm -f",
      "podman rm -a",
      "podman unshare",
      "podman container",
      "podman machine init",
      "podman exec -it",
      "podman machine start"
    ],
    "examples": [
      "podman --version",
      "podman exec",
      "podman info",
      "podman exec -u root",
      "podman images",
      "podman logs",
      "podman images -a",
      "podman logs -f",
      "podman pull",
      "podman logs --tail",
      "image:tag",
      "podman pull registry",
      "podman inspect",
      ".access.redhat.com/u",
      "podman push",
      "podman inspect -f",
      "podman rmi image",
      "podman top container",
      "podman rmi -a",
      "podman stats",
      "podman rmi -f image",
      "podman image inspect",
      "podman diff",
      "image",
      "podman image history",
      "podman commit",
      "podman image prune",
      "podman cp src",
      "podman cp",
      "-a",
      "podman tag src:tag",
      "podman pause",
      "dst:tag",
      "podman save image -o",
      "podman unpause",
      "file.tar",
      "podman load -i",
      "podman rename",
      "podman search nginx",
      "podman port",
      "podman search",
      "podman network ls",
      "podman network",
      "--list-tags",
      "podman run image",
      "podman network rm",
      "podman run -it image",
      "/bin/bash",
      "podman run -d image",
      "podman run --name",
      "podman run -p",
      "podman volume ls",
      "podman run -v",
      "podman volume create",
      "/host:/container",
      "podman volume rm",
      "podman run -e",
      "podman volume",
      "podman run",
      "podman volume prune",
      "podman run --rm",
      "podman build -t",
      "podman build -f",
      "--restart=always",
      "podman run --restart",
      "podman build",
      "podman run -u user",
      "cat Containerfile",
      "podman run --cap-add",
      "podman generate",
      "podman run --memory",
      "podman play kube",
      "podman run --cpus",
      "podman generate kube",
      "podman run --network",
      "podman pod ls",
      "podman pod create",
      "podman pod rm mypod",
      "podman ps",
      "podman pod start",
      "podman ps -a",
      "podman pod stop",
      "podman ps -q",
      "podman pod stats",
      "podman ps -qa",
      "podman pod inspect",
      "podman ps --format",
      "podman run --pod",
      "podman stop",
      "podman system prune",
      "podman stop -t 0",
      "container",
      "podman start",
      "podman system df",
      "podman restart",
      "podman system reset",
      "podman kill",
      "podman login",
      "podman kill -s",
      "podman logout",
      "podman rm container",
      "cat /etc/containers/",
      "podman rm -f",
      "podman rm -a",
      "podman unshare",
      "podman container",
      "podman machine init",
      "podman exec -it",
      "podman machine start"
    ]
  },
  {
    "section": "Informacje o systemie",
    "commands": [
      "lsusb",
      "cat /etc/os-release",
      "cat",
      "hostnamectl",
      "uptime",
      "lscpu",
      "cat /proc/uptime",
      "cat /proc/cpuinfo",
      "w",
      "nproc",
      "lsmem",
      "cat /proc/loadavg",
      "vmstat",
      "cat /proc/meminfo",
      "iostat",
      "lsnuma",
      "cat /sys/class/dmi/i",
      "baseboard",
      "lshw",
      "sensors",
      "sensors-detect",
      "lspci",
      "cat /sys/block/sda/q"
    ],
    "examples": [
      "lsusb",
      "cat /etc/os-release",
      "cat",
      "hostnamectl",
      "uptime",
      "lscpu",
      "cat /proc/uptime",
      "cat /proc/cpuinfo",
      "w",
      "nproc",
      "lsmem",
      "cat /proc/loadavg",
      "vmstat",
      "cat /proc/meminfo",
      "iostat",
      "lsnuma",
      "cat /sys/class/dmi/i",
      "baseboard",
      "lshw",
      "sensors",
      "sensors-detect",
      "lspci",
      "cat /sys/block/sda/q"
    ]
  },
  {
    "section": "Zmienne ■rodowiskowe i pow■oka",
    "commands": [
      "env",
      "printenv",
      "echo $VARIABLE",
      "Ctrl+R",
      "echo $HISTSIZE",
      "echo $HISTFILE",
      "set",
      "echo $HISTFILESIZE",
      "echo $SHELL",
      "echo $BASH_VERSION",
      "echo $PS1",
      "alias ll='ls -alh'",
      "alias",
      "hash",
      "echo ${ARRAY[0]}",
      "complete",
      "echo ${ARRAY[@]}",
      "echo ${#ARRAY[@]}",
      "source",
      "cat ~/.bashrc",
      "cat ~/.bash_profile",
      "true",
      "cat ~/.bash_logout",
      "false",
      "cat /etc/profile",
      "cat /etc/bashrc",
      "echo $$",
      "ls /etc/profile.d/",
      "echo $?",
      "echo $!",
      "history",
      "echo $0",
      "echo $#",
      "echo $@",
      "echo $*"
    ],
    "examples": [
      "env",
      "printenv",
      "echo $VARIABLE",
      "Ctrl+R",
      "echo $HISTSIZE",
      "echo $HISTFILE",
      "set",
      "echo $HISTFILESIZE",
      "echo $SHELL",
      "echo $BASH_VERSION",
      "echo $PS1",
      "alias ll='ls -alh'",
      "alias",
      "hash",
      "echo ${ARRAY[0]}",
      "complete",
      "echo ${ARRAY[@]}",
      "echo ${#ARRAY[@]}",
      "source",
      "cat ~/.bashrc",
      "cat ~/.bash_profile",
      "true",
      "cat ~/.bash_logout",
      "false",
      "cat /etc/profile",
      "cat /etc/bashrc",
      "echo $$",
      "ls /etc/profile.d/",
      "echo $?",
      "echo $!",
      "history",
      "echo $0",
      "echo $#",
      "echo $@",
      "echo $*"
    ]
  },
  {
    "section": "Wyszukiwanie plików",
    "commands": [
      "find / -name",
      "find . -nogroup",
      "find . -name '*.log'",
      "find . -empty",
      "find . -iname",
      "find . -maxdepth 2",
      "find / -type f -name",
      "find . -mindepth 2",
      "find / -type d -name",
      "find . ! -name",
      "find / -type l",
      "find / -type b",
      "find / -type c",
      "find . -name '*.tmp'",
      "find . -size +100M",
      "find . -size -10k",
      "find . -size +1G",
      "find . -name '*.txt'",
      "find . -size 512c",
      "find . -name '*.py'",
      "find . -newer",
      "find . -type f -name",
      "reference_file",
      "find . -mtime -7",
      "find . -type f -newer",
      "find . -mtime +30",
      "find /tmp -mtime +7",
      "find . -mmin -60",
      "find . -name",
      "find . -atime -1",
      "find . -mount -name",
      "find . -ctime -1",
      "find . -xdev -name",
      "find . -perm 644",
      "find / -inum 12345",
      "find . -perm -644",
      "find . -links +1",
      "find . -perm /644",
      "find . -perm -4000",
      "find . -perm -2000",
      "updatedb",
      "find . -perm -1000",
      "find . -user",
      "find . -group",
      "find . -uid 1000",
      "find . -gid 1000",
      "cat",
      "find . -nouser"
    ],
    "examples": [
      "find / -name",
      "find . -nogroup",
      "find . -name '*.log'",
      "find . -empty",
      "find . -iname",
      "find . -maxdepth 2",
      "find / -type f -name",
      "find . -mindepth 2",
      "find / -type d -name",
      "find . ! -name",
      "find / -type l",
      "find / -type b",
      "find / -type c",
      "find . -name '*.tmp'",
      "find . -size +100M",
      "find . -size -10k",
      "find . -size +1G",
      "find . -name '*.txt'",
      "find . -size 512c",
      "find . -name '*.py'",
      "find . -newer",
      "find . -type f -name",
      "reference_file",
      "find . -mtime -7",
      "find . -type f -newer",
      "find . -mtime +30",
      "find /tmp -mtime +7",
      "find . -mmin -60",
      "find . -name",
      "find . -atime -1",
      "find . -mount -name",
      "find . -ctime -1",
      "find . -xdev -name",
      "find . -perm 644",
      "find / -inum 12345",
      "find . -perm -644",
      "find . -links +1",
      "find . -perm /644",
      "find . -perm -4000",
      "find . -perm -2000",
      "updatedb",
      "find . -perm -1000",
      "find . -user",
      "find . -group",
      "find . -uid 1000",
      "find . -gid 1000",
      "cat",
      "find . -nouser"
    ]
  },
  {
    "section": "Edytor Vim",
    "commands": [
      "vim file.txt",
      "c$",
      "vim +10 file.txt",
      "cw",
      "vim +/pattern",
      "cc",
      "vim -R file.txt",
      "dw",
      "d$",
      "vim -d file1 file2",
      "d0",
      "D",
      "vim -u NONE file.txt",
      "/pattern",
      "?pattern",
      "n",
      "N",
      "*",
      "i",
      "I",
      "a",
      "A",
      "o",
      "O",
      "Esc",
      "ZZ",
      "ZQ",
      "v",
      "V",
      "w",
      "Ctrl+v",
      "b",
      "gU",
      "e",
      "gu",
      "0",
      "$",
      "gg",
      "G",
      "10G",
      "Ctrl+f",
      "Ctrl+b",
      "Ctrl+d",
      "gt",
      "Ctrl+u",
      "gT",
      "dd",
      "5dd",
      "yy",
      "qa",
      "5yy",
      "q",
      "p",
      "P",
      "u",
      "Ctrl+r",
      "x",
      "X",
      "r",
      "cat ~/.vimrc",
      "R"
    ],
    "examples": [
      "vim file.txt",
      "c$",
      "vim +10 file.txt",
      "cw",
      "vim +/pattern",
      "cc",
      "vim -R file.txt",
      "dw",
      "d$",
      "vim -d file1 file2",
      "d0",
      "D",
      "vim -u NONE file.txt",
      "/pattern",
      "?pattern",
      "n",
      "N",
      "*",
      "i",
      "I",
      "a",
      "A",
      "o",
      "O",
      "Esc",
      "ZZ",
      "ZQ",
      "v",
      "V",
      "w",
      "Ctrl+v",
      "b",
      "gU",
      "e",
      "gu",
      "0",
      "$",
      "gg",
      "G",
      "10G",
      "Ctrl+f",
      "Ctrl+b",
      "Ctrl+d",
      "gt",
      "Ctrl+u",
      "gT",
      "dd",
      "5dd",
      "yy",
      "qa",
      "5yy",
      "q",
      "p",
      "P",
      "u",
      "Ctrl+r",
      "x",
      "X",
      "r",
      "cat ~/.vimrc",
      "R"
    ]
  },
  {
    "section": "Diagnostyka i narz■dzia systemowe",
    "commands": [
      "cat",
      "cmd",
      "ip -s link show eth0",
      "valgrind",
      "--leak-check=full",
      "cat /proc/sys/net/nf",
      "/var/log/sa/saDD",
      "kdump",
      "cat /etc/kdump.conf",
      "fio",
      "systemctl status",
      "--filename=/tmp/test",
      "count=1000",
      "bonnie++",
      "cat /proc/sys/kernel",
      "cat /proc/net/tcp",
      "cat /proc/PID/limits",
      "cat /proc/net/udp"
    ],
    "examples": [
      "cat",
      "cmd",
      "ip -s link show eth0",
      "valgrind",
      "--leak-check=full",
      "cat /proc/sys/net/nf",
      "/var/log/sa/saDD",
      "kdump",
      "cat /etc/kdump.conf",
      "fio",
      "systemctl status",
      "--filename=/tmp/test",
      "count=1000",
      "bonnie++",
      "cat /proc/sys/kernel",
      "cat /proc/net/tcp",
      "cat /proc/PID/limits",
      "cat /proc/net/udp"
    ]
  },
  {
    "section": "Skrypty bash — podstawy",
    "commands": [
      "esac",
      "chmod +x script.sh",
      "./script.sh",
      "}",
      "VAR='value'",
      "VAR=$(command)",
      "$@",
      "$#",
      "echo \"Value: $VAR\"",
      "$0",
      "$$",
      "$?",
      "then",
      "else",
      "2>/dev/null",
      "fi",
      "1>/dev/null",
      "echo ${ARRAY[@]}",
      "echo ${#ARRAY[@]}",
      "ARRAY+=('e')",
      "done",
      "do",
      "echo ${MAP[k1]}",
      "mktemp",
      "break",
      "continue",
      "TMPFILE=$(mktemp)"
    ],
    "examples": [
      "esac",
      "chmod +x script.sh",
      "./script.sh",
      "}",
      "VAR='value'",
      "VAR=$(command)",
      "$@",
      "$#",
      "echo \"Value: $VAR\"",
      "$0",
      "$$",
      "$?",
      "then",
      "else",
      "2>/dev/null",
      "fi",
      "1>/dev/null",
      "echo ${ARRAY[@]}",
      "echo ${#ARRAY[@]}",
      "ARRAY+=('e')",
      "done",
      "do",
      "echo ${MAP[k1]}",
      "mktemp",
      "break",
      "continue",
      "TMPFILE=$(mktemp)"
    ]
  },
  {
    "section": "Zaawansowane narz■dzia tekstowe",
    "commands": [
      "echo {1..5}",
      "echo file{1..3}.txt",
      "echo {a,b,c}.log",
      "echo $((RANDOM %",
      "100))",
      "32",
      "echo '3.14 * 2' | bc",
      "date",
      "gpg",
      "hwclock",
      "cat /etc/chrony.conf",
      "systemctl status",
      "file"
    ],
    "examples": [
      "echo {1..5}",
      "echo file{1..3}.txt",
      "echo {a,b,c}.log",
      "echo $((RANDOM %",
      "100))",
      "32",
      "echo '3.14 * 2' | bc",
      "date",
      "gpg",
      "hwclock",
      "cat /etc/chrony.conf",
      "systemctl status",
      "file"
    ]
  },
  {
    "section": "Zarz■dzanie dyskami RAID",
    "commands": [
      "--raid-devices=2",
      "/dev/md0",
      "--scan",
      "/dev/sdb",
      "cat /proc/mdstat",
      "mdadm",
      "/dev/sdd",
      "cat /etc/mdadm.conf"
    ],
    "examples": [
      "--raid-devices=2",
      "/dev/md0",
      "--scan",
      "/dev/sdb",
      "cat /proc/mdstat",
      "mdadm",
      "/dev/sdd",
      "cat /etc/mdadm.conf"
    ]
  },
  {
    "section": "Samba i NFS (klient)",
    "commands": [
      "smbclient",
      "//server",
      "testparm",
      "cat",
      "mount -t cifs",
      "cat /etc/fstab |",
      "systemctl restart",
      "grep cifs",
      "firewall-cmd"
    ],
    "examples": [
      "smbclient",
      "//server",
      "testparm",
      "cat",
      "mount -t cifs",
      "cat /etc/fstab |",
      "systemctl restart",
      "grep cifs",
      "firewall-cmd"
    ]
  },
  {
    "section": "Dodatkowe narz■dzia administracyjne",
    "commands": [
      "alternatives",
      "update-alternatives",
      "ntsysv",
      "systemd-cgtop",
      "systemd-cgls",
      "cat",
      "systemctl enable",
      "memory:mygroup",
      "scap-workbench",
      "t_in_bytes=512M",
      "mygroup",
      "cat /sys/fs/cgroup/m",
      "fips-mode-setup",
      "emory/mygroup/memory",
      "ls /sys/fs/cgroup/",
      "update-crypto-polici",
      "ip netns add myns",
      "ip netns exec myns",
      "bash",
      "ip netns list",
      "cat /etc/crypto-poli",
      "ip netns delete myns",
      "authselect",
      "/tmp/cap.pcap",
      "wireshark",
      "nmcli connection",
      "firewall-cmd",
      "systemctl status",
      "--zone=drop"
    ],
    "examples": [
      "alternatives",
      "update-alternatives",
      "ntsysv",
      "systemd-cgtop",
      "systemd-cgls",
      "cat",
      "systemctl enable",
      "memory:mygroup",
      "scap-workbench",
      "t_in_bytes=512M",
      "mygroup",
      "cat /sys/fs/cgroup/m",
      "fips-mode-setup",
      "emory/mygroup/memory",
      "ls /sys/fs/cgroup/",
      "update-crypto-polici",
      "ip netns add myns",
      "ip netns exec myns",
      "bash",
      "ip netns list",
      "cat /etc/crypto-poli",
      "ip netns delete myns",
      "authselect",
      "/tmp/cap.pcap",
      "wireshark",
      "nmcli connection",
      "firewall-cmd",
      "systemctl status",
      "--zone=drop"
    ]
  }
]
```

## `runtime/knowledge/permissions/README.md`

- size: 360 bytes
- sha256: `1bc493d9869441a987d4800ef93c0b84b2ea006d2b6b571d6a439f6d3ecbbcfe`
- category: knowledge

```markdown
# Permissions

Ownership, permission bits, access control basics, and safe permission checks.

## Modules

- `permissions/uprawnienia-i-wasno-plikow.md`: 31 imported commands from `Uprawnienia i w■asno■■ plików`

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
```

## `runtime/knowledge/permissions/uprawnienia-i-wasno-plikow.md`

- size: 11889 bytes
- sha256: `9a2ccb62ebe795c2ad4765e378879c95715a3d073d25ab19a529aeb3c4a47361`
- category: knowledge

```markdown
---
title: Uprawnienia i w■asno■■ plików
topic: permissions
source_section: Uprawnienia i w■asno■■ plików
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [chmod, chown, find, katalogu, linux, ls, permissions, rhcsa, umask, uprawnienia-i-wasno-plikow]
---

# Uprawnienia i w■asno■■ plików

Imported RHCSA material for 31 commands. Primary command families: chmod, chown, find, katalogu, ls, umask.

## Tags

chmod, chown, find, katalogu, linux, ls, permissions, rhcsa, umask, uprawnienia-i-wasno-plikow

## Examples

- `chmod 755 file`
- `chown`
- `chmod 644 file`
- `chmod 600 file`
- `chmod 777 file`
- `umask`
- `chmod u+x file`
- `w■a■ciciela`
- `chmod g-w file`
- `chmod o-r file`

## Troubleshooting

- Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Uprawnienia i w■asno■■ plików`

## Commands

### `chmod 755 file`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chmod`
- Examples:
  - `chmod 755 file`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `chown`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chown`
- Examples:
  - `chown`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `chmod 644 file`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chmod`
- Examples:
  - `chmod 644 file`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `chmod 600 file`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chmod`
- Examples:
  - `chmod 600 file`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `chmod 777 file`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chmod`
- Examples:
  - `chmod 777 file`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `umask`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `umask`
- Examples:
  - `umask`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `chmod u+x file`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chmod`
- Examples:
  - `chmod u+x file`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `w■a■ciciela`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `waciciela`
- Examples:
  - `w■a■ciciela`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `chmod g-w file`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chmod`
- Examples:
  - `chmod g-w file`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `chmod o-r file`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chmod`
- Examples:
  - `chmod o-r file`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `chmod a+r file`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chmod`
- Examples:
  - `chmod a+r file`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `chmod u=rwx,g=rx,o=r`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chmod`
- Examples:
  - `chmod u=rwx,g=rx,o=r`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `chmod -R 755 dir/`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chmod`
- Examples:
  - `chmod -R 755 dir/`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `katalogu`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `katalogu`
- Examples:
  - `katalogu`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `chmod`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chmod`
- Examples:
  - `chmod`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `chmod 4755 file`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chmod`
- Examples:
  - `chmod 4755 file`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `w■a■ciciel)`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `waciciel`
- Examples:
  - `w■a■ciciel)`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `chmod 2755 dir`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chmod`
- Examples:
  - `chmod 2755 dir`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `chmod 1755 dir`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chmod`
- Examples:
  - `chmod 1755 dir`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `chmod +t dir`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chmod`
- Examples:
  - `chmod +t dir`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `chmod u+s file`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chmod`
- Examples:
  - `chmod u+s file`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `chmod g+s dir`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chmod`
- Examples:
  - `chmod g+s dir`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `ls -Z file`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `ls`
- Examples:
  - `ls -Z file`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `chown user file`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chown`
- Examples:
  - `chown user file`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `chown user:group`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chown`
- Examples:
  - `chown user:group`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `find / -perm -4000`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `find`
- Examples:
  - `find / -perm -4000`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `chown :group file`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chown`
- Examples:
  - `chown :group file`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `find / -perm -2000`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `find`
- Examples:
  - `find / -perm -2000`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `chown -R user:group`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `chown`
- Examples:
  - `chown -R user:group`
- Troubleshooting hint:
  - Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `find / -perm -o+w`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `find`
- Examples:
  - `find / -perm -o+w`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`

### `dir/`

- Category: `Uprawnienia i w■asno■■ plików`
- Risk: `unclassified`
- Tags: `permissions`, `dir`
- Examples:
  - `dir/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Uprawnienia i w■asno■■ plików`
```

## `runtime/knowledge/podman/README.md`

- size: 323 bytes
- sha256: `affea5c5d83a9cc8577d0e347d412b53a00bb780d3783e958b872cb577fe75a4`
- category: knowledge

```markdown
# Podman

Podman images, containers, pods, volumes, networks, and rootless usage patterns.

## Modules

- `podman/kontenery-podman.md`: 109 imported commands from `Kontenery Podman`

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
```

## `runtime/knowledge/podman/kontenery-podman.md`

- size: 35613 bytes
- sha256: `35b2138379678d249cf29b77051382ce981ebbc9257697ec6d8a8ac998b8d891`
- category: knowledge

```markdown
---
title: Kontenery Podman
topic: podman
source_section: Kontenery Podman
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [cat, container, dst:tag, file.tar, image, image:tag, kontenery-podman, linux, podman, rhcsa]
---

# Kontenery Podman

Imported RHCSA material for 109 commands. Primary command families: cat, container, dst:tag, file.tar, image, image:tag, podman.

## Tags

cat, container, dst:tag, file.tar, image, image:tag, kontenery-podman, linux, podman, rhcsa

## Examples

- `podman --version`
- `podman exec`
- `podman info`
- `podman exec -u root`
- `podman images`
- `podman logs`
- `podman images -a`
- `podman logs -f`
- `podman pull`
- `podman logs --tail`

## Troubleshooting

- When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Kontenery Podman`

## Commands

### `podman --version`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman --version`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman exec`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman exec`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman info`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman info`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman exec -u root`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman exec -u root`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman images`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman images`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman logs`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman logs`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman images -a`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman images -a`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman logs -f`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman logs -f`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman pull`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman pull`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman logs --tail`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman logs --tail`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `image:tag`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `image:tag`
- Examples:
  - `image:tag`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman pull registry`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman pull registry`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman inspect`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman inspect`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `.access.redhat.com/u`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `access-redhat-com-u`
- Examples:
  - `.access.redhat.com/u`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman push`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman push`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman inspect -f`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman inspect -f`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman rmi image`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman rmi image`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman top container`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman top container`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman rmi -a`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman rmi -a`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman stats`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman stats`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman rmi -f image`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman rmi -f image`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman image inspect`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman image inspect`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman diff`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman diff`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `image`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `image`
- Examples:
  - `image`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman image history`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman image history`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman commit`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman commit`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman image prune`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman image prune`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman cp src`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman cp src`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman cp`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman cp`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `-a`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `a`
- Examples:
  - `-a`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman tag src:tag`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman tag src:tag`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman pause`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman pause`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `dst:tag`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `dst:tag`
- Examples:
  - `dst:tag`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman save image -o`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman save image -o`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman unpause`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman unpause`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `file.tar`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `file.tar`
- Examples:
  - `file.tar`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman load -i`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman load -i`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman rename`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman rename`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman search nginx`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman search nginx`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman port`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman port`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman search`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman search`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman network ls`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman network ls`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman network`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman network`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `--list-tags`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `list-tags`
- Examples:
  - `--list-tags`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman run image`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman run image`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman network rm`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman network rm`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman run -it image`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman run -it image`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `/bin/bash`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `bin-bash`
- Examples:
  - `/bin/bash`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman run -d image`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman run -d image`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman run --name`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman run --name`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman run -p`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman run -p`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman volume ls`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman volume ls`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman run -v`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman run -v`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman volume create`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman volume create`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `/host:/container`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `host-container`
- Examples:
  - `/host:/container`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman volume rm`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman volume rm`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman run -e`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman run -e`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman volume`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman volume`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman run`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman run`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman volume prune`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman volume prune`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman run --rm`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman run --rm`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman build -t`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman build -t`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman build -f`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman build -f`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `--restart=always`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `restart-always`
- Examples:
  - `--restart=always`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman run --restart`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman run --restart`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman build`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman build`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman run -u user`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman run -u user`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `cat Containerfile`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `cat`
- Examples:
  - `cat Containerfile`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman run --cap-add`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman run --cap-add`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman generate`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman generate`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman run --memory`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman run --memory`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman play kube`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman play kube`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman run --cpus`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman run --cpus`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman generate kube`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman generate kube`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman run --network`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman run --network`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman pod ls`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman pod ls`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman pod create`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman pod create`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman pod rm mypod`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman pod rm mypod`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman ps`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman ps`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman pod start`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman pod start`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman ps -a`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman ps -a`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman pod stop`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman pod stop`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman ps -q`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman ps -q`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman pod stats`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman pod stats`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman ps -qa`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman ps -qa`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman pod inspect`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman pod inspect`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman ps --format`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman ps --format`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman run --pod`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman run --pod`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman stop`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman stop`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman system prune`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman system prune`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman stop -t 0`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman stop -t 0`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `container`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `container`
- Examples:
  - `container`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman start`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman start`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman system df`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman system df`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman restart`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman restart`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman system reset`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman system reset`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman kill`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman kill`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman login`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman login`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman kill -s`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman kill -s`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman logout`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman logout`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman rm container`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman rm container`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `cat /etc/containers/`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `cat`
- Examples:
  - `cat /etc/containers/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman rm -f`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman rm -f`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman rm -a`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman rm -a`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman unshare`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman unshare`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman container`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman container`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman machine init`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman machine init`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman exec -it`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman exec -it`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`

### `podman machine start`

- Category: `Kontenery Podman`
- Risk: `unclassified`
- Tags: `podman`, `podman`
- Examples:
  - `podman machine start`
- Troubleshooting hint:
  - When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.
- Provenance:
  - RHCSA section: `Kontenery Podman`
```

## `runtime/knowledge/raw/rhcsa_raw.txt`

- size: 198795 bytes
- sha256: `6290f1ff6ccc72bd5c571dc7a9fef0014cfd5650b88127038cb69ef33d5e8c9d`
- category: knowledge

Content omitted from inline markdown because this generated artifact is 198795 bytes.
Full file is preserved at `source_export/runtime/knowledge/raw/rhcsa_raw.txt`.

## `runtime/knowledge/reports/category_distribution.md`

- size: 383 bytes
- sha256: `f34741e23c40927c51b13c1b7acc44b53eadafc51777fef232cec840c4140a17`
- category: knowledge

```markdown
# Candidate Category Distribution

- Automation: 219
- Bash: 404
- File Management: 345
- Gemini Expansion Additions: 25
- Logs: 83
- Networking: 409
- Packages: 122
- Processes: 167
- RHCSA Exam Tasks: 568
- SSH: 65
- Security: 195
- Storage: 229
- Systemd: 123
- Users & Permissions: 198

## By Status

- candidate: 1978
- duplicate_existing: 1077
- malformed: 76
- unresolved: 21
```

## `runtime/knowledge/reports/deduplication_report.md`

- size: 2753 bytes
- sha256: `c6f93a322cef32b107f320f2b3eed003c54a709d3c047bb2985359e6348fa6f5`
- category: knowledge

```markdown
# Candidate Deduplication Report

- Total parsed entries: 3152
- Total unique candidate commands: 2570
- Duplicates against existing canonical/index: 725
- Internal candidate duplicates: 582

## Duplicate Type Counts

- candidate_internal: 382
- canonical+command_index: 481
- canonical+command_index+candidate_internal: 193
- command_index: 44
- command_index+candidate_internal: 7
- new_candidate: 2045

## Sample Existing Duplicates

- `basename` -> canonical+command_index
- `cat` -> canonical+command_index
- `cat -A file.txt` -> canonical+command_index
- `cat -n file.txt` -> canonical+command_index
- `cat /etc/anacrontab` -> canonical+command_index
- `cat /etc/bashrc` -> canonical+command_index
- `cat /etc/cron.allow` -> canonical+command_index
- `cat /etc/cron.deny` -> canonical+command_index
- `cat /etc/crontab` -> canonical+command_index
- `cat /etc/exports` -> canonical+command_index
- `cat /etc/fstab` -> canonical+command_index
- `cat /etc/os-release` -> canonical+command_index
- `cat /etc/profile` -> canonical+command_index
- `cat /etc/systemd/sys` -> canonical+command_index
- `cat /proc/cmdline` -> canonical+command_index
- `cat /proc/cpuinfo` -> canonical+command_index
- `cat /proc/mdstat` -> canonical+command_index
- `cat /proc/meminfo` -> canonical+command_index
- `cat /proc/mounts` -> canonical+command_index
- `cat /proc/net/tcp` -> canonical+command_index
- `cat /proc/net/udp` -> canonical+command_index
- `cat /proc/sys/kernel` -> canonical+command_index
- `cat /proc/version` -> canonical+command_index
- `cat /sys/fs/cgroup/m` -> canonical+command_index
- `cat /var/log/audit/a` -> canonical+command_index
- `cat /var/log/cron` -> canonical+command_index
- `cat /var/log/maillog` -> canonical+command_index
- `cat /var/log/secure` -> canonical+command_index
- `cat /var/spool/cron/` -> canonical+command_index
- `cat file.txt` -> canonical+command_index
- `cat file1 file2` -> canonical+command_index
- `cat ~/.bash_logout` -> canonical+command_index
- `cat ~/.bash_profile` -> canonical+command_index
- `cat ~/.bashrc` -> canonical+command_index
- `cd` -> command_index
- `cd -` -> canonical+command_index
- `cd /` -> canonical+command_index
- `cd /path/to/dir` -> canonical+command_index
- `cd ~` -> canonical+command_index
- `cp` -> command_index
- `cp --backup src dst` -> canonical+command_index
- `cp -a src/ dst/` -> canonical+command_index
- `cp -i src dst` -> canonical+command_index
- `cp -p src dst` -> canonical+command_index
- `cp -r src/ dst/` -> canonical+command_index
- `cp -u src dst` -> canonical+command_index
- `cp -v src dst` -> canonical+command_index
- `cp source dest` -> canonical+command_index
- `df` -> command_index
- `diff` -> command_index

Canonical runtime files were not modified.
```

## `runtime/knowledge/reports/parsing_quality_report.md`

- size: 5457 bytes
- sha256: `6ed0b3f79d8a2fb2d7af87345321464cfac89185b5e7bf147041dab8bfcb16ce`
- category: knowledge

```markdown
# Candidate Parsing Quality Report

- Total parsed entries: 3152
- Candidate records written: 3152
- Malformed or unresolved entries: 97

## Status Counts

- candidate: 1978
- duplicate_existing: 1077
- malformed: 76
- unresolved: 21

## Quality Flag Counts

- complex_pipeline_or_snippet: 1
- invalid_base_command: 2
- likely_contamination_or_comment: 7
- path_not_command: 74
- probable_pdf_merge_artifact: 16
- weak_description: 625

## Sample Malformed/Unresolved Entries

- line 3720: `cd $(dirname "$0") without symlink'` (likely_contamination_or_comment)
- line 4022: `file` (probable_pdf_merge_artifact)
- line 4028: `file '/start/,/end/p'` (weak_description, probable_pdf_merge_artifact)
- line 4033: `file -b /bin/ls` (probable_pdf_merge_artifact)
- line 4038: `file -out file.enc` (probable_pdf_merge_artifact)
- line 4048: `file /etc/passwd` (weak_description, probable_pdf_merge_artifact)
- line 4053: `file 2>/dev/null` (weak_description, probable_pdf_merge_artifact)
- line 4058: `file chronyd` (probable_pdf_merge_artifact)
- line 4063: `file file` (weak_description, probable_pdf_merge_artifact)
- line 4068: `file grup` (weak_description, probable_pdf_merge_artifact)
- line 4073: `file kadej linii` (weak_description, probable_pdf_merge_artifact)
- line 4078: `file regularnego` (weak_description, probable_pdf_merge_artifact)
- line 4083: `file symboliczne u:user:rwx file` (probable_pdf_merge_artifact)
- line 5092: `rm -rf / or rm -rf $VAR/ when $VAR unset.'` (likely_contamination_or_comment, weak_description)
- line 5102: `rm -rf /var/log/journal bypassing vacuum logic.'` (likely_contamination_or_comment, weak_description)
- line 5287: `touch file` (probable_pdf_merge_artifact)
- line 5292: `touch file.txt` (weak_description, probable_pdf_merge_artifact)
- line 5297: `touch kernel logic` (likely_contamination_or_comment, probable_pdf_merge_artifact)
- line 5302: `touch planner systems` (likely_contamination_or_comment, probable_pdf_merge_artifact)
- line 6525: `/etc/hostname` (path_not_command)
- line 6530: `/etc/hosts` (path_not_command)
- line 6535: `/etc/resolv.conf` (path_not_command)
- line 6990: `firewall-cmd --runtime-to-permanent` (likely_contamination_or_comment)
- line 8852: `/proc` (path_not_command)
- line 10458: `'systemctl edit“` (invalid_base_command)
- line 11826: `/backup/xfs.dump` (path_not_command, weak_description)
- line 11831: `/bin/backup.sh` (path_not_command, weak_description)
- line 11836: `/bin/task.sh` (path_not_command)
- line 11846: `/boot` (path_not_command)
- line 11851: `/check.sh` (path_not_command, weak_description)
- line 11856: `/dev/md0` (path_not_command)
- line 11861: `/dev/null` (path_not_command)
- line 11866: `/dev/nvme0n1` (path_not_command)
- line 11871: `/dev/sda` (path_not_command)
- line 11876: `/dev/sdb` (path_not_command)
- line 11881: `/dev/sdb1` (path_not_command)
- line 11891: `/dev/sdc` (path_not_command)
- line 11896: `/dev/sdd` (path_not_command)
- line 11901: `/dev/tty` (path_not_command)
- line 11906: `/dev/urandom` (path_not_command)
- line 11911: `/dev/vgname/lvname` (path_not_command, weak_description)
- line 11916: `/dev/vgname/snapname` (path_not_command, weak_description)
- line 11921: `/etc` (path_not_command)
- line 11926: `/etc/anacrontab` (path_not_command)
- line 11936: `/etc/audit/auditd.conf` (path_not_command)
- line 11941: `/etc/auto.nfs` (path_not_command, weak_description)
- line 11946: `/etc/centos-release` (path_not_command, weak_description)
- line 11951: `/etc/chrony.conf` (path_not_command)
- line 11956: `/etc/cron.d` (path_not_command)
- line 11961: `/etc/cron.daily` (path_not_command)
- line 11966: `/etc/cron.hourly` (path_not_command)
- line 11971: `/etc/cron.monthly` (path_not_command)
- line 11981: `/etc/cron.weekly` (path_not_command)
- line 11986: `/etc/crontab` (path_not_command)
- line 11991: `/etc/crypttab` (path_not_command)
- line 11996: `/etc/default/grub` (path_not_command, weak_description)
- line 12001: `/etc/fstab` (path_not_command)
- line 12006: `/etc/logrotate.conf` (path_not_command, weak_description)
- line 12011: `/etc/nftables.conf` (path_not_command)
- line 12016: `/etc/pam.d/system-auth` (path_not_command)
- line 12026: `/etc/passwd` (path_not_command, weak_description)
- line 12031: `/etc/redhat-release` (path_not_command, weak_description)
- line 12036: `/etc/rsyslog.conf` (path_not_command, weak_description)
- line 12041: `/etc/sssd/sssd.conf` (path_not_command)
- line 12046: `/etc/sudoers` (path_not_command)
- line 12051: `/etc/sysctl.conf` (path_not_command)
- line 12056: `/etc/sysctl.d/99-hardening.conf` (path_not_command)
- line 12061: `/etc/systemd/system/secure_processor.service` (path_not_command)
- line 12071: `/etc/updatedb.conf` (path_not_command, weak_description)
- line 12076: `/hostname` (path_not_command, weak_description)
- line 12081: `/mnt` (path_not_command, weak_description)
- line 12086: `/path` (path_not_command, weak_description)
- line 12091: `/path/to/file` (path_not_command, weak_description)
- line 12096: `/path/to/key.gpg` (path_not_command, weak_description)
- line 12101: `/path/to/module.ko` (path_not_command, weak_description)
- line 12106: `/path/to/script.sh` (path_not_command)
- line 12116: `/proc/net/sockstat` (path_not_command)
- line 12121: `/sbin/init` (path_not_command)
- line 12126: `/tmp` (path_not_command)
- line 12132: `/tmp/cap.pcap` (path_not_command)

No command rows were promoted to canonical indexes.
```

## `runtime/knowledge/reports/retrieval_engine_report.md`

- size: 3764 bytes
- sha256: `68f6f50f08e1db02b9ea6dea5606767b42c5fd4d6457340e3bfb6c4f6a638580`
- category: knowledge

```markdown
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
```

## `runtime/knowledge/schema/command.schema.json`

- size: 2467 bytes
- sha256: `8af744dada5d8a7d863cf2980e657109f998a9fcb0faa90e2bc052e9d2e49f24`
- category: knowledge

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://aoia.local/schema/command.schema.json",
  "title": "AOIA Command Knowledge Entry",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "id",
    "command",
    "description",
    "category",
    "tags",
    "risk",
    "os",
    "shell",
    "examples"
  ],
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$"
    },
    "command": {
      "type": "string",
      "minLength": 1
    },
    "description": {
      "type": "string",
      "minLength": 1,
      "maxLength": 240
    },
    "category": {
      "type": "string",
      "enum": [
        "archive",
        "diagnostic",
        "filesystem",
        "network",
        "package",
        "process",
        "security",
        "service",
        "system",
        "user"
      ]
    },
    "tags": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "string",
        "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$"
      }
    },
    "risk": {
      "type": "string",
      "enum": [
        "low",
        "medium",
        "high",
        "critical"
      ]
    },
    "os": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "string",
        "enum": [
          "linux",
          "rhel",
          "ubuntu",
          "debian",
          "fedora",
          "macos"
        ]
      }
    },
    "shell": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "string",
        "enum": [
          "bash",
          "sh",
          "zsh"
        ]
      }
    },
    "examples": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "input",
          "expected_effect"
        ],
        "properties": {
          "input": {
            "type": "string",
            "minLength": 1
          },
          "expected_effect": {
            "type": "string",
            "minLength": 1,
            "maxLength": 240
          }
        }
      }
    },
    "notes": {
      "type": "string",
      "maxLength": 500
    },
    "related_commands": {
      "type": "array",
      "uniqueItems": true,
      "items": {
        "type": "string",
        "pattern": "^[a-z0-9._+-]+$"
      }
    }
  }
}
```

## `runtime/knowledge/selinux/README.md`

- size: 307 bytes
- sha256: `7db0c2e67b2046063a1c1d8fb95fda8ee26b4efdd8b705cb466da521bfccd736`
- category: knowledge

```markdown
# Selinux

SELinux inspection, contexts, booleans, labeling, and policy-related remediation.

## Modules

- `selinux/selinux.md`: 36 imported commands from `SELinux`

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
```

## `runtime/knowledge/selinux/selinux.md`

- size: 11784 bytes
- sha256: `1cbbde7010c41440aa1651de04fb76ef60a288e2242260de2f379700f06c12c9`
- category: knowledge

```markdown
---
title: SELinux
topic: selinux
source_section: SELinux
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [cat, getenforce, grep, httpd_sys_content_t, journalctl, linux, ls, matchpathcon, restorecon, rhcsa, selinux, semanage, sestatus, setsebool, touch]
---

# SELinux

Imported RHCSA material for 36 commands. Primary command families: cat, getenforce, grep, httpd_sys_content_t, journalctl, ls, matchpathcon, restorecon.

## Tags

cat, getenforce, grep, httpd_sys_content_t, journalctl, linux, ls, matchpathcon, restorecon, rhcsa, selinux, semanage, sestatus, setsebool, touch

## Examples

- `getenforce`
- `setsebool httpd_can_`
- `sestatus`
- `setsebool -P httpd_c`
- `setsebool -P`
- `cat`
- `setsebool -P samba_e`
- `/etc/selinux/config`
- `ls -Z dir/`
- `semanage user -l`

## Troubleshooting

- Quote patterns explicitly to avoid shell expansion when matching text.
- Use time or unit filters first to keep logs readable on low-RAM systems.
- Correlate AVC denials with labels and booleans before disabling SELinux protections.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `SELinux`

## Commands

### `getenforce`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `getenforce`
- Examples:
  - `getenforce`
- Troubleshooting hint:
  - Correlate AVC denials with labels and booleans before disabling SELinux protections.
- Provenance:
  - RHCSA section: `SELinux`

### `setsebool httpd_can_`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `setsebool`
- Examples:
  - `setsebool httpd_can_`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SELinux`

### `sestatus`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `sestatus`
- Examples:
  - `sestatus`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SELinux`

### `setsebool -P httpd_c`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `setsebool`
- Examples:
  - `setsebool -P httpd_c`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SELinux`

### `setsebool -P`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `setsebool`
- Examples:
  - `setsebool -P`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SELinux`

### `cat`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `cat`
- Examples:
  - `cat`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SELinux`

### `setsebool -P samba_e`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `setsebool`
- Examples:
  - `setsebool -P samba_e`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SELinux`

### `/etc/selinux/config`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `etc-selinux-config`
- Examples:
  - `/etc/selinux/config`
- Troubleshooting hint:
  - Correlate AVC denials with labels and booleans before disabling SELinux protections.
- Provenance:
  - RHCSA section: `SELinux`

### `ls -Z dir/`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `ls`
- Examples:
  - `ls -Z dir/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SELinux`

### `semanage user -l`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `semanage`
- Examples:
  - `semanage user -l`
- Troubleshooting hint:
  - Correlate AVC denials with labels and booleans before disabling SELinux protections.
- Provenance:
  - RHCSA section: `SELinux`

### `ls -dZ dir/`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `ls`
- Examples:
  - `ls -dZ dir/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SELinux`

### `semanage login -l`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `semanage`
- Examples:
  - `semanage login -l`
- Troubleshooting hint:
  - Correlate AVC denials with labels and booleans before disabling SELinux protections.
- Provenance:
  - RHCSA section: `SELinux`

### `semanage login -a -s`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `semanage`
- Examples:
  - `semanage login -a -s`
- Troubleshooting hint:
  - Correlate AVC denials with labels and booleans before disabling SELinux protections.
- Provenance:
  - RHCSA section: `SELinux`

### `SELinux`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `selinux`
- Examples:
  - `SELinux`
- Troubleshooting hint:
  - Correlate AVC denials with labels and booleans before disabling SELinux protections.
- Provenance:
  - RHCSA section: `SELinux`

### `httpd_sys_content_t`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `httpd_sys_content_t`
- Examples:
  - `httpd_sys_content_t`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SELinux`

### `restorecon`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `restorecon`
- Examples:
  - `restorecon`
- Troubleshooting hint:
  - Correlate AVC denials with labels and booleans before disabling SELinux protections.
- Provenance:
  - RHCSA section: `SELinux`

### `/path/to/file`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `path-to-file`
- Examples:
  - `/path/to/file`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SELinux`

### `restorecon -R`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `restorecon`
- Examples:
  - `restorecon -R`
- Troubleshooting hint:
  - Correlate AVC denials with labels and booleans before disabling SELinux protections.
- Provenance:
  - RHCSA section: `SELinux`

### `restorecon -Rv`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `restorecon`
- Examples:
  - `restorecon -Rv`
- Troubleshooting hint:
  - Correlate AVC denials with labels and booleans before disabling SELinux protections.
- Provenance:
  - RHCSA section: `SELinux`

### `restorecon -F /path/`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `restorecon`
- Examples:
  - `restorecon -F /path/`
- Troubleshooting hint:
  - Correlate AVC denials with labels and booleans before disabling SELinux protections.
- Provenance:
  - RHCSA section: `SELinux`

### `semanage fcontext -l`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `semanage`
- Examples:
  - `semanage fcontext -l`
- Troubleshooting hint:
  - Correlate AVC denials with labels and booleans before disabling SELinux protections.
- Provenance:
  - RHCSA section: `SELinux`

### `semanage fcontext -a`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `semanage`
- Examples:
  - `semanage fcontext -a`
- Troubleshooting hint:
  - Correlate AVC denials with labels and booleans before disabling SELinux protections.
- Provenance:
  - RHCSA section: `SELinux`

### `-t`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `t`
- Examples:
  - `-t`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SELinux`

### `semanage fcontext -d`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `semanage`
- Examples:
  - `semanage fcontext -d`
- Troubleshooting hint:
  - Correlate AVC denials with labels and booleans before disabling SELinux protections.
- Provenance:
  - RHCSA section: `SELinux`

### `journalctl -t`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `journalctl`
- Examples:
  - `journalctl -t`
- Troubleshooting hint:
  - Use time or unit filters first to keep logs readable on low-RAM systems.
- Provenance:
  - RHCSA section: `SELinux`

### `semanage fcontext -m`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `semanage`
- Examples:
  - `semanage fcontext -m`
- Troubleshooting hint:
  - Correlate AVC denials with labels and booleans before disabling SELinux protections.
- Provenance:
  - RHCSA section: `SELinux`

### `matchpathcon`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `matchpathcon`
- Examples:
  - `matchpathcon`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SELinux`

### `semanage port -l`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `semanage`
- Examples:
  - `semanage port -l`
- Troubleshooting hint:
  - Correlate AVC denials with labels and booleans before disabling SELinux protections.
- Provenance:
  - RHCSA section: `SELinux`

### `semanage port -l |`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `semanage`
- Examples:
  - `semanage port -l |`
- Troubleshooting hint:
  - Correlate AVC denials with labels and booleans before disabling SELinux protections.
- Provenance:
  - RHCSA section: `SELinux`

### `semanage port -a -t`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `semanage`
- Examples:
  - `semanage port -a -t`
- Troubleshooting hint:
  - Correlate AVC denials with labels and booleans before disabling SELinux protections.
- Provenance:
  - RHCSA section: `SELinux`

### `semanage port -d -t`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `semanage`
- Examples:
  - `semanage port -d -t`
- Troubleshooting hint:
  - Correlate AVC denials with labels and booleans before disabling SELinux protections.
- Provenance:
  - RHCSA section: `SELinux`

### `cat /var/log/audit/a`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `cat`
- Examples:
  - `cat /var/log/audit/a`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SELinux`

### `semanage port -m -t`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `semanage`
- Examples:
  - `semanage port -m -t`
- Troubleshooting hint:
  - Correlate AVC denials with labels and booleans before disabling SELinux protections.
- Provenance:
  - RHCSA section: `SELinux`

### `grep 'denied' /var/l`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `grep`
- Examples:
  - `grep 'denied' /var/l`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `SELinux`

### `semanage boolean -l`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `semanage`
- Examples:
  - `semanage boolean -l`
- Troubleshooting hint:
  - Correlate AVC denials with labels and booleans before disabling SELinux protections.
- Provenance:
  - RHCSA section: `SELinux`

### `touch /.autorelabel`

- Category: `SELinux`
- Risk: `unclassified`
- Tags: `selinux`, `touch`
- Examples:
  - `touch /.autorelabel`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `SELinux`
```

## `runtime/knowledge/storage/README.md`

- size: 565 bytes
- sha256: `a2a042efa09df4588bb2cc15d97504b8b31d6e6bb377eb889fa64efba0de2a96`
- category: knowledge

```markdown
# Storage

Disks, partitions, filesystems, mount operations, RAID, and persistence checks.

## Modules

- `storage/przechowywanie-danych-dyski-i-partycje.md`: 5 imported commands from `Przechowywanie danych — dyski i partycje`
- `storage/systemy-plikow-i-montowanie.md`: 17 imported commands from `Systemy plików i montowanie`
- `storage/zarzdzanie-dyskami-raid.md`: 7 imported commands from `Zarz■dzanie dyskami RAID`

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
```

## `runtime/knowledge/storage/przechowywanie-danych-dyski-i-partycje.md`

- size: 2736 bytes
- sha256: `e7d4aee0363e0d1a978e04bc1733d302605062c8388c550472291d08c20b7855`
- category: knowledge

```markdown
---
title: Przechowywanie danych — dyski i partycje
topic: storage
source_section: Przechowywanie danych — dyski i partycje
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [blkid, linux, lsblk, partprobe, print, przechowywanie-danych-dyski-i-partycje, rhcsa, storage]
---

# Przechowywanie danych — dyski i partycje

Imported RHCSA material for 5 commands. Primary command families: blkid, lsblk, partprobe, print.

## Tags

blkid, linux, lsblk, partprobe, print, przechowywanie-danych-dyski-i-partycje, rhcsa, storage

## Examples

- `lsblk`
- `print`
- `partprobe`
- `dysków`
- `blkid`

## Troubleshooting

- Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Przechowywanie danych — dyski i partycje`

## Commands

### `lsblk`

- Category: `Przechowywanie danych — dyski i partycje`
- Risk: `unclassified`
- Tags: `storage`, `lsblk`
- Examples:
  - `lsblk`
- Troubleshooting hint:
  - Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.
- Provenance:
  - RHCSA section: `Przechowywanie danych — dyski i partycje`

### `print`

- Category: `Przechowywanie danych — dyski i partycje`
- Risk: `unclassified`
- Tags: `storage`, `print`
- Examples:
  - `print`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Przechowywanie danych — dyski i partycje`

### `partprobe`

- Category: `Przechowywanie danych — dyski i partycje`
- Risk: `unclassified`
- Tags: `storage`, `partprobe`
- Examples:
  - `partprobe`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Przechowywanie danych — dyski i partycje`

### `dysków`

- Category: `Przechowywanie danych — dyski i partycje`
- Risk: `unclassified`
- Tags: `storage`, `dyskow`
- Examples:
  - `dysków`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Przechowywanie danych — dyski i partycje`

### `blkid`

- Category: `Przechowywanie danych — dyski i partycje`
- Risk: `unclassified`
- Tags: `storage`, `blkid`
- Examples:
  - `blkid`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Przechowywanie danych — dyski i partycje`
```

## `runtime/knowledge/storage/systemy-plikow-i-montowanie.md`

- size: 6784 bytes
- sha256: `58c842ba2f67f0931b8e3998d65af8b05c42021084fd4aac2ea29cb96b4c0f7d`
- category: knowledge

```markdown
---
title: Systemy plików i montowanie
topic: storage
source_section: Systemy plików i montowanie
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [cat, findmnt, linux, montowania, mount, rhcsa, storage, systemy-plikow-i-montowanie]
---

# Systemy plików i montowanie

Imported RHCSA material for 17 commands. Primary command families: cat, findmnt, montowania, mount.

## Tags

cat, findmnt, linux, montowania, mount, rhcsa, storage, systemy-plikow-i-montowanie

## Examples

- `cat /etc/fstab`
- `mount | column -t`
- `/dev/sdb1`
- `mount /dev/sdb1 /mnt`
- `mount -t ext4`
- `mount -t xfs`
- `mount -o ro`
- `mount -o rw,noexec`
- `mount -o remount,rw`
- `/mnt`

## Troubleshooting

- Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Systemy plików i montowanie`

## Commands

### `cat /etc/fstab`

- Category: `Systemy plików i montowanie`
- Risk: `unclassified`
- Tags: `storage`, `cat`
- Examples:
  - `cat /etc/fstab`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Systemy plików i montowanie`

### `mount | column -t`

- Category: `Systemy plików i montowanie`
- Risk: `unclassified`
- Tags: `storage`, `mount`
- Examples:
  - `mount | column -t`
- Troubleshooting hint:
  - Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.
- Provenance:
  - RHCSA section: `Systemy plików i montowanie`

### `/dev/sdb1`

- Category: `Systemy plików i montowanie`
- Risk: `unclassified`
- Tags: `storage`, `dev-sdb1`
- Examples:
  - `/dev/sdb1`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Systemy plików i montowanie`

### `mount /dev/sdb1 /mnt`

- Category: `Systemy plików i montowanie`
- Risk: `unclassified`
- Tags: `storage`, `mount`
- Examples:
  - `mount /dev/sdb1 /mnt`
- Troubleshooting hint:
  - Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.
- Provenance:
  - RHCSA section: `Systemy plików i montowanie`

### `mount -t ext4`

- Category: `Systemy plików i montowanie`
- Risk: `unclassified`
- Tags: `storage`, `mount`
- Examples:
  - `mount -t ext4`
- Troubleshooting hint:
  - Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.
- Provenance:
  - RHCSA section: `Systemy plików i montowanie`

### `mount -t xfs`

- Category: `Systemy plików i montowanie`
- Risk: `unclassified`
- Tags: `storage`, `mount`
- Examples:
  - `mount -t xfs`
- Troubleshooting hint:
  - Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.
- Provenance:
  - RHCSA section: `Systemy plików i montowanie`

### `mount -o ro`

- Category: `Systemy plików i montowanie`
- Risk: `unclassified`
- Tags: `storage`, `mount`
- Examples:
  - `mount -o ro`
- Troubleshooting hint:
  - Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.
- Provenance:
  - RHCSA section: `Systemy plików i montowanie`

### `mount -o rw,noexec`

- Category: `Systemy plików i montowanie`
- Risk: `unclassified`
- Tags: `storage`, `mount`
- Examples:
  - `mount -o rw,noexec`
- Troubleshooting hint:
  - Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.
- Provenance:
  - RHCSA section: `Systemy plików i montowanie`

### `mount -o remount,rw`

- Category: `Systemy plików i montowanie`
- Risk: `unclassified`
- Tags: `storage`, `mount`
- Examples:
  - `mount -o remount,rw`
- Troubleshooting hint:
  - Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.
- Provenance:
  - RHCSA section: `Systemy plików i montowanie`

### `/mnt`

- Category: `Systemy plików i montowanie`
- Risk: `unclassified`
- Tags: `storage`, `mnt`
- Examples:
  - `/mnt`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Systemy plików i montowanie`

### `mount -o remount,ro`

- Category: `Systemy plików i montowanie`
- Risk: `unclassified`
- Tags: `storage`, `mount`
- Examples:
  - `mount -o remount,ro`
- Troubleshooting hint:
  - Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.
- Provenance:
  - RHCSA section: `Systemy plików i montowanie`

### `mount UUID=xxx /mnt`

- Category: `Systemy plików i montowanie`
- Risk: `unclassified`
- Tags: `storage`, `mount`
- Examples:
  - `mount UUID=xxx /mnt`
- Troubleshooting hint:
  - Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.
- Provenance:
  - RHCSA section: `Systemy plików i montowanie`

### `mount LABEL=mylabel`

- Category: `Systemy plików i montowanie`
- Risk: `unclassified`
- Tags: `storage`, `mount`
- Examples:
  - `mount LABEL=mylabel`
- Troubleshooting hint:
  - Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.
- Provenance:
  - RHCSA section: `Systemy plików i montowanie`

### `mount -a`

- Category: `Systemy plików i montowanie`
- Risk: `unclassified`
- Tags: `storage`, `mount`
- Examples:
  - `mount -a`
- Troubleshooting hint:
  - Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.
- Provenance:
  - RHCSA section: `Systemy plików i montowanie`

### `findmnt`

- Category: `Systemy plików i montowanie`
- Risk: `unclassified`
- Tags: `storage`, `findmnt`
- Examples:
  - `findmnt`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Systemy plików i montowanie`

### `montowania`

- Category: `Systemy plików i montowanie`
- Risk: `unclassified`
- Tags: `storage`, `montowania`
- Examples:
  - `montowania`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Systemy plików i montowanie`

### `cat /proc/mounts`

- Category: `Systemy plików i montowanie`
- Risk: `unclassified`
- Tags: `storage`, `cat`
- Examples:
  - `cat /proc/mounts`
- Troubleshooting hint:
  - Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.
- Provenance:
  - RHCSA section: `Systemy plików i montowanie`
```

## `runtime/knowledge/storage/zarzdzanie-dyskami-raid.md`

- size: 3158 bytes
- sha256: `1c55fcd6b1352a3c08567657b63c6033b9baf0b6eae05677377d2e4c196e713a`
- category: knowledge

```markdown
---
title: Zarz■dzanie dyskami RAID
topic: storage
source_section: Zarz■dzanie dyskami RAID
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [cat, linux, mdadm, rhcsa, storage, zarzdzanie-dyskami-raid]
---

# Zarz■dzanie dyskami RAID

Imported RHCSA material for 7 commands. Primary command families: cat, mdadm.

## Tags

cat, linux, mdadm, rhcsa, storage, zarzdzanie-dyskami-raid

## Examples

- `--raid-devices=2`
- `/dev/md0`
- `--scan`
- `cat /proc/mdstat`
- `mdadm`
- `/dev/sdd`
- `cat /etc/mdadm.conf`

## Troubleshooting

- Validate command intent against current host state before applying changes in production.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Zarz■dzanie dyskami RAID`

## Commands

### `--raid-devices=2`

- Category: `Zarz■dzanie dyskami RAID`
- Risk: `unclassified`
- Tags: `storage`, `raid-devices-2`
- Examples:
  - `--raid-devices=2`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie dyskami RAID`

### `/dev/md0`

- Category: `Zarz■dzanie dyskami RAID`
- Risk: `unclassified`
- Tags: `storage`, `dev-md0`
- Examples:
  - `/dev/md0`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie dyskami RAID`

### `--scan`

- Category: `Zarz■dzanie dyskami RAID`
- Risk: `unclassified`
- Tags: `storage`, `scan`
- Examples:
  - `--scan`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie dyskami RAID`

### `cat /proc/mdstat`

- Category: `Zarz■dzanie dyskami RAID`
- Risk: `unclassified`
- Tags: `storage`, `cat`
- Examples:
  - `cat /proc/mdstat`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie dyskami RAID`

### `mdadm`

- Category: `Zarz■dzanie dyskami RAID`
- Risk: `unclassified`
- Tags: `storage`, `mdadm`
- Examples:
  - `mdadm`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie dyskami RAID`

### `/dev/sdd`

- Category: `Zarz■dzanie dyskami RAID`
- Risk: `unclassified`
- Tags: `storage`, `dev-sdd`
- Examples:
  - `/dev/sdd`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie dyskami RAID`

### `cat /etc/mdadm.conf`

- Category: `Zarz■dzanie dyskami RAID`
- Risk: `unclassified`
- Tags: `storage`, `cat`
- Examples:
  - `cat /etc/mdadm.conf`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie dyskami RAID`
```

## `runtime/knowledge/systemd/README.md`

- size: 637 bytes
- sha256: `b5f461f9c876c01cb3a1db42829f3d51ae87535d811a785431e0bf662d981635`
- category: knowledge

```markdown
# Systemd

systemd, services, boot flow, timers/cron, and package/service lifecycle actions.

## Modules

- `systemd/boot-i-grub.md`: 29 imported commands from `Boot i GRUB`
- `systemd/cron-i-harmonogramowanie-zada.md`: 21 imported commands from `Cron i harmonogramowanie zada■`
- `systemd/systemd-i-zarzdzanie-usugami.md`: 54 imported commands from `Systemd i zarz■dzanie us■ugami`
- `systemd/zarzdzanie-pakietami-dnf-rpm.md`: 70 imported commands from `Zarz■dzanie pakietami (DNF/RPM)`

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
```

## `runtime/knowledge/systemd/boot-i-grub.md`

- size: 9827 bytes
- sha256: `cf875b0cd42f80c340ca9d661dbaee281a71e584a0108a63d8c2824ab33f2ceb`
- category: knowledge

```markdown
---
title: Boot i GRUB
topic: systemd
source_section: Boot i GRUB
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [boot-i-grub, cat, dnf, echo, grub, grub2-install, grub2-set-default, halt, insmod, kernel, linux, ls, lsmod, poweroff, reboot, rhcsa, rpm, sync, sysctl, systemctl, systemd]
---

# Boot i GRUB

Imported RHCSA material for 29 commands. Primary command families: cat, dnf, echo, grub, grub2-install, grub2-set-default, halt, insmod.

## Tags

boot-i-grub, cat, dnf, echo, grub, grub2-install, grub2-set-default, halt, insmod, kernel, linux, ls, lsmod, poweroff, reboot, rhcsa, rpm, sync, sysctl, systemctl, systemd

## Examples

- `/boot/grub2/grub.cfg`
- `cat /etc/sysctl.conf`
- `grub2-install`
- `cat /etc/sysctl.d/`
- `echo 'net.ipv4.ip_fo`
- `--target=x86_64-efi`
- `grub2-set-default`
- `GRUB`
- `lsmod`
- `ls /boot/grub2/`

## Troubleshooting

- If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Boot i GRUB`

## Commands

### `/boot/grub2/grub.cfg`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `boot-grub2-grub-cfg`
- Examples:
  - `/boot/grub2/grub.cfg`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `cat /etc/sysctl.conf`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `cat`
- Examples:
  - `cat /etc/sysctl.conf`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `grub2-install`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `grub2-install`
- Examples:
  - `grub2-install`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `cat /etc/sysctl.d/`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `cat`
- Examples:
  - `cat /etc/sysctl.d/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `echo 'net.ipv4.ip_fo`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `echo`
- Examples:
  - `echo 'net.ipv4.ip_fo`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `--target=x86_64-efi`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `target-x86-64-efi`
- Examples:
  - `--target=x86_64-efi`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `grub2-set-default`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `grub2-set-default`
- Examples:
  - `grub2-set-default`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `GRUB`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `grub`
- Examples:
  - `GRUB`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `lsmod`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `lsmod`
- Examples:
  - `lsmod`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `ls /boot/grub2/`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `ls`
- Examples:
  - `ls /boot/grub2/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `ls /boot/`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `ls`
- Examples:
  - `ls /boot/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `insmod`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `insmod`
- Examples:
  - `insmod`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `/boot/initramfs*`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `boot-initramfs`
- Examples:
  - `/boot/initramfs*`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `echo 'module_name' >`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `echo`
- Examples:
  - `echo 'module_name' >`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `cat /etc/modprobe.d/`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `cat`
- Examples:
  - `cat /etc/modprobe.d/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `rpm -qa kernel`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `rpm`
- Examples:
  - `rpm -qa kernel`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `kernel`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `kernel`
- Examples:
  - `kernel`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `dnf install kernel`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf install kernel`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `systemctl rescue`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl rescue`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `dnf remove`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf remove`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `systemctl emergency`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl emergency`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `cat /proc/cmdline`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `cat`
- Examples:
  - `cat /proc/cmdline`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `cat /proc/version`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `cat`
- Examples:
  - `cat /proc/version`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `cat /proc/sys/kernel`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `cat`
- Examples:
  - `cat /proc/sys/kernel`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `reboot`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `reboot`
- Examples:
  - `reboot`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `poweroff`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `poweroff`
- Examples:
  - `poweroff`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `halt`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `halt`
- Examples:
  - `halt`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `sysctl`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `sysctl`
- Examples:
  - `sysctl`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`

### `sync`

- Category: `Boot i GRUB`
- Risk: `unclassified`
- Tags: `systemd`, `sync`
- Examples:
  - `sync`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Boot i GRUB`
```

## `runtime/knowledge/systemd/cron-i-harmonogramowanie-zada.md`

- size: 8417 bytes
- sha256: `f4bbb4d0e10d95f42772864ce1d8c846d495d6587203c819baf80f896c94fe7d`
- category: knowledge

```markdown
---
title: Cron i harmonogramowanie zada■
topic: systemd
source_section: Cron i harmonogramowanie zada■
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [atq, batch, cat, cron-i-harmonogramowanie-zada, linux, list-timers, ls, myapp.timer, rhcsa, run-parts, systemd, systemd-run, timer-name.timer]
---

# Cron i harmonogramowanie zada■

Imported RHCSA material for 21 commands. Primary command families: atq, batch, cat, list-timers, ls, myapp.timer, run-parts, systemd-run.

## Tags

atq, batch, cat, cron-i-harmonogramowanie-zada, linux, list-timers, ls, myapp.timer, rhcsa, run-parts, systemd, systemd-run, timer-name.timer

## Examples

- `systemd-run`
- `cat /etc/crontab`
- `atq`
- `ls /etc/cron.d/`
- `ls /etc/cron.daily/`
- `ls /etc/cron.weekly/`
- `batch`
- `ls /etc/cron.hourly/`
- `cat /etc/at.allow`
- `cat /var/spool/cron/`

## Troubleshooting

- Validate command intent against current host state before applying changes in production.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Cron i harmonogramowanie zada■`

## Commands

### `systemd-run`

- Category: `Cron i harmonogramowanie zada■`
- Risk: `unclassified`
- Tags: `systemd`, `systemd-run`
- Examples:
  - `systemd-run`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Cron i harmonogramowanie zada■`

### `cat /etc/crontab`

- Category: `Cron i harmonogramowanie zada■`
- Risk: `unclassified`
- Tags: `systemd`, `cat`
- Examples:
  - `cat /etc/crontab`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Cron i harmonogramowanie zada■`

### `atq`

- Category: `Cron i harmonogramowanie zada■`
- Risk: `unclassified`
- Tags: `systemd`, `atq`
- Examples:
  - `atq`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Cron i harmonogramowanie zada■`

### `ls /etc/cron.d/`

- Category: `Cron i harmonogramowanie zada■`
- Risk: `unclassified`
- Tags: `systemd`, `ls`
- Examples:
  - `ls /etc/cron.d/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Cron i harmonogramowanie zada■`

### `ls /etc/cron.daily/`

- Category: `Cron i harmonogramowanie zada■`
- Risk: `unclassified`
- Tags: `systemd`, `ls`
- Examples:
  - `ls /etc/cron.daily/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Cron i harmonogramowanie zada■`

### `ls /etc/cron.weekly/`

- Category: `Cron i harmonogramowanie zada■`
- Risk: `unclassified`
- Tags: `systemd`, `ls`
- Examples:
  - `ls /etc/cron.weekly/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Cron i harmonogramowanie zada■`

### `batch`

- Category: `Cron i harmonogramowanie zada■`
- Risk: `unclassified`
- Tags: `systemd`, `batch`
- Examples:
  - `batch`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Cron i harmonogramowanie zada■`

### `ls /etc/cron.hourly/`

- Category: `Cron i harmonogramowanie zada■`
- Risk: `unclassified`
- Tags: `systemd`, `ls`
- Examples:
  - `ls /etc/cron.hourly/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Cron i harmonogramowanie zada■`

### `cat /etc/at.allow`

- Category: `Cron i harmonogramowanie zada■`
- Risk: `unclassified`
- Tags: `systemd`, `cat`
- Examples:
  - `cat /etc/at.allow`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Cron i harmonogramowanie zada■`

### `cat /var/spool/cron/`

- Category: `Cron i harmonogramowanie zada■`
- Risk: `unclassified`
- Tags: `systemd`, `cat`
- Examples:
  - `cat /var/spool/cron/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Cron i harmonogramowanie zada■`

### `cat /etc/at.deny`

- Category: `Cron i harmonogramowanie zada■`
- Risk: `unclassified`
- Tags: `systemd`, `cat`
- Examples:
  - `cat /etc/at.deny`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Cron i harmonogramowanie zada■`

### `cat /etc/cron.allow`

- Category: `Cron i harmonogramowanie zada■`
- Risk: `unclassified`
- Tags: `systemd`, `cat`
- Examples:
  - `cat /etc/cron.allow`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Cron i harmonogramowanie zada■`

### `cat /etc/cron.deny`

- Category: `Cron i harmonogramowanie zada■`
- Risk: `unclassified`
- Tags: `systemd`, `cat`
- Examples:
  - `cat /etc/cron.deny`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Cron i harmonogramowanie zada■`

### `run-parts`

- Category: `Cron i harmonogramowanie zada■`
- Risk: `unclassified`
- Tags: `systemd`, `run-parts`
- Examples:
  - `run-parts`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Cron i harmonogramowanie zada■`

### `/etc/cron.daily`

- Category: `Cron i harmonogramowanie zada■`
- Risk: `unclassified`
- Tags: `systemd`, `etc-cron-daily`
- Examples:
  - `/etc/cron.daily`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Cron i harmonogramowanie zada■`

### `cat /etc/anacrontab`

- Category: `Cron i harmonogramowanie zada■`
- Risk: `unclassified`
- Tags: `systemd`, `cat`
- Examples:
  - `cat /etc/anacrontab`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Cron i harmonogramowanie zada■`

### `list-timers`

- Category: `Cron i harmonogramowanie zada■`
- Risk: `unclassified`
- Tags: `systemd`, `list-timers`
- Examples:
  - `list-timers`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Cron i harmonogramowanie zada■`

### `timer-name.timer`

- Category: `Cron i harmonogramowanie zada■`
- Risk: `unclassified`
- Tags: `systemd`, `timer-name.timer`
- Examples:
  - `timer-name.timer`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Cron i harmonogramowanie zada■`

### `myapp.timer`

- Category: `Cron i harmonogramowanie zada■`
- Risk: `unclassified`
- Tags: `systemd`, `myapp.timer`
- Examples:
  - `myapp.timer`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Cron i harmonogramowanie zada■`

### `cat /etc/systemd/sys`

- Category: `Cron i harmonogramowanie zada■`
- Risk: `unclassified`
- Tags: `systemd`, `cat`
- Examples:
  - `cat /etc/systemd/sys`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Cron i harmonogramowanie zada■`

### `tem/myapp.timer`

- Category: `Cron i harmonogramowanie zada■`
- Risk: `unclassified`
- Tags: `systemd`, `tem-myapp-timer`
- Examples:
  - `tem/myapp.timer`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Cron i harmonogramowanie zada■`
```

## `runtime/knowledge/systemd/systemd-i-zarzdzanie-usugami.md`

- size: 20275 bytes
- sha256: `a168c358e68695f79003d8531d35470237c96f101f5707abc03d831748e5b907`
- category: knowledge

```markdown
---
title: Systemd i zarz■dzanie us■ugami
topic: systemd
source_section: Systemd i zarz■dzanie us■ugami
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [daemon-reexec, daemon-reload, emergency.target, get-default, hostnamectl, journalctl, linux, list-dependencies, list-unit-files, localectl, loginctl, rescue.target, rhcsa, service, set-default, systemctl, systemd, systemd-analyze, systemd-i-zarzdzanie-usugami, timedatectl]
---

# Systemd i zarz■dzanie us■ugami

Imported RHCSA material for 54 commands. Primary command families: daemon-reexec, daemon-reload, emergency.target, get-default, hostnamectl, journalctl, list-dependencies, list-unit-files.

## Tags

daemon-reexec, daemon-reload, emergency.target, get-default, hostnamectl, journalctl, linux, list-dependencies, list-unit-files, localectl, loginctl, rescue.target, rhcsa, service, set-default, systemctl, systemd, systemd-analyze, systemd-i-zarzdzanie-usugami, timedatectl

## Examples

- `systemctl status`
- `systemctl show`
- `service`
- `systemctl start`
- `systemctl show -p`
- `systemctl stop`
- `systemd-analyze`
- `systemctl restart`
- `systemctl reload`
- `systemctl enable`

## Troubleshooting

- If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Use time or unit filters first to keep logs readable on low-RAM systems.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Systemd i zarz■dzanie us■ugami`

## Commands

### `systemctl status`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl status`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl show`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl show`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `service`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `service`
- Examples:
  - `service`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl start`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl start`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl show -p`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl show -p`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl stop`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl stop`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemd-analyze`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemd-analyze`
- Examples:
  - `systemd-analyze`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl restart`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl restart`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl reload`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl reload`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl enable`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl enable`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl disable`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl disable`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `journalctl`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `journalctl`
- Examples:
  - `journalctl`
- Troubleshooting hint:
  - Use time or unit filters first to keep logs readable on low-RAM systems.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `journalctl -u`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `journalctl`
- Examples:
  - `journalctl -u`
- Troubleshooting hint:
  - Use time or unit filters first to keep logs readable on low-RAM systems.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `journalctl -f`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `journalctl`
- Examples:
  - `journalctl -f`
- Troubleshooting hint:
  - Use time or unit filters first to keep logs readable on low-RAM systems.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl is-active`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl is-active`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `journalctl -f -u`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `journalctl`
- Examples:
  - `journalctl -f -u`
- Troubleshooting hint:
  - Use time or unit filters first to keep logs readable on low-RAM systems.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl is-enabled`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl is-enabled`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `journalctl -n 50`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `journalctl`
- Examples:
  - `journalctl -n 50`
- Troubleshooting hint:
  - Use time or unit filters first to keep logs readable on low-RAM systems.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl is-failed`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl is-failed`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `journalctl --since`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `journalctl`
- Examples:
  - `journalctl --since`
- Troubleshooting hint:
  - Use time or unit filters first to keep logs readable on low-RAM systems.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl list-units`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl list-units`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `journalctl --until`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `journalctl`
- Examples:
  - `journalctl --until`
- Troubleshooting hint:
  - Use time or unit filters first to keep logs readable on low-RAM systems.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `--type=service`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `type-service`
- Examples:
  - `--type=service`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `journalctl -p err`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `journalctl`
- Examples:
  - `journalctl -p err`
- Troubleshooting hint:
  - Use time or unit filters first to keep logs readable on low-RAM systems.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `journalctl -p`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `journalctl`
- Examples:
  - `journalctl -p`
- Troubleshooting hint:
  - Use time or unit filters first to keep logs readable on low-RAM systems.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `list-unit-files`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `list-unit-files`
- Examples:
  - `list-unit-files`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `journalctl -b`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `journalctl`
- Examples:
  - `journalctl -b`
- Troubleshooting hint:
  - Use time or unit filters first to keep logs readable on low-RAM systems.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `journalctl -b -1`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `journalctl`
- Examples:
  - `journalctl -b -1`
- Troubleshooting hint:
  - Use time or unit filters first to keep logs readable on low-RAM systems.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `list-dependencies`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `list-dependencies`
- Examples:
  - `list-dependencies`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl mask`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl mask`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `journalctl -k`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `journalctl`
- Examples:
  - `journalctl -k`
- Troubleshooting hint:
  - Use time or unit filters first to keep logs readable on low-RAM systems.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl unmask`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl unmask`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `journalctl -o json`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `journalctl`
- Examples:
  - `journalctl -o json`
- Troubleshooting hint:
  - Use time or unit filters first to keep logs readable on low-RAM systems.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `daemon-reload`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `daemon-reload`
- Examples:
  - `daemon-reload`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `daemon-reexec`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `daemon-reexec`
- Examples:
  - `daemon-reexec`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `--vacuum-size=500M`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `vacuum-size-500m`
- Examples:
  - `--vacuum-size=500M`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `get-default`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `get-default`
- Examples:
  - `get-default`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl --user`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl --user`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `set-default`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `set-default`
- Examples:
  - `set-default`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `loginctl`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `loginctl`
- Examples:
  - `loginctl`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl isolate`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl isolate`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `rescue.target`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `rescue.target`
- Examples:
  - `rescue.target`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `emergency.target`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `emergency.target`
- Examples:
  - `emergency.target`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `hostnamectl`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `hostnamectl`
- Examples:
  - `hostnamectl`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl poweroff`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl poweroff`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl reboot`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl reboot`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `timedatectl`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `timedatectl`
- Examples:
  - `timedatectl`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl halt`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl halt`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl suspend`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl suspend`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl hibernate`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl hibernate`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl cat`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl cat`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `localectl`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `localectl`
- Examples:
  - `localectl`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`

### `systemctl edit`

- Category: `Systemd i zarz■dzanie us■ugami`
- Risk: `unclassified`
- Tags: `systemd`, `systemctl`
- Examples:
  - `systemctl edit`
- Troubleshooting hint:
  - If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.
- Provenance:
  - RHCSA section: `Systemd i zarz■dzanie us■ugami`
```

## `runtime/knowledge/systemd/zarzdzanie-pakietami-dnf-rpm.md`

- size: 25165 bytes
- sha256: `6adcd793530a2a432ab7f90c80ee099ee814d382f17367cc1b2d90e233643ba4`
- category: knowledge

```markdown
---
title: Zarz■dzanie pakietami (DNF/RPM)
topic: systemd
source_section: Zarz■dzanie pakietami (DNF/RPM)
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [aktualizacjami, dnf, linux, package, rhcsa, rpm, subscription-manager, systemd, zarzdzanie-pakietami-dnf-rpm]
---

# Zarz■dzanie pakietami (DNF/RPM)

Imported RHCSA material for 70 commands. Primary command families: aktualizacjami, dnf, package, rpm, subscription-manager.

## Tags

aktualizacjami, dnf, linux, package, rhcsa, rpm, subscription-manager, systemd, zarzdzanie-pakietami-dnf-rpm

## Examples

- `dnf install package`
- `dnf check-update`
- `dnf install -y`
- `dnf security update`
- `package`
- `dnf remove package`
- `dnf updateinfo list`
- `dnf erase package`
- `dnf update`
- `dnf distro-sync`

## Troubleshooting

- Check interface state, service state, and firewall exposure together during network diagnostics.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Zarz■dzanie pakietami (DNF/RPM)`

## Commands

### `dnf install package`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf install package`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf check-update`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf check-update`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf install -y`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf install -y`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf security update`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf security update`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `package`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `package`
- Examples:
  - `package`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf remove package`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf remove package`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf updateinfo list`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf updateinfo list`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf erase package`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf erase package`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf update`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf update`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf distro-sync`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf distro-sync`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf update package`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf update package`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf module list`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf module list`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf upgrade`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf upgrade`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf module enable`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf module enable`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf upgrade-minimal`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf upgrade-minimal`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf module disable`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf module disable`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf downgrade`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf downgrade`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf module install m`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf module install m`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf reinstall`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf reinstall`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf module reset`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf module reset`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf autoremove`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf autoremove`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf module info`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf module info`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf clean all`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf clean all`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `rpm -qa`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `rpm`
- Examples:
  - `rpm -qa`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf clean packages`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf clean packages`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `rpm -qi package`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `rpm`
- Examples:
  - `rpm -qi package`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf clean metadata`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf clean metadata`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `rpm -ql package`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `rpm`
- Examples:
  - `rpm -ql package`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf makecache`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf makecache`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `rpm -qd package`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `rpm`
- Examples:
  - `rpm -qd package`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf search keyword`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf search keyword`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `rpm -qc package`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `rpm`
- Examples:
  - `rpm -qc package`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf info package`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf info package`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `rpm -qf`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `rpm`
- Examples:
  - `rpm -qf`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf list installed`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf list installed`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `rpm -qR package`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `rpm`
- Examples:
  - `rpm -qR package`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf list available`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf list available`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `rpm -q --scripts`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `rpm`
- Examples:
  - `rpm -q --scripts`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf list updates`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf list updates`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `rpm -q --changelog`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `rpm`
- Examples:
  - `rpm -q --changelog`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `aktualizacjami`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `aktualizacjami`
- Examples:
  - `aktualizacjami`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf list extras`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf list extras`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `rpm -ivh package.rpm`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `rpm`
- Examples:
  - `rpm -ivh package.rpm`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf list obsoletes`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf list obsoletes`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `rpm -Uvh package.rpm`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `rpm`
- Examples:
  - `rpm -Uvh package.rpm`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf provides`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf provides`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `rpm -Fvh package.rpm`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `rpm`
- Examples:
  - `rpm -Fvh package.rpm`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `rpm -e package`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `rpm`
- Examples:
  - `rpm -e package`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf whatprovides`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf whatprovides`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `rpm -V package`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `rpm`
- Examples:
  - `rpm -V package`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf repolist`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf repolist`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `rpm -Va`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `rpm`
- Examples:
  - `rpm -Va`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf repolist all`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf repolist all`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `rpm --import`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `rpm`
- Examples:
  - `rpm --import`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `rpm -K package.rpm`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `rpm`
- Examples:
  - `rpm -K package.rpm`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf repoinfo repo-id`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf repoinfo repo-id`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf config-manager`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf config-manager`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `rpm -qp --scripts`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `rpm`
- Examples:
  - `rpm -qp --scripts`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `rpm -qip package.rpm`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `rpm`
- Examples:
  - `rpm -qip package.rpm`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf grouplist`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf grouplist`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `subscription-manager`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `subscription-manager`
- Examples:
  - `subscription-manager`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf groupinstall`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf groupinstall`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf groupremove`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf groupremove`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf groupinfo 'Group`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf groupinfo 'Group`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `Name'`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `name`
- Examples:
  - `Name'`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf history`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf history`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf history info 5`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf history info 5`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf history undo 5`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf history undo 5`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf history redo 5`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf history redo 5`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`

### `dnf history rollback`

- Category: `Zarz■dzanie pakietami (DNF/RPM)`
- Risk: `unclassified`
- Tags: `systemd`, `dnf`
- Examples:
  - `dnf history rollback`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie pakietami (DNF/RPM)`
```

## `runtime/knowledge/tools/CANONICAL_BUILDER_README.md`

- size: 1274 bytes
- sha256: `26a7397b2a2ba425b49af4787183cc0ed1c6474f2a227d4a242faf9cf66edab6`
- category: knowledge

```markdown
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
```

## `runtime/knowledge/tools/CONTEXT_PACK_README.md`

- size: 1279 bytes
- sha256: `aacc55273625a3baca980426a834a8e1eaf7fad9102d6221a32e12a13c3ccd49`
- category: knowledge

```markdown
# RHCSA Context Pack Builder

`context_pack_builder.py` creates static context packs from the deterministic
RHCSA command index and canonical command entries.

## Deterministic Context Philosophy

Context packs are generated by exact keyword lookup only. Query text is split
into deterministic tokens, tokens are matched against `command_index.json`, and
matching command details are copied from `rhcsa_commands.json`.

## Lookup vs AI Reasoning

Lookup returns commands connected to exact indexed tokens. It does not infer
meaning, expand synonyms, score relevance, summarize results, or reason about a
user request. AI reasoning is outside this phase.

## Static Context Injection Boundary

The output file is a static JSON artifact. It can be reviewed before any future
runtime integration. This builder does not inject context into the app, router,
providers, or prompts.

## What It Does Not Do

- does not implement semantic search
- does not use embeddings
- does not use vector databases
- does not rank results
- does not generate summaries
- does not modify router or runtime code

## Usage

Default static query:

```text
python3 knowledge/tools/context_pack_builder.py
```

Explicit query:

```text
python3 knowledge/tools/context_pack_builder.py "network ports"
```
```

## `runtime/knowledge/tools/INDEX_BUILDER_README.md`

- size: 1090 bytes
- sha256: `3e4481d439c3192634d8ce63a162c0d85baeac2c222cebe8754c747eda2c0d36`
- category: knowledge

```markdown
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
```

## `runtime/knowledge/tools/INJECTION_LAYER_README.md`

- size: 1142 bytes
- sha256: `f5695bb07f06bcb800487fb1c06a383cddb2412e9d3cf3eb08016b92da73fc38`
- category: knowledge

```markdown
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
```

## `runtime/knowledge/tools/README.md`

- size: 1165 bytes
- sha256: `fe489096261209a2a4ac1bd99a8c6c5c7ba8b4c520d964e87a354c16cc7599c2`
- category: knowledge

```markdown
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
```

## `runtime/knowledge/tools/SECTION_PARSER_README.md`

- size: 1187 bytes
- sha256: `af990c3f853e9839f97eaa2ee234e6b41b62b8f797f450c4206db4ff9ef40a68`
- category: knowledge

```markdown
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
```

## `runtime/knowledge/tools/candidate_index_loader.py`

- size: 17798 bytes
- sha256: `83b405b745f2894b27cc50fff5ed1284210d7033e4a294c13d9f715b0ac5bd5f`
- category: knowledge

```python
#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter, OrderedDict, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_ROOT = PROJECT_ROOT / "knowledge"
SOURCE_TEXT = KNOWLEDGE_ROOT / "extracted" / "linux_master_library_v1.txt"
CANONICAL_JSON = KNOWLEDGE_ROOT / "canonical" / "rhcsa_commands.json"
COMMAND_INDEX_JSON = KNOWLEDGE_ROOT / "index" / "command_index.json"
CANDIDATES_DIR = KNOWLEDGE_ROOT / "candidates"
REPORTS_DIR = KNOWLEDGE_ROOT / "reports"
CANDIDATE_JSON = CANDIDATES_DIR / "candidate_command_index.json"
CANDIDATE_CSV = CANDIDATES_DIR / "candidate_commands.csv"
DEDUP_REPORT = REPORTS_DIR / "deduplication_report.md"
QUALITY_REPORT = REPORTS_DIR / "parsing_quality_report.md"
CATEGORY_REPORT = REPORTS_DIR / "category_distribution.md"

CANONICAL_SOURCE = "runtime/knowledge/source/linux_master_library_v1.pdf"
ENTRY_RE = re.compile(r"^\s*(1\.(?:[4-9]|1[0-8])\.(\d+))\s+(.+?)\s*$")
SECTION_RE = re.compile(r"^\s*1\.(?:[4-9]|1[0-8])\s+([A-Z][A-Za-z &/]+)\s*$")
TOC_RE = re.compile(r"^\s*(1\.(?:[4-9]|1[0-8])\.(\d+))\s+(.+?)\s+(?:(?:\.\s*){3,})\s+(\d+)\s*$")

SECTION_BY_NUMBER = {
    "1.4": "File Management",
    "1.5": "Users & Permissions",
    "1.6": "Networking",
    "1.7": "Storage",
    "1.8": "Systemd",
    "1.9": "Processes",
    "1.10": "Bash",
    "1.11": "SSH",
    "1.12": "Logs",
    "1.13": "Security",
    "1.14": "Packages",
    "1.15": "Automation",
    "1.16": "RHCSA Exam Tasks",
    "1.17": "Sources",
    "1.18": "Gemini Expansion Additions",
}

NOISE_PHRASES = {
    "aoia",
    "do not",
    "kernel logic",
    "memory.py",
    "planner systems",
    "runtime",
    "without symlink",
    "bypassing",
    "when $var unset",
}


@dataclass(frozen=True)
class CandidateRecord:
    command: str
    command_key: str
    base_command: str
    category: str
    description: str
    examples: list[str]
    source_line: int
    source_page: int | None
    canonical_source: str
    source_files: list[str]
    status: str
    duplicate_type: str
    duplicate_of: str
    quality_flags: list[str]
    confidence: str


def normalize_text(value: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    return re.sub(r"[^a-z0-9_+./$|<>*;:=-]+", " ", normalized).strip()


def normalize_command(value: str) -> str:
    value = value.replace("‘", "'").replace("’", "'").replace("`", "")
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"\s+\d+$", "", value).strip()
    return value


def command_key(command: str) -> str:
    command = normalize_command(command)
    if " " not in command:
        return command.lower()
    base, rest = command.split(" ", 1)
    return f"{base.lower()} {rest}"


def base_command(command: str) -> str:
    command = normalize_command(command)
    command = re.sub(r"^(sudo|time|watch|timeout)\s+", "", command)
    return command.split(" ", 1)[0].lower() if command else ""


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def load_existing_sets() -> tuple[set[str], set[str]]:
    canonical_payload = read_json(CANONICAL_JSON, [])
    canonical_keys: set[str] = set()
    if isinstance(canonical_payload, list):
        for item in canonical_payload:
            if isinstance(item, dict) and item.get("command"):
                canonical_keys.add(command_key(str(item["command"])))

    command_index_payload = read_json(COMMAND_INDEX_JSON, {})
    index_keys: set[str] = set()
    if isinstance(command_index_payload, dict):
        for key, values in command_index_payload.items():
            index_keys.add(command_key(str(key)))
            if isinstance(values, list):
                for value in values:
                    index_keys.add(command_key(str(value)))
    return canonical_keys, index_keys


def parse_toc_pages(lines: list[str]) -> dict[str, int]:
    pages: dict[str, int] = {}
    for line in lines:
        if line.strip().startswith("1       FINAL MASTER"):
            break
        match = TOC_RE.match(line.replace("\f", ""))
        if match:
            pages[match.group(1)] = int(match.group(4))
    return pages


def section_for_entry(entry_id: str, fallback: str) -> str:
    prefix = ".".join(entry_id.split(".")[:2])
    return SECTION_BY_NUMBER.get(prefix, fallback or "Unclassified")


def strip_toc_dots(text: str) -> str:
    text = re.sub(r"\s+\.{3,}.*$", "", text).strip()
    return normalize_command(text)


def is_source_line(line: str) -> bool:
    return line.strip().startswith("Sources:")


def parse_sources(line: str) -> list[str]:
    raw = line.split(":", 1)[1] if ":" in line else ""
    return [item.strip() for item in raw.split(",") if item.strip()]


def is_probable_example(line: str, command: str) -> bool:
    text = line.strip()
    if not text or text.startswith("Sources:"):
        return False
    if text.startswith("•") or re.match(r"^\d+(\.\d+)*\s", text):
        return False
    if len(text) > 180:
        return False
    first = text.split()[0] if text.split() else ""
    return first == base_command(command) or text == command


def quality_flags(command: str, description: str) -> list[str]:
    flags: list[str] = []
    normalized = normalize_text(command)
    base = base_command(command)
    if not command:
        flags.append("empty_command")
    if not base or not re.match(r"^[a-z0-9_.$/{[(+-][a-z0-9_.$/{[(+-]*$", base):
        flags.append("invalid_base_command")
    if len(command) > 120:
        flags.append("too_long")
    if any(phrase in normalized for phrase in NOISE_PHRASES):
        flags.append("likely_contamination_or_comment")
    if command.count("|") > 2 or command.count(";") > 2:
        flags.append("complex_pipeline_or_snippet")
    if command.startswith(("/", "~")):
        flags.append("path_not_command")
    if description.lower() in {"sekcja komend", "dangerous mistakes"}:
        flags.append("weak_description")
    if re.search(r"\b(file|regularnego|kadej|grup|planner|logic)\b", normalized) and base in {"file", "touch", "type"}:
        flags.append("probable_pdf_merge_artifact")
    return list(dict.fromkeys(flags))


def confidence_for(flags: list[str], duplicate_type: str) -> str:
    severe = {"empty_command", "invalid_base_command", "path_not_command", "too_long"}
    if severe.intersection(flags):
        return "none"
    if "likely_contamination_or_comment" in flags or "probable_pdf_merge_artifact" in flags:
        return "low"
    if duplicate_type:
        return "high"
    if "weak_description" in flags or "complex_pipeline_or_snippet" in flags:
        return "medium"
    return "high"


def status_for(flags: list[str], duplicate_type: str) -> str:
    severe = {"empty_command", "invalid_base_command", "path_not_command", "too_long"}
    if severe.intersection(flags):
        return "malformed"
    if "likely_contamination_or_comment" in flags or "probable_pdf_merge_artifact" in flags:
        return "unresolved"
    if duplicate_type:
        return "duplicate_existing"
    return "candidate"


def parse_entries(lines: list[str], page_by_entry: dict[str, int]) -> list[dict[str, Any]]:
    body_start = 0
    for index, line in enumerate(lines):
        if line.strip().startswith("1       FINAL MASTER"):
            body_start = index
            break

    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    current_category = ""

    def flush() -> None:
        nonlocal current
        if current is not None:
            entries.append(current)
            current = None

    for source_line, raw in enumerate(lines[body_start:], start=body_start + 1):
        line = raw.replace("\f", "").rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        section_match = SECTION_RE.match(stripped)
        if section_match:
            current_category = section_match.group(1).strip()
            continue
        match = ENTRY_RE.match(stripped)
        if match:
            entry_id = match.group(1)
            command = strip_toc_dots(match.group(3))
            if command in SECTION_BY_NUMBER.values():
                continue
            flush()
            current = {
                "entry_id": entry_id,
                "command": command,
                "category": section_for_entry(entry_id, current_category),
                "description_lines": [],
                "examples": [],
                "sources": [],
                "source_line": source_line,
                "source_page": page_by_entry.get(entry_id),
            }
            continue
        if current is None:
            continue
        if is_source_line(stripped):
            current["sources"].extend(parse_sources(stripped))
            continue
        if is_probable_example(stripped, current["command"]):
            current["examples"].append(stripped)
        elif len(current["description_lines"]) < 3:
            current["description_lines"].append(stripped)

    flush()
    return entries


def build_candidates(raw_entries: list[dict[str, Any]], canonical_keys: set[str], index_keys: set[str]) -> list[CandidateRecord]:
    seen: OrderedDict[str, int] = OrderedDict()
    records: list[CandidateRecord] = []
    for entry in raw_entries:
        command = normalize_command(str(entry["command"]))
        key = command_key(command)
        base = base_command(command)
        duplicate_types: list[str] = []
        duplicate_of = ""
        if key in canonical_keys:
            duplicate_types.append("canonical")
            duplicate_of = command
        if key in index_keys:
            duplicate_types.append("command_index")
            duplicate_of = duplicate_of or command
        if key in seen:
            duplicate_types.append("candidate_internal")
            duplicate_of = duplicate_of or records[seen[key]].command

        description = " ".join(str(item).strip() for item in entry["description_lines"] if str(item).strip())
        flags = quality_flags(command, description)
        duplicate_type = "+".join(duplicate_types)
        status = status_for(flags, duplicate_type)
        confidence = confidence_for(flags, duplicate_type)

        record = CandidateRecord(
            command=command,
            command_key=key,
            base_command=base,
            category=str(entry["category"]),
            description=description,
            examples=list(dict.fromkeys(entry["examples"])),
            source_line=int(entry["source_line"]),
            source_page=entry["source_page"],
            canonical_source=CANONICAL_SOURCE,
            source_files=list(dict.fromkeys(entry["sources"])),
            status=status,
            duplicate_type=duplicate_type,
            duplicate_of=duplicate_of,
            quality_flags=flags,
            confidence=confidence,
        )
        if key not in seen:
            seen[key] = len(records)
        records.append(record)
    return records


def write_json(records: list[CandidateRecord], stats: dict[str, Any]) -> None:
    payload = {
        "schema_version": "1.0",
        "source": str(SOURCE_TEXT.relative_to(PROJECT_ROOT)),
        "canonical_source": CANONICAL_SOURCE,
        "promotion_status": "candidates_only",
        "stats": stats,
        "records": [asdict(record) for record in records],
    }
    CANDIDATE_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(records: list[CandidateRecord]) -> None:
    with CANDIDATE_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "command",
            "command_key",
            "base_command",
            "category",
            "description",
            "examples",
            "source_line",
            "source_page",
            "canonical_source",
            "source_files",
            "status",
            "duplicate_type",
            "duplicate_of",
            "quality_flags",
            "confidence",
        ])
        for record in records:
            writer.writerow([
                record.command,
                record.command_key,
                record.base_command,
                record.category,
                record.description,
                " | ".join(record.examples),
                record.source_line,
                record.source_page or "",
                record.canonical_source,
                " | ".join(record.source_files),
                record.status,
                record.duplicate_type,
                record.duplicate_of,
                " | ".join(record.quality_flags),
                record.confidence,
            ])


def stats_for(records: list[CandidateRecord], raw_entries: list[dict[str, Any]]) -> dict[str, Any]:
    unique_keys = {record.command_key for record in records}
    duplicates_existing = [record for record in records if "canonical" in record.duplicate_type or "command_index" in record.duplicate_type]
    malformed = [record for record in records if record.status in {"malformed", "unresolved"}]
    return {
        "total_parsed_entries": len(raw_entries),
        "total_candidate_records": len(records),
        "total_unique_candidate_commands": len(unique_keys),
        "duplicates_against_existing": len(duplicates_existing),
        "malformed_unresolved_entries": len(malformed),
        "candidate_only_entries": sum(1 for record in records if record.status == "candidate"),
        "internal_candidate_duplicates": sum(1 for record in records if "candidate_internal" in record.duplicate_type),
    }


def write_reports(records: list[CandidateRecord], stats: dict[str, Any]) -> None:
    category_counts = Counter(record.category for record in records)
    status_counts = Counter(record.status for record in records)
    duplicate_counts = Counter(record.duplicate_type or "new_candidate" for record in records)
    flag_counts = Counter(flag for record in records for flag in record.quality_flags)

    DEDUP_REPORT.write_text(
        "\n".join([
            "# Candidate Deduplication Report",
            "",
            f"- Total parsed entries: {stats['total_parsed_entries']}",
            f"- Total unique candidate commands: {stats['total_unique_candidate_commands']}",
            f"- Duplicates against existing canonical/index: {stats['duplicates_against_existing']}",
            f"- Internal candidate duplicates: {stats['internal_candidate_duplicates']}",
            "",
            "## Duplicate Type Counts",
            "",
            *[f"- {key}: {value}" for key, value in sorted(duplicate_counts.items())],
            "",
            "## Sample Existing Duplicates",
            "",
            *[
                f"- `{record.command}` -> {record.duplicate_type}"
                for record in records
                if record.status == "duplicate_existing"
            ][:50],
            "",
            "Canonical runtime files were not modified.",
        ]) + "\n",
        encoding="utf-8",
    )

    QUALITY_REPORT.write_text(
        "\n".join([
            "# Candidate Parsing Quality Report",
            "",
            f"- Total parsed entries: {stats['total_parsed_entries']}",
            f"- Candidate records written: {stats['total_candidate_records']}",
            f"- Malformed or unresolved entries: {stats['malformed_unresolved_entries']}",
            "",
            "## Status Counts",
            "",
            *[f"- {key}: {value}" for key, value in sorted(status_counts.items())],
            "",
            "## Quality Flag Counts",
            "",
            *([f"- {key}: {value}" for key, value in sorted(flag_counts.items())] or ["- none: 0"]),
            "",
            "## Sample Malformed/Unresolved Entries",
            "",
            *[
                f"- line {record.source_line}: `{record.command}` ({', '.join(record.quality_flags)})"
                for record in records
                if record.status in {"malformed", "unresolved"}
            ][:80],
            "",
            "No command rows were promoted to canonical indexes.",
        ]) + "\n",
        encoding="utf-8",
    )

    CATEGORY_REPORT.write_text(
        "\n".join([
            "# Candidate Category Distribution",
            "",
            *[f"- {category}: {count}" for category, count in sorted(category_counts.items())],
            "",
            "## By Status",
            "",
            *[f"- {status}: {count}" for status, count in sorted(status_counts.items())],
        ]) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    lines = SOURCE_TEXT.read_text(encoding="utf-8", errors="replace").splitlines()
    canonical_keys, index_keys = load_existing_sets()
    page_by_entry = parse_toc_pages(lines)
    raw_entries = parse_entries(lines, page_by_entry)
    records = build_candidates(raw_entries, canonical_keys, index_keys)
    stats = stats_for(records, raw_entries)
    write_json(records, stats)
    write_csv(records)
    write_reports(records, stats)
    for key, value in stats.items():
        print(f"{key}={value}")
    print(f"candidate_json={CANDIDATE_JSON.relative_to(PROJECT_ROOT)}")
    print(f"candidate_csv={CANDIDATE_CSV.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## `runtime/knowledge/tools/canonical_builder.py`

- size: 5951 bytes
- sha256: `5554ede5832f8bb046887ef44e7ed96fcdbda1dcda41192c3b288bf5ff403a9e`
- category: knowledge

```python
"""Build deterministic canonical RHCSA command entries from parsed sections."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "knowledge" / "parsed" / "rhcsa_sections.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "knowledge" / "canonical" / "rhcsa_commands.json"
DEFAULT_RISK = "unclassified"

WHITESPACE_RE = re.compile(r"\s+")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 1:
        print("ERROR: usage: python3 knowledge/tools/canonical_builder.py [sections_json]")
        return 2

    input_path = Path(args[0]).resolve() if args else DEFAULT_INPUT
    output_path = DEFAULT_OUTPUT

    try:
        report = build_canonical(input_path, output_path)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: RHCSA canonical command build complete")
    print(f"canonical_entries_created={report['canonical_entries_created']}")
    print(f"duplicates_removed={report['duplicates_removed']}")
    print(f"malformed_entries_skipped={report['malformed_entries_skipped']}")
    print(f"output_path={output_path}")
    return 0


def build_canonical(input_path: Path, output_path: Path) -> dict[str, int]:
    if not input_path.exists():
        raise RuntimeError(f"input file does not exist: {input_path}")
    if not input_path.is_file():
        raise RuntimeError(f"input path is not a file: {input_path}")
    if input_path.stat().st_size == 0:
        raise RuntimeError(f"input file is empty: {input_path}")

    try:
        sections = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON: {exc.msg}") from exc

    if not isinstance(sections, list):
        raise RuntimeError("parsed sections file must contain a JSON array")

    entries: list[dict[str, Any]] = []
    seen_commands: set[str] = set()
    duplicates_removed = 0
    malformed_entries_skipped = 0

    for section_index, section in enumerate(sections):
        if not isinstance(section, dict):
            print(f"WARN: skipped malformed section at index {section_index}")
            malformed_entries_skipped += 1
            continue

        source_section = normalize_text(section.get("section", ""))
        commands = section.get("commands")
        examples = section.get("examples", [])

        if not source_section or not isinstance(commands, list):
            print(f"WARN: skipped malformed section at index {section_index}")
            malformed_entries_skipped += 1
            continue

        section_examples = normalize_examples(examples)

        for command_index, raw_command in enumerate(commands):
            command = normalize_text(raw_command)
            if not command:
                print(
                    "WARN: skipped malformed command "
                    f"at section_index={section_index} command_index={command_index}"
                )
                malformed_entries_skipped += 1
                continue

            if command in seen_commands:
                duplicates_removed += 1
                continue

            entry = {
                "command": command,
                "category": source_section,
                "risk": DEFAULT_RISK,
                "description": "",
                "examples": select_examples(command, section_examples),
                "source_section": source_section,
            }

            validation_error = validate_entry(entry)
            if validation_error:
                print(
                    "WARN: skipped malformed entry "
                    f"at section_index={section_index} command_index={command_index}: "
                    f"{validation_error}"
                )
                malformed_entries_skipped += 1
                continue

            entries.append(entry)
            seen_commands.add(command)

    if not entries:
        raise RuntimeError("no canonical entries created")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if not output_path.exists():
        raise RuntimeError(f"output file was not created: {output_path}")
    if output_path.stat().st_size == 0:
        raise RuntimeError(f"output file is empty: {output_path}")

    return {
        "canonical_entries_created": len(entries),
        "duplicates_removed": duplicates_removed,
        "malformed_entries_skipped": malformed_entries_skipped,
    }


def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return WHITESPACE_RE.sub(" ", value).strip()


def normalize_examples(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        example = normalize_text(item)
        if example and example not in seen:
            normalized.append(example)
            seen.add(example)
    return normalized


def select_examples(command: str, section_examples: list[str]) -> list[str]:
    matches = [example for example in section_examples if example == command]
    return matches if matches else []


def validate_entry(entry: dict[str, Any]) -> str | None:
    if not entry.get("command"):
        return "command field required"
    if not entry.get("category"):
        return "category field required"
    if not entry.get("risk"):
        return "risk field required"
    if not isinstance(entry.get("examples"), list):
        return "examples must be an array"
    if not entry.get("source_section"):
        return "source_section field required"
    return None


if __name__ == "__main__":
    raise SystemExit(main())
```

## `runtime/knowledge/tools/context_injector.py`

- size: 7102 bytes
- sha256: `72909f9ffdbca9ba3c8a92d3e10069dc000fa239bf644352d91a7e764f837f1f`
- category: knowledge

```python
"""Build static deterministic helper context from RHCSA context packs."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTEXT_PACK = PROJECT_ROOT / "knowledge" / "context" / "context_pack.json"
DEFAULT_CANONICAL = PROJECT_ROOT / "knowledge" / "canonical" / "rhcsa_commands.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "knowledge" / "injection" / "injected_context.json"
SOURCE_NAME = "RHCSA knowledge pack"

WHITESPACE_RE = re.compile(r"\s+")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        print("ERROR: usage: python3 knowledge/tools/context_injector.py")
        return 2

    try:
        report = build_injected_context(DEFAULT_CONTEXT_PACK, DEFAULT_CANONICAL, DEFAULT_OUTPUT)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: RHCSA deterministic context injection build complete")
    print(f"injected_contexts_generated={report['injected_contexts_generated']}")
    print(f"commands_injected={report['commands_injected']}")
    print(f"duplicates_removed={report['duplicates_removed']}")
    print(f"malformed_entries_skipped={report['malformed_entries_skipped']}")
    print(f"output_path={DEFAULT_OUTPUT}")
    return 0


def build_injected_context(
    context_pack_path: Path,
    canonical_path: Path,
    output_path: Path,
) -> dict[str, int]:
    context_packs = load_json_array(context_pack_path, "context pack")
    canonical_entries = load_json_array(canonical_path, "canonical commands")
    canonical_commands, malformed_canonical = load_canonical_commands(canonical_entries)

    injected_contexts: list[dict[str, Any]] = []
    total_commands_injected = 0
    total_duplicates_removed = 0
    malformed_entries_skipped = malformed_canonical

    for pack_index, pack in enumerate(context_packs):
        if not isinstance(pack, dict):
            print(f"WARN: skipped malformed context pack at index {pack_index}")
            malformed_entries_skipped += 1
            continue

        query = normalize_text(pack.get("query"))
        matched_commands = pack.get("matched_commands")
        if not query or not isinstance(matched_commands, list):
            print(f"WARN: skipped malformed context pack at index {pack_index}")
            malformed_entries_skipped += 1
            continue

        static_context: list[str] = []
        seen_commands: set[str] = set()

        for command_index, command_entry in enumerate(matched_commands):
            if not isinstance(command_entry, dict):
                print(
                    "WARN: skipped malformed matched command "
                    f"at pack_index={pack_index} command_index={command_index}"
                )
                malformed_entries_skipped += 1
                continue

            command = normalize_text(command_entry.get("command"))
            if not command:
                print(
                    "WARN: skipped matched command without command field "
                    f"at pack_index={pack_index} command_index={command_index}"
                )
                malformed_entries_skipped += 1
                continue

            if command in seen_commands:
                total_duplicates_removed += 1
                continue

            if command not in canonical_commands:
                print(f"WARN: skipped command missing from canonical pack: {command}")
                malformed_entries_skipped += 1
                continue

            static_context.append(f"Use: {command}")
            seen_commands.add(command)

        injected = {
            "query": query,
            "static_context": static_context,
            "source": SOURCE_NAME,
        }
        validate_injected_context(injected, pack_index)
        injected_contexts.append(injected)
        total_commands_injected += len(static_context)

    if not injected_contexts:
        raise RuntimeError("no injected contexts generated")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(injected_contexts, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if not output_path.exists():
        raise RuntimeError(f"output file was not created: {output_path}")
    if output_path.stat().st_size == 0:
        raise RuntimeError(f"output file is empty: {output_path}")

    return {
        "injected_contexts_generated": len(injected_contexts),
        "commands_injected": total_commands_injected,
        "duplicates_removed": total_duplicates_removed,
        "malformed_entries_skipped": malformed_entries_skipped,
    }


def load_json_array(path: Path, label: str) -> list[Any]:
    if not path.exists():
        raise RuntimeError(f"{label} file does not exist: {path}")
    if not path.is_file():
        raise RuntimeError(f"{label} path is not a file: {path}")
    if path.stat().st_size == 0:
        raise RuntimeError(f"{label} file is empty: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} invalid JSON: {exc.msg}") from exc
    if not isinstance(data, list):
        raise RuntimeError(f"{label} must contain a JSON array")
    return data


def load_canonical_commands(entries: list[Any]) -> tuple[set[str], int]:
    commands: set[str] = set()
    malformed_entries = 0
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            print(f"WARN: skipped malformed canonical entry at index {index}")
            malformed_entries += 1
            continue
        command = normalize_text(entry.get("command"))
        if not command:
            print(f"WARN: skipped canonical entry without command at index {index}")
            malformed_entries += 1
            continue
        commands.add(command)
    return commands, malformed_entries


def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return WHITESPACE_RE.sub(" ", value).strip()


def validate_injected_context(context: dict[str, Any], index: int) -> None:
    if not context.get("query"):
        raise RuntimeError(f"injected context at index {index} has empty query")
    static_context = context.get("static_context")
    if not isinstance(static_context, list):
        raise RuntimeError(f"injected context at index {index} has invalid static_context")
    if len(static_context) != len(set(static_context)):
        raise RuntimeError(f"injected context at index {index} has duplicate command injections")
    for item in static_context:
        if not isinstance(item, str) or not item.startswith("Use: "):
            raise RuntimeError(f"injected context at index {index} has malformed injection")
    if context.get("source") != SOURCE_NAME:
        raise RuntimeError(f"injected context at index {index} has invalid source")


if __name__ == "__main__":
    raise SystemExit(main())
```

## `runtime/knowledge/tools/context_pack_builder.py`

- size: 8220 bytes
- sha256: `4063cb327e9f1532d0b923986b7f05e8b57db3c26885846eefbb0c4b88854ca0`
- category: knowledge

```python
"""Build deterministic static context packs from the RHCSA keyword index."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INDEX = PROJECT_ROOT / "knowledge" / "index" / "command_index.json"
DEFAULT_COMMANDS = PROJECT_ROOT / "knowledge" / "canonical" / "rhcsa_commands.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "knowledge" / "context" / "context_pack.json"
DEFAULT_QUERIES = ("network ports",)

TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ÖØ-öø-ÿ_./$~{}*?+-]+")
WHITESPACE_RE = re.compile(r"\s+")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    queries = [normalize_text(query) for query in args] if args else list(DEFAULT_QUERIES)
    queries = [query for query in queries if query]
    if not queries:
        print("ERROR: at least one non-empty query is required")
        return 2

    try:
        report = build_context_packs(DEFAULT_INDEX, DEFAULT_COMMANDS, DEFAULT_OUTPUT, queries)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: RHCSA deterministic context pack build complete")
    print(f"context_packs_generated={report['context_packs_generated']}")
    print(f"matched_keywords={report['matched_keywords']}")
    print(f"matched_commands={report['matched_commands']}")
    print(f"duplicates_removed={report['duplicates_removed']}")
    print(f"malformed_entries_skipped={report['malformed_entries_skipped']}")
    print(f"output_path={DEFAULT_OUTPUT}")
    return 0


def build_context_packs(
    index_path: Path,
    commands_path: Path,
    output_path: Path,
    queries: list[str],
) -> dict[str, int]:
    index = load_json_object(index_path, "command index")
    canonical_entries = load_json_array(commands_path, "canonical commands")
    command_map, malformed_entries_skipped = build_command_map(canonical_entries)

    context_packs: list[dict[str, Any]] = []
    total_matched_keywords = 0
    total_matched_commands = 0
    total_duplicates_removed = 0

    for query in queries:
        pack, duplicates_removed = build_context_pack(query, index, command_map)
        context_packs.append(pack)
        total_matched_keywords += len(pack["matched_keywords"])
        total_matched_commands += len(pack["matched_commands"])
        total_duplicates_removed += duplicates_removed

    validate_context_packs(context_packs)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(context_packs, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if not output_path.exists():
        raise RuntimeError(f"output file was not created: {output_path}")
    if output_path.stat().st_size == 0:
        raise RuntimeError(f"output file is empty: {output_path}")

    return {
        "context_packs_generated": len(context_packs),
        "matched_keywords": total_matched_keywords,
        "matched_commands": total_matched_commands,
        "duplicates_removed": total_duplicates_removed,
        "malformed_entries_skipped": malformed_entries_skipped,
    }


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    data = load_json(path, label)
    if not isinstance(data, dict):
        raise RuntimeError(f"{label} must contain a JSON object")
    return data


def load_json_array(path: Path, label: str) -> list[Any]:
    data = load_json(path, label)
    if not isinstance(data, list):
        raise RuntimeError(f"{label} must contain a JSON array")
    return data


def load_json(path: Path, label: str) -> Any:
    if not path.exists():
        raise RuntimeError(f"{label} file does not exist: {path}")
    if not path.is_file():
        raise RuntimeError(f"{label} path is not a file: {path}")
    if path.stat().st_size == 0:
        raise RuntimeError(f"{label} file is empty: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} invalid JSON: {exc.msg}") from exc


def build_command_map(entries: list[Any]) -> tuple[dict[str, dict[str, Any]], int]:
    command_map: dict[str, dict[str, Any]] = {}
    malformed_entries_skipped = 0
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            print(f"WARN: skipped malformed canonical entry at index {index}")
            malformed_entries_skipped += 1
            continue
        command = normalize_text(entry.get("command"))
        if not command:
            print(f"WARN: skipped canonical entry without command at index {index}")
            malformed_entries_skipped += 1
            continue
        command_map[command] = entry
    return command_map, malformed_entries_skipped


def build_context_pack(
    query: str,
    index: dict[str, Any],
    command_map: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], int]:
    query_tokens = sorted(tokenize(query))
    matched_keywords = [token for token in query_tokens if token in index]

    matched_commands: list[dict[str, Any]] = []
    seen_commands: set[str] = set()
    duplicates_removed = 0

    for keyword in matched_keywords:
        commands = index.get(keyword, [])
        if not isinstance(commands, list):
            print(f"WARN: skipped malformed command list for keyword: {keyword}")
            continue
        for raw_command in commands:
            command = normalize_text(raw_command)
            if not command:
                print(f"WARN: skipped malformed command for keyword: {keyword}")
                continue
            if command in seen_commands:
                duplicates_removed += 1
                continue

            entry = command_map.get(command)
            if not entry:
                print(f"WARN: skipped command missing canonical entry: {command}")
                continue

            matched_commands.append(
                {
                    "command": command,
                    "description": normalize_text(entry.get("description")),
                    "examples": normalize_examples(entry.get("examples")),
                    "source_section": normalize_text(entry.get("source_section")),
                }
            )
            seen_commands.add(command)

    return (
        {
            "query": query,
            "matched_keywords": matched_keywords,
            "matched_commands": matched_commands,
        },
        duplicates_removed,
    )


def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return WHITESPACE_RE.sub(" ", value).strip()


def normalize_examples(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    examples: list[str] = []
    seen: set[str] = set()
    for item in value:
        example = normalize_text(item)
        if example and example not in seen:
            examples.append(example)
            seen.add(example)
    return examples


def tokenize(value: str) -> set[str]:
    tokens: set[str] = set()
    for match in TOKEN_RE.finditer(value.lower()):
        token = match.group(0).strip(".,:;()[]{}\"'")
        if token:
            tokens.add(token)
    return tokens


def validate_context_packs(context_packs: list[dict[str, Any]]) -> None:
    for index, pack in enumerate(context_packs):
        if not pack.get("query"):
            raise RuntimeError(f"context pack at index {index} has empty query")
        keywords = pack.get("matched_keywords")
        if not isinstance(keywords, list) or keywords != sorted(keywords):
            raise RuntimeError(f"context pack at index {index} has invalid keyword order")
        commands = pack.get("matched_commands")
        if not isinstance(commands, list):
            raise RuntimeError(f"context pack at index {index} has invalid matched_commands")
        command_names = [entry.get("command") for entry in commands if isinstance(entry, dict)]
        if len(command_names) != len(set(command_names)):
            raise RuntimeError(f"context pack at index {index} has duplicate commands")


if __name__ == "__main__":
    raise SystemExit(main())
```

## `runtime/knowledge/tools/index_builder.py`

- size: 5228 bytes
- sha256: `0fa47676973124140eec4734f576b30b65b7f4d1b47e474c9d8ff76ffeb5b403`
- category: knowledge

```python
"""Build a deterministic local keyword index for canonical RHCSA commands."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "knowledge" / "canonical" / "rhcsa_commands.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "knowledge" / "index" / "command_index.json"

TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ÖØ-öø-ÿ_./$~{}*?+-]+")
WHITESPACE_RE = re.compile(r"\s+")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 1:
        print("ERROR: usage: python3 knowledge/tools/index_builder.py [canonical_json]")
        return 2

    input_path = Path(args[0]).resolve() if args else DEFAULT_INPUT
    output_path = DEFAULT_OUTPUT

    try:
        report = build_index(input_path, output_path)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: RHCSA deterministic keyword index build complete")
    print(f"keywords_indexed={report['keywords_indexed']}")
    print(f"commands_indexed={report['commands_indexed']}")
    print(f"duplicates_removed={report['duplicates_removed']}")
    print(f"malformed_entries_skipped={report['malformed_entries_skipped']}")
    print(f"output_path={output_path}")
    return 0


def build_index(input_path: Path, output_path: Path) -> dict[str, int]:
    if not input_path.exists():
        raise RuntimeError(f"input file does not exist: {input_path}")
    if not input_path.is_file():
        raise RuntimeError(f"input path is not a file: {input_path}")
    if input_path.stat().st_size == 0:
        raise RuntimeError(f"input file is empty: {input_path}")

    try:
        entries = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON: {exc.msg}") from exc

    if not isinstance(entries, list):
        raise RuntimeError("canonical command file must contain a JSON array")

    index: dict[str, set[str]] = defaultdict(set)
    malformed_entries_skipped = 0
    duplicate_links_removed = 0
    unique_commands: set[str] = set()

    for entry_index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            print(f"WARN: skipped malformed entry at index {entry_index}")
            malformed_entries_skipped += 1
            continue

        command = normalize_text(entry.get("command"))
        category = normalize_text(entry.get("category"))
        if not command or not category:
            print(f"WARN: skipped malformed entry at index {entry_index}")
            malformed_entries_skipped += 1
            continue

        unique_commands.add(command)
        keywords = sorted(tokenize(category) | tokenize(command))
        if not keywords:
            print(f"WARN: skipped entry with no keywords at index {entry_index}")
            malformed_entries_skipped += 1
            continue

        for keyword in keywords:
            before = len(index[keyword])
            index[keyword].add(command)
            if len(index[keyword]) == before:
                duplicate_links_removed += 1

    if not index:
        raise RuntimeError("no index entries created")

    deterministic_index = {
        keyword: sorted(commands)
        for keyword, commands in sorted(index.items(), key=lambda item: item[0])
    }
    validate_index(deterministic_index)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(deterministic_index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if not output_path.exists():
        raise RuntimeError(f"output file was not created: {output_path}")
    if output_path.stat().st_size == 0:
        raise RuntimeError(f"output file is empty: {output_path}")

    return {
        "keywords_indexed": len(deterministic_index),
        "commands_indexed": len(unique_commands),
        "duplicates_removed": duplicate_links_removed,
        "malformed_entries_skipped": malformed_entries_skipped,
    }


def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return WHITESPACE_RE.sub(" ", value).strip()


def tokenize(value: str) -> set[str]:
    tokens: set[str] = set()
    for match in TOKEN_RE.finditer(value.lower()):
        token = match.group(0).strip(".,:;()[]{}\"'")
        if token:
            tokens.add(token)
    return tokens


def validate_index(index: dict[str, list[str]]) -> None:
    previous_key = ""
    for key, commands in index.items():
        if previous_key and key < previous_key:
            raise RuntimeError("index keys are not sorted")
        previous_key = key
        if not isinstance(commands, list):
            raise RuntimeError(f"invalid command list for keyword: {key}")
        if len(commands) != len(set(commands)):
            raise RuntimeError(f"duplicate commands found for keyword: {key}")
        if commands != sorted(commands):
            raise RuntimeError(f"commands are not sorted for keyword: {key}")


if __name__ == "__main__":
    raise SystemExit(main())
```

## `runtime/knowledge/tools/markdown_kb_builder.py`

- size: 14211 bytes
- sha256: `5e2cfd54e8698bfb817611921871323c60c998b3bad65f7c91d53dfd60e8676b`
- category: knowledge

```python
#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_PATH = ROOT / "canonical" / "rhcsa_commands.json"
TOPIC_DIRS = (
    "filesystem",
    "networking",
    "users",
    "permissions",
    "selinux",
    "systemd",
    "storage",
    "lvm",
    "podman",
    "bash",
    "troubleshooting",
)

TOPIC_DESCRIPTIONS = {
    "filesystem": "File navigation, file operations, search, archives, and editor-oriented workflows.",
    "networking": "Networking, SSH, firewall, remote access, and shared-service connectivity.",
    "users": "User, group, identity, and account lifecycle operations.",
    "permissions": "Ownership, permission bits, access control basics, and safe permission checks.",
    "selinux": "SELinux inspection, contexts, booleans, labeling, and policy-related remediation.",
    "systemd": "systemd, services, boot flow, timers/cron, and package/service lifecycle actions.",
    "storage": "Disks, partitions, filesystems, mount operations, RAID, and persistence checks.",
    "lvm": "Logical Volume Manager concepts and operational commands.",
    "podman": "Podman images, containers, pods, volumes, networks, and rootless usage patterns.",
    "bash": "Shell variables, scripting, text processing, and CLI composition patterns.",
    "troubleshooting": "Diagnostics, logs, process inspection, system information, and recovery-oriented workflows.",
}

TOPIC_KEYWORDS = {
    "filesystem": (
        "nawigacja",
        "operacje na plikach",
        "przegladanie zawartosci plikow",
        "wyszukiwanie plikow",
        "archiwizacja",
        "vim",
    ),
    "networking": (
        "sie",
        "ssh",
        "zapora",
        "firewalld",
        "nfs",
        "samba",
        "autofs",
    ),
    "users": (
        "ytkownik",
        "grupami",
        "grup",
    ),
    "permissions": (
        "uprawnienia",
        "wlasnosc",
        "wlasnosc",
    ),
    "selinux": ("selinux",),
    "systemd": (
        "systemd",
        "uslugami",
        "usluga",
        "boot",
        "grub",
        "cron",
        "harmonogramowanie",
        "pakietami",
        "dnf",
        "rpm",
    ),
    "storage": (
        "systemy plikow",
        "montowanie",
        "dysk",
        "partycje",
        "raid",
        "przechowywanie danych",
    ),
    "lvm": ("lvm", "logical volume"),
    "podman": ("podman", "kontenery"),
    "bash": (
        "powloka",
        "bash",
        "rodowiskowe",
        "filtrowanie tekstu",
        "tekstowe",
        "skrypty bash",
    ),
    "troubleshooting": (
        "diagnostyka",
        "logowanie",
        "monitorowanie",
        "informacje o systemie",
        "procesami",
        "administracyjne",
    ),
}


@dataclass(frozen=True)
class CommandEntry:
    command: str
    category: str
    risk: str
    description: str
    examples: list[str]
    source_section: str


def normalize_text(value: str) -> str:
    ascii_text = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()


def slugify(value: str) -> str:
    slug = normalize_text(value).replace(" ", "-")
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "module"


def load_entries() -> list[CommandEntry]:
    payload = json.loads(CANONICAL_PATH.read_text(encoding="utf-8"))
    entries: list[CommandEntry] = []
    for item in payload:
        command = str(item.get("command", "")).strip()
        if not command:
            continue
        entries.append(
            CommandEntry(
                command=command,
                category=str(item.get("category", "")).strip(),
                risk=str(item.get("risk", "unclassified")).strip() or "unclassified",
                description=str(item.get("description", "")).strip(),
                examples=[str(example).strip() for example in item.get("examples", []) if str(example).strip()],
                source_section=str(item.get("source_section", "")).strip() or str(item.get("category", "")).strip(),
            )
        )
    return entries


def detect_topic(section: str) -> str:
    normalized = normalize_text(section)
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return topic
    return "filesystem"


def summarize_section(entries: list[CommandEntry]) -> str:
    commands = [entry.command for entry in entries]
    families = sorted({head for command in commands if (head := semantic_head(command))})[:8]
    return (
        f"Imported RHCSA material for {len(entries)} commands. "
        f"Primary command families: {', '.join(families) if families else 'none'}."
    )


def base_command(command: str) -> str:
    return command.split()[0]


def semantic_head(command: str) -> str | None:
    head = base_command(command)
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9._:+-]*", head):
        return None
    return head.lower()


def derived_tags(topic: str, section: str, entries: list[CommandEntry]) -> list[str]:
    tags = {"rhcsa", "linux", topic, slugify(section)}
    for entry in entries:
        head = semantic_head(entry.command)
        if head:
            tags.add(head)
    return sorted(tags)


def troubleshooting_notes(topic: str, entries: list[CommandEntry]) -> list[str]:
    commands = " ".join(entry.command for entry in entries).lower()
    notes: list[str] = []
    if "rm -rf" in commands or "rsync --delete" in commands:
        notes.append("Verify the full target path with `pwd` and `ls` before destructive filesystem commands.")
    if "grep" in commands or "awk" in commands or "sed" in commands:
        notes.append("Quote patterns explicitly to avoid shell expansion when matching text.")
    if "systemctl" in commands:
        notes.append("If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.")
    if "journalctl" in commands:
        notes.append("Use time or unit filters first to keep logs readable on low-RAM systems.")
    if "chmod" in commands or "chown" in commands:
        notes.append("Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.")
    if "useradd" in commands or "passwd" in commands or "usermod" in commands:
        notes.append("Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.")
    if "nmcli" in commands or "ip " in commands or "ssh" in commands or "firewall-cmd" in commands:
        notes.append("Check interface state, service state, and firewall exposure together during network diagnostics.")
    if "mount" in commands or "mkfs" in commands or "lsblk" in commands or "fdisk" in commands:
        notes.append("Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.")
    if re.search(r"\b(pvs|vgs|lvs|pvcreate|vgcreate|lvcreate|lvextend|lvreduce|lvremove|vgextend|pvdisplay|vgdisplay|lvdisplay)\b", commands):
        notes.append("Validate PV/VG/LV layout with `pvs`, `vgs`, and `lvs` before resizing storage.")
    if "podman" in commands:
        notes.append("When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.")
    if "selinux" in commands or "semanage" in commands or "restorecon" in commands or "getenforce" in commands:
        notes.append("Correlate AVC denials with labels and booleans before disabling SELinux protections.")
    if not notes:
        notes.append("Validate command intent against current host state before applying changes in production.")
    if topic == "troubleshooting":
        notes.append("Prefer read-only inspection first, then narrow fixes to the subsystem that produced the symptom.")
    return notes[:4]


def render_module(topic: str, section: str, entries: list[CommandEntry]) -> str:
    tags = derived_tags(topic, section, entries)
    lines = [
        "---",
        f"title: {section}",
        f"topic: {topic}",
        f"source_section: {section}",
        "source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from: knowledge/canonical/rhcsa_commands.json",
        f"tags: [{', '.join(tags)}]",
        "---",
        "",
        f"# {section}",
        "",
        summarize_section(entries),
        "",
        "## Tags",
        "",
        ", ".join(tags),
        "",
        "## Examples",
        "",
    ]
    examples = unique_examples(entries)[:10]
    for example in examples:
        lines.append(f"- `{example}`")

    lines.extend(
        [
            "",
            "## Troubleshooting",
            "",
        ]
    )
    for note in troubleshooting_notes(topic, entries):
        lines.append(f"- {note}")

    lines.extend(
        [
            "",
            "## Provenance",
            "",
            "- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`",
            "- Canonical import: `knowledge/canonical/rhcsa_commands.json`",
            f"- Source section: `{section}`",
            "",
            "## Commands",
            "",
        ]
    )

    for entry in entries:
        entry_examples = entry.examples[:3] or [entry.command]
        lines.extend(
            [
                f"### `{entry.command}`",
                "",
                f"- Category: `{entry.category or section}`",
                f"- Risk: `{entry.risk}`",
                f"- Tags: `{topic}`, `{semantic_head(entry.command) or slugify(base_command(entry.command))}`",
            ]
        )
        if entry.description:
            lines.append(f"- Description: {entry.description}")
        lines.append("- Examples:")
        for example in entry_examples:
            lines.append(f"  - `{example}`")
        lines.append("- Troubleshooting hint:")
        lines.append(f"  - {troubleshooting_notes(topic, [entry])[0]}")
        lines.append("- Provenance:")
        lines.append(f"  - RHCSA section: `{entry.source_section}`")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def unique_examples(entries: list[CommandEntry]) -> list[str]:
    seen: set[str] = set()
    examples: list[str] = []
    for entry in entries:
        for example in entry.examples or [entry.command]:
            if example not in seen:
                seen.add(example)
                examples.append(example)
    return examples


def render_topic_readme(topic: str, modules: list[tuple[str, Path, list[CommandEntry]]]) -> str:
    lines = [
        f"# {topic.title()}",
        "",
        TOPIC_DESCRIPTIONS[topic],
        "",
        "## Modules",
        "",
    ]
    for section, path, entries in modules:
        rel_path = path.relative_to(ROOT)
        lines.append(f"- `{rel_path}`: {len(entries)} imported commands from `{section}`")
    lines.extend(
        [
            "",
            "## Provenance",
            "",
            "- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`",
            "- Canonical import: `knowledge/canonical/rhcsa_commands.json`",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_root_readme(topic_map: dict[str, list[tuple[str, Path, list[CommandEntry]]]]) -> str:
    lines = [
        "# RHCSA Local Knowledge Base",
        "",
        "This directory contains the structured local RHCSA knowledge base built from the",
        "existing canonical command import. The original deterministic JSON pipeline remains",
        "in place; these markdown modules add topic-oriented operator-readable knowledge.",
        "",
        "## Topic Layout",
        "",
    ]
    for topic in TOPIC_DIRS:
        count = sum(len(entries) for _, _, entries in topic_map.get(topic, []))
        lines.append(f"- `{topic}/`: {count} commands")
    lines.extend(
        [
            "",
            "## Provenance",
            "",
            "- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`",
            "- Canonical import: `knowledge/canonical/rhcsa_commands.json`",
            "- Parsed sections: `knowledge/parsed/rhcsa_sections.json`",
            "",
            "## Notes",
            "",
            "- Existing deterministic JSON artifacts are preserved.",
            "- Markdown modules are generated from the canonical command import.",
            "- Topic mapping is heuristic but deterministic.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def reset_topic_dirs() -> None:
    for topic in TOPIC_DIRS:
        path = ROOT / topic
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)


def build() -> dict[str, list[tuple[str, Path, list[CommandEntry]]]]:
    entries = load_entries()
    grouped: dict[str, list[CommandEntry]] = defaultdict(list)
    for entry in entries:
        grouped[entry.source_section].append(entry)

    reset_topic_dirs()
    topic_map: dict[str, list[tuple[str, Path, list[CommandEntry]]]] = defaultdict(list)
    for section, section_entries in sorted(grouped.items()):
        topic = detect_topic(section)
        filename = slugify(section) + ".md"
        path = ROOT / topic / filename
        path.write_text(render_module(topic, section, section_entries), encoding="utf-8")
        topic_map[topic].append((section, path, section_entries))

    for topic in TOPIC_DIRS:
        readme_path = ROOT / topic / "README.md"
        readme_path.write_text(render_topic_readme(topic, topic_map.get(topic, [])), encoding="utf-8")

    (ROOT / "README.md").write_text(render_root_readme(topic_map), encoding="utf-8")
    return topic_map


def main() -> int:
    topic_map = build()
    print("Generated RHCSA markdown knowledge base:")
    for topic in TOPIC_DIRS:
        modules = topic_map.get(topic, [])
        command_count = sum(len(entries) for _, _, entries in modules)
        print(f"- {topic}: {len(modules)} modules, {command_count} commands")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## `runtime/knowledge/tools/pdf_extract.py`

- size: 3318 bytes
- sha256: `fe9d387d973b0f17a98c9afbc7bdc01ecf690c42670bebf2d92571d1fd0917b6`
- category: knowledge

```python
"""Deterministic raw text extraction for the RHCSA command library PDF."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "knowledge" / "source" / "RHCSA_Command_Library.pdf"
DEFAULT_OUTPUT = PROJECT_ROOT / "knowledge" / "raw" / "rhcsa_raw.txt"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 1:
        print("ERROR: usage: python3 knowledge/tools/pdf_extract.py [input_pdf]")
        return 2

    input_path = Path(args[0]).resolve() if args else DEFAULT_INPUT
    output_path = DEFAULT_OUTPUT

    try:
        pages = extract_pdf(input_path, output_path)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    size = output_path.stat().st_size
    print("OK: RHCSA PDF raw extraction complete")
    print(f"extracted_pages={pages}")
    print(f"output_size_bytes={size}")
    print(f"output_path={output_path}")
    return 0


def extract_pdf(input_path: Path, output_path: Path) -> int:
    if not input_path.exists():
        raise RuntimeError(f"input PDF does not exist: {input_path}")
    if not input_path.is_file():
        raise RuntimeError(f"input path is not a file: {input_path}")
    if input_path.suffix.lower() != ".pdf":
        raise RuntimeError(f"input file is not a PDF: {input_path}")

    pdftotext = shutil.which("pdftotext")
    pdfinfo = shutil.which("pdfinfo")
    if not pdftotext:
        raise RuntimeError("required local tool not found: pdftotext")
    if not pdfinfo:
        raise RuntimeError("required local tool not found: pdfinfo")

    pages = read_page_count(pdfinfo, input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"input_path={input_path}")
    print(f"output_path={output_path}")
    print("extractor=pdftotext")

    result = subprocess.run(
        [pdftotext, "-layout", "-enc", "UTF-8", str(input_path), str(output_path)],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "pdftotext failed"
        raise RuntimeError(message)

    if not output_path.exists():
        raise RuntimeError(f"output file was not created: {output_path}")
    if output_path.stat().st_size == 0:
        raise RuntimeError(f"output file is empty: {output_path}")

    return pages


def read_page_count(pdfinfo: str, input_path: Path) -> int:
    result = subprocess.run(
        [pdfinfo, str(input_path)],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "pdfinfo failed"
        raise RuntimeError(message)

    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            _, value = line.split(":", 1)
            try:
                return int(value.strip())
            except ValueError as exc:
                raise RuntimeError(f"invalid page count from pdfinfo: {value.strip()}") from exc

    raise RuntimeError("pdfinfo output did not include page count")


if __name__ == "__main__":
    raise SystemExit(main())
```

## `runtime/knowledge/tools/section_parser.py`

- size: 6321 bytes
- sha256: `a633ce2385ca4cba7d0a273d9283d8fbea8b8b10a72398a1d82c33a968eab787`
- category: knowledge

```python
"""Deterministic structural parser for RHCSA raw extracted text."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "knowledge" / "raw" / "rhcsa_raw.txt"
DEFAULT_OUTPUT = PROJECT_ROOT / "knowledge" / "parsed" / "rhcsa_sections.json"

SECTION_RE = re.compile(r"^\s*\D*\s*(\d{1,2})\.\s+(.+?)\s+(\d+)\s+komend\s*$")
PAGE_FOOTER_RE = re.compile(r"^\s*Biblioteka komend RHCSA\s+Strona\s+\d+\s*$")
HEADER_RE = re.compile(r"^\s*RHCSA COMMAND LIBRARY\s+RHCSA 9\s+\|\s+Red Hat Certified System Administrator\s*$")
COMMAND_TOKEN_RE = re.compile(r"^[a-zA-Z0-9_./$~{}*?+-][^\s]{0,80}$")
SPLIT_RE = re.compile(r"\s{2,}")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 1:
        print("ERROR: usage: python3 knowledge/tools/section_parser.py [raw_text_file]")
        return 2

    input_path = Path(args[0]).resolve() if args else DEFAULT_INPUT
    output_path = DEFAULT_OUTPUT

    try:
        report = parse_file(input_path, output_path)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: RHCSA section parsing complete")
    print(f"sections_found={report['sections_found']}")
    print(f"commands_detected={report['commands_detected']}")
    print(f"malformed_blocks_skipped={report['malformed_blocks_skipped']}")
    print(f"output_path={output_path}")
    return 0


def parse_file(input_path: Path, output_path: Path) -> dict[str, int]:
    if not input_path.exists():
        raise RuntimeError(f"input file does not exist: {input_path}")
    if not input_path.is_file():
        raise RuntimeError(f"input path is not a file: {input_path}")
    if input_path.stat().st_size == 0:
        raise RuntimeError(f"input file is empty: {input_path}")

    raw_text = input_path.read_text(encoding="utf-8")
    sections, malformed_blocks = parse_sections(raw_text.splitlines())
    validate_sections(sections)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(sections, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if not output_path.exists():
        raise RuntimeError(f"output file was not created: {output_path}")
    if output_path.stat().st_size == 0:
        raise RuntimeError(f"output file is empty: {output_path}")

    commands_detected = sum(len(section["commands"]) for section in sections)
    return {
        "sections_found": len(sections),
        "commands_detected": commands_detected,
        "malformed_blocks_skipped": malformed_blocks,
    }


def parse_sections(lines: list[str]) -> tuple[list[dict[str, Any]], int]:
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    malformed_blocks = 0

    for line in lines:
        cleaned = line.strip()
        if should_skip_line(cleaned):
            continue

        section_match = SECTION_RE.match(cleaned)
        if section_match:
            section_name = normalize_section_name(section_match.group(2))
            if not section_name:
                malformed_blocks += 1
                current = None
                continue
            current = {"section": section_name, "commands": [], "examples": []}
            sections.append(current)
            continue

        if current is None:
            continue

        command_candidates = extract_command_candidates(line)
        if not command_candidates:
            continue

        for command in command_candidates:
            if command not in current["commands"]:
                current["commands"].append(command)
                current["examples"].append(command)

    return sections, malformed_blocks


def should_skip_line(cleaned: str) -> bool:
    if not cleaned:
        return True
    if cleaned == "\x0c":
        return True
    if PAGE_FOOTER_RE.match(cleaned):
        return True
    if HEADER_RE.match(cleaned):
        return True
    if cleaned.startswith("Spis Tre"):
        return True
    return False


def normalize_section_name(value: str) -> str:
    normalized = " ".join(value.split())
    return normalized.strip(" -")


def extract_command_candidates(line: str) -> list[str]:
    parts = [part.strip() for part in SPLIT_RE.split(line.rstrip()) if part.strip()]
    if len(parts) < 2:
        return []

    candidates: list[str] = []
    for index in range(0, len(parts), 2):
        token = parts[index]
        if is_command_like(token):
            candidates.append(token)
    return candidates


def is_command_like(value: str) -> bool:
    if len(value) > 90:
        return False
    if " " in value and not allowed_command_with_space(value):
        return False
    first = value.split()[0]
    if not COMMAND_TOKEN_RE.match(first):
        return False
    if value.endswith("."):
        return False
    return True


def allowed_command_with_space(value: str) -> bool:
    first = value.split()[0]
    return first in {
        "alias",
        "awk",
        "cat",
        "cd",
        "chmod",
        "chown",
        "cp",
        "dnf",
        "echo",
        "find",
        "firewall-cmd",
        "grep",
        "ip",
        "journalctl",
        "ls",
        "mkdir",
        "mount",
        "nmcli",
        "podman",
        "restorecon",
        "rm",
        "rpm",
        "rsync",
        "semanage",
        "setsebool",
        "ssh",
        "systemctl",
        "tar",
        "touch",
        "useradd",
        "usermod",
        "vim",
    }


def validate_sections(sections: list[dict[str, Any]]) -> None:
    if not sections:
        raise RuntimeError("no sections detected")
    for index, section in enumerate(sections):
        name = section.get("section")
        if not isinstance(name, str) or not name.strip():
            raise RuntimeError(f"empty section name at index {index}")
        if not isinstance(section.get("commands"), list):
            raise RuntimeError(f"invalid commands list at index {index}")
        if not isinstance(section.get("examples"), list):
            raise RuntimeError(f"invalid examples list at index {index}")


if __name__ == "__main__":
    raise SystemExit(main())
```

## `runtime/knowledge/troubleshooting/README.md`

- size: 824 bytes
- sha256: `b90c3dc0c1134dc6e85523fd5836970e3863d6aeb5213feff1ac818f039a1a56`
- category: knowledge

```markdown
# Troubleshooting

Diagnostics, logs, process inspection, system information, and recovery-oriented workflows.

## Modules

- `troubleshooting/diagnostyka-i-narzdzia-systemowe.md`: 15 imported commands from `Diagnostyka i narz■dzia systemowe`
- `troubleshooting/dodatkowe-narzdzia-administracyjne.md`: 24 imported commands from `Dodatkowe narz■dzia administracyjne`
- `troubleshooting/informacje-o-systemie.md`: 17 imported commands from `Informacje o systemie`
- `troubleshooting/logowanie-i-monitorowanie-systemu.md`: 16 imported commands from `Logowanie i monitorowanie systemu`
- `troubleshooting/zarzdzanie-procesami.md`: 16 imported commands from `Zarz■dzanie procesami`

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
```

## `runtime/knowledge/troubleshooting/diagnostyka-i-narzdzia-systemowe.md`

- size: 6570 bytes
- sha256: `7aa0f052225cde7a95ee97763db4e5b5c9dcce30d28974f986ee23bbd4214faf`
- category: knowledge

```markdown
---
title: Diagnostyka i narz■dzia systemowe
topic: troubleshooting
source_section: Diagnostyka i narz■dzia systemowe
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [bonnie++, cat, cmd, diagnostyka-i-narzdzia-systemowe, fio, ip, kdump, linux, rhcsa, troubleshooting, valgrind]
---

# Diagnostyka i narz■dzia systemowe

Imported RHCSA material for 15 commands. Primary command families: bonnie++, cat, cmd, fio, ip, kdump, valgrind.

## Tags

bonnie++, cat, cmd, diagnostyka-i-narzdzia-systemowe, fio, ip, kdump, linux, rhcsa, troubleshooting, valgrind

## Examples

- `cmd`
- `ip -s link show eth0`
- `valgrind`
- `--leak-check=full`
- `cat /proc/sys/net/nf`
- `/var/log/sa/saDD`
- `kdump`
- `cat /etc/kdump.conf`
- `fio`
- `--filename=/tmp/test`

## Troubleshooting

- Check interface state, service state, and firewall exposure together during network diagnostics.
- Prefer read-only inspection first, then narrow fixes to the subsystem that produced the symptom.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Diagnostyka i narz■dzia systemowe`

## Commands

### `cmd`

- Category: `Diagnostyka i narz■dzia systemowe`
- Risk: `unclassified`
- Tags: `troubleshooting`, `cmd`
- Examples:
  - `cmd`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Diagnostyka i narz■dzia systemowe`

### `ip -s link show eth0`

- Category: `Diagnostyka i narz■dzia systemowe`
- Risk: `unclassified`
- Tags: `troubleshooting`, `ip`
- Examples:
  - `ip -s link show eth0`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Diagnostyka i narz■dzia systemowe`

### `valgrind`

- Category: `Diagnostyka i narz■dzia systemowe`
- Risk: `unclassified`
- Tags: `troubleshooting`, `valgrind`
- Examples:
  - `valgrind`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Diagnostyka i narz■dzia systemowe`

### `--leak-check=full`

- Category: `Diagnostyka i narz■dzia systemowe`
- Risk: `unclassified`
- Tags: `troubleshooting`, `leak-check-full`
- Examples:
  - `--leak-check=full`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Diagnostyka i narz■dzia systemowe`

### `cat /proc/sys/net/nf`

- Category: `Diagnostyka i narz■dzia systemowe`
- Risk: `unclassified`
- Tags: `troubleshooting`, `cat`
- Examples:
  - `cat /proc/sys/net/nf`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Diagnostyka i narz■dzia systemowe`

### `/var/log/sa/saDD`

- Category: `Diagnostyka i narz■dzia systemowe`
- Risk: `unclassified`
- Tags: `troubleshooting`, `var-log-sa-sadd`
- Examples:
  - `/var/log/sa/saDD`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Diagnostyka i narz■dzia systemowe`

### `kdump`

- Category: `Diagnostyka i narz■dzia systemowe`
- Risk: `unclassified`
- Tags: `troubleshooting`, `kdump`
- Examples:
  - `kdump`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Diagnostyka i narz■dzia systemowe`

### `cat /etc/kdump.conf`

- Category: `Diagnostyka i narz■dzia systemowe`
- Risk: `unclassified`
- Tags: `troubleshooting`, `cat`
- Examples:
  - `cat /etc/kdump.conf`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Diagnostyka i narz■dzia systemowe`

### `fio`

- Category: `Diagnostyka i narz■dzia systemowe`
- Risk: `unclassified`
- Tags: `troubleshooting`, `fio`
- Examples:
  - `fio`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Diagnostyka i narz■dzia systemowe`

### `--filename=/tmp/test`

- Category: `Diagnostyka i narz■dzia systemowe`
- Risk: `unclassified`
- Tags: `troubleshooting`, `filename-tmp-test`
- Examples:
  - `--filename=/tmp/test`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Diagnostyka i narz■dzia systemowe`

### `count=1000`

- Category: `Diagnostyka i narz■dzia systemowe`
- Risk: `unclassified`
- Tags: `troubleshooting`, `count-1000`
- Examples:
  - `count=1000`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Diagnostyka i narz■dzia systemowe`

### `bonnie++`

- Category: `Diagnostyka i narz■dzia systemowe`
- Risk: `unclassified`
- Tags: `troubleshooting`, `bonnie++`
- Examples:
  - `bonnie++`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Diagnostyka i narz■dzia systemowe`

### `cat /proc/net/tcp`

- Category: `Diagnostyka i narz■dzia systemowe`
- Risk: `unclassified`
- Tags: `troubleshooting`, `cat`
- Examples:
  - `cat /proc/net/tcp`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Diagnostyka i narz■dzia systemowe`

### `cat /proc/PID/limits`

- Category: `Diagnostyka i narz■dzia systemowe`
- Risk: `unclassified`
- Tags: `troubleshooting`, `cat`
- Examples:
  - `cat /proc/PID/limits`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Diagnostyka i narz■dzia systemowe`

### `cat /proc/net/udp`

- Category: `Diagnostyka i narz■dzia systemowe`
- Risk: `unclassified`
- Tags: `troubleshooting`, `cat`
- Examples:
  - `cat /proc/net/udp`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Diagnostyka i narz■dzia systemowe`
```

## `runtime/knowledge/troubleshooting/dodatkowe-narzdzia-administracyjne.md`

- size: 10308 bytes
- sha256: `b795b3136e658e380c3d1cf2c6f8c79369ef9156bfbbcd2311d6052dd97d7b0f`
- category: knowledge

```markdown
---
title: Dodatkowe narz■dzia administracyjne
topic: troubleshooting
source_section: Dodatkowe narz■dzia administracyjne
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [alternatives, authselect, bash, cat, dodatkowe-narzdzia-administracyjne, fips-mode-setup, ip, linux, ls, memory:mygroup, mygroup, ntsysv, rhcsa, scap-workbench, systemd-cgls, systemd-cgtop, troubleshooting, update-alternatives, update-crypto-polici, wireshark]
---

# Dodatkowe narz■dzia administracyjne

Imported RHCSA material for 24 commands. Primary command families: alternatives, authselect, bash, cat, fips-mode-setup, ip, ls, memory:mygroup.

## Tags

alternatives, authselect, bash, cat, dodatkowe-narzdzia-administracyjne, fips-mode-setup, ip, linux, ls, memory:mygroup, mygroup, ntsysv, rhcsa, scap-workbench, systemd-cgls, systemd-cgtop, troubleshooting, update-alternatives, update-crypto-polici, wireshark

## Examples

- `alternatives`
- `update-alternatives`
- `ntsysv`
- `systemd-cgtop`
- `systemd-cgls`
- `memory:mygroup`
- `scap-workbench`
- `t_in_bytes=512M`
- `mygroup`
- `cat /sys/fs/cgroup/m`

## Troubleshooting

- Check interface state, service state, and firewall exposure together during network diagnostics.
- Prefer read-only inspection first, then narrow fixes to the subsystem that produced the symptom.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Dodatkowe narz■dzia administracyjne`

## Commands

### `alternatives`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `alternatives`
- Examples:
  - `alternatives`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `update-alternatives`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `update-alternatives`
- Examples:
  - `update-alternatives`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `ntsysv`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `ntsysv`
- Examples:
  - `ntsysv`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `systemd-cgtop`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `systemd-cgtop`
- Examples:
  - `systemd-cgtop`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `systemd-cgls`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `systemd-cgls`
- Examples:
  - `systemd-cgls`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `memory:mygroup`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `memory:mygroup`
- Examples:
  - `memory:mygroup`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `scap-workbench`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `scap-workbench`
- Examples:
  - `scap-workbench`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `t_in_bytes=512M`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `t-in-bytes-512m`
- Examples:
  - `t_in_bytes=512M`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `mygroup`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `mygroup`
- Examples:
  - `mygroup`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `cat /sys/fs/cgroup/m`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `cat`
- Examples:
  - `cat /sys/fs/cgroup/m`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `fips-mode-setup`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `fips-mode-setup`
- Examples:
  - `fips-mode-setup`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `emory/mygroup/memory`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `emory-mygroup-memory`
- Examples:
  - `emory/mygroup/memory`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `ls /sys/fs/cgroup/`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `ls`
- Examples:
  - `ls /sys/fs/cgroup/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `update-crypto-polici`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `update-crypto-polici`
- Examples:
  - `update-crypto-polici`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `ip netns add myns`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `ip`
- Examples:
  - `ip netns add myns`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `ip netns exec myns`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `ip`
- Examples:
  - `ip netns exec myns`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `bash`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `bash`
- Examples:
  - `bash`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `ip netns list`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `ip`
- Examples:
  - `ip netns list`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `cat /etc/crypto-poli`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `cat`
- Examples:
  - `cat /etc/crypto-poli`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `ip netns delete myns`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `ip`
- Examples:
  - `ip netns delete myns`
- Troubleshooting hint:
  - Check interface state, service state, and firewall exposure together during network diagnostics.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `authselect`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `authselect`
- Examples:
  - `authselect`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `/tmp/cap.pcap`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `tmp-cap-pcap`
- Examples:
  - `/tmp/cap.pcap`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `wireshark`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `wireshark`
- Examples:
  - `wireshark`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`

### `--zone=drop`

- Category: `Dodatkowe narz■dzia administracyjne`
- Risk: `unclassified`
- Tags: `troubleshooting`, `zone-drop`
- Examples:
  - `--zone=drop`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Dodatkowe narz■dzia administracyjne`
```

## `runtime/knowledge/troubleshooting/informacje-o-systemie.md`

- size: 6657 bytes
- sha256: `a3a850b66b574e6148e931685a71f07226d2547d22d25045bd7a483f7cda265e`
- category: knowledge

```markdown
---
title: Informacje o systemie
topic: troubleshooting
source_section: Informacje o systemie
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [baseboard, cat, informacje-o-systemie, iostat, linux, lscpu, lshw, lsmem, lsnuma, lspci, lsusb, nproc, rhcsa, sensors, sensors-detect, troubleshooting, vmstat]
---

# Informacje o systemie

Imported RHCSA material for 17 commands. Primary command families: baseboard, cat, iostat, lscpu, lshw, lsmem, lsnuma, lspci.

## Tags

baseboard, cat, informacje-o-systemie, iostat, linux, lscpu, lshw, lsmem, lsnuma, lspci, lsusb, nproc, rhcsa, sensors, sensors-detect, troubleshooting, vmstat

## Examples

- `lsusb`
- `cat /etc/os-release`
- `lscpu`
- `cat /proc/uptime`
- `cat /proc/cpuinfo`
- `nproc`
- `lsmem`
- `vmstat`
- `iostat`
- `lsnuma`

## Troubleshooting

- Validate command intent against current host state before applying changes in production.
- Prefer read-only inspection first, then narrow fixes to the subsystem that produced the symptom.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Informacje o systemie`

## Commands

### `lsusb`

- Category: `Informacje o systemie`
- Risk: `unclassified`
- Tags: `troubleshooting`, `lsusb`
- Examples:
  - `lsusb`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Informacje o systemie`

### `cat /etc/os-release`

- Category: `Informacje o systemie`
- Risk: `unclassified`
- Tags: `troubleshooting`, `cat`
- Examples:
  - `cat /etc/os-release`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Informacje o systemie`

### `lscpu`

- Category: `Informacje o systemie`
- Risk: `unclassified`
- Tags: `troubleshooting`, `lscpu`
- Examples:
  - `lscpu`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Informacje o systemie`

### `cat /proc/uptime`

- Category: `Informacje o systemie`
- Risk: `unclassified`
- Tags: `troubleshooting`, `cat`
- Examples:
  - `cat /proc/uptime`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Informacje o systemie`

### `cat /proc/cpuinfo`

- Category: `Informacje o systemie`
- Risk: `unclassified`
- Tags: `troubleshooting`, `cat`
- Examples:
  - `cat /proc/cpuinfo`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Informacje o systemie`

### `nproc`

- Category: `Informacje o systemie`
- Risk: `unclassified`
- Tags: `troubleshooting`, `nproc`
- Examples:
  - `nproc`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Informacje o systemie`

### `lsmem`

- Category: `Informacje o systemie`
- Risk: `unclassified`
- Tags: `troubleshooting`, `lsmem`
- Examples:
  - `lsmem`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Informacje o systemie`

### `vmstat`

- Category: `Informacje o systemie`
- Risk: `unclassified`
- Tags: `troubleshooting`, `vmstat`
- Examples:
  - `vmstat`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Informacje o systemie`

### `iostat`

- Category: `Informacje o systemie`
- Risk: `unclassified`
- Tags: `troubleshooting`, `iostat`
- Examples:
  - `iostat`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Informacje o systemie`

### `lsnuma`

- Category: `Informacje o systemie`
- Risk: `unclassified`
- Tags: `troubleshooting`, `lsnuma`
- Examples:
  - `lsnuma`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Informacje o systemie`

### `cat /sys/class/dmi/i`

- Category: `Informacje o systemie`
- Risk: `unclassified`
- Tags: `troubleshooting`, `cat`
- Examples:
  - `cat /sys/class/dmi/i`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Informacje o systemie`

### `baseboard`

- Category: `Informacje o systemie`
- Risk: `unclassified`
- Tags: `troubleshooting`, `baseboard`
- Examples:
  - `baseboard`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Informacje o systemie`

### `lshw`

- Category: `Informacje o systemie`
- Risk: `unclassified`
- Tags: `troubleshooting`, `lshw`
- Examples:
  - `lshw`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Informacje o systemie`

### `sensors`

- Category: `Informacje o systemie`
- Risk: `unclassified`
- Tags: `troubleshooting`, `sensors`
- Examples:
  - `sensors`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Informacje o systemie`

### `sensors-detect`

- Category: `Informacje o systemie`
- Risk: `unclassified`
- Tags: `troubleshooting`, `sensors-detect`
- Examples:
  - `sensors-detect`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Informacje o systemie`

### `lspci`

- Category: `Informacje o systemie`
- Risk: `unclassified`
- Tags: `troubleshooting`, `lspci`
- Examples:
  - `lspci`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Informacje o systemie`

### `cat /sys/block/sda/q`

- Category: `Informacje o systemie`
- Risk: `unclassified`
- Tags: `troubleshooting`, `cat`
- Examples:
  - `cat /sys/block/sda/q`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Informacje o systemie`
```

## `runtime/knowledge/troubleshooting/logowanie-i-monitorowanie-systemu.md`

- size: 6981 bytes
- sha256: `bf8236778fe0e41f0f12b1e0d0d03100d2fa5d37e0d789753b773bc1138a4643`
- category: knowledge

```markdown
---
title: Logowanie i monitorowanie systemu
topic: troubleshooting
source_section: Logowanie i monitorowanie systemu
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [aureport, cat, dmesg, grep, journalctl, linux, logowanie-i-monitorowanie-systemu, ls, rhcsa, troubleshooting, udit.log]
---

# Logowanie i monitorowanie systemu

Imported RHCSA material for 16 commands. Primary command families: aureport, cat, dmesg, grep, journalctl, ls, udit.log.

## Tags

aureport, cat, dmesg, grep, journalctl, linux, logowanie-i-monitorowanie-systemu, ls, rhcsa, troubleshooting, udit.log

## Examples

- `journalctl -xe`
- `journalctl -u sshd`
- `aureport`
- `journalctl -o`
- `--disk-usage`
- `dmesg`
- `cat /etc/audit/audit`
- `--level=err,warn`
- `/var/log/messages`
- `cat /var/log/secure`

## Troubleshooting

- Quote patterns explicitly to avoid shell expansion when matching text.
- Use time or unit filters first to keep logs readable on low-RAM systems.
- Check interface state, service state, and firewall exposure together during network diagnostics.
- Prefer read-only inspection first, then narrow fixes to the subsystem that produced the symptom.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Logowanie i monitorowanie systemu`

## Commands

### `journalctl -xe`

- Category: `Logowanie i monitorowanie systemu`
- Risk: `unclassified`
- Tags: `troubleshooting`, `journalctl`
- Examples:
  - `journalctl -xe`
- Troubleshooting hint:
  - Use time or unit filters first to keep logs readable on low-RAM systems.
- Provenance:
  - RHCSA section: `Logowanie i monitorowanie systemu`

### `journalctl -u sshd`

- Category: `Logowanie i monitorowanie systemu`
- Risk: `unclassified`
- Tags: `troubleshooting`, `journalctl`
- Examples:
  - `journalctl -u sshd`
- Troubleshooting hint:
  - Use time or unit filters first to keep logs readable on low-RAM systems.
- Provenance:
  - RHCSA section: `Logowanie i monitorowanie systemu`

### `aureport`

- Category: `Logowanie i monitorowanie systemu`
- Risk: `unclassified`
- Tags: `troubleshooting`, `aureport`
- Examples:
  - `aureport`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Logowanie i monitorowanie systemu`

### `journalctl -o`

- Category: `Logowanie i monitorowanie systemu`
- Risk: `unclassified`
- Tags: `troubleshooting`, `journalctl`
- Examples:
  - `journalctl -o`
- Troubleshooting hint:
  - Use time or unit filters first to keep logs readable on low-RAM systems.
- Provenance:
  - RHCSA section: `Logowanie i monitorowanie systemu`

### `--disk-usage`

- Category: `Logowanie i monitorowanie systemu`
- Risk: `unclassified`
- Tags: `troubleshooting`, `disk-usage`
- Examples:
  - `--disk-usage`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Logowanie i monitorowanie systemu`

### `dmesg`

- Category: `Logowanie i monitorowanie systemu`
- Risk: `unclassified`
- Tags: `troubleshooting`, `dmesg`
- Examples:
  - `dmesg`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Logowanie i monitorowanie systemu`

### `cat /etc/audit/audit`

- Category: `Logowanie i monitorowanie systemu`
- Risk: `unclassified`
- Tags: `troubleshooting`, `cat`
- Examples:
  - `cat /etc/audit/audit`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Logowanie i monitorowanie systemu`

### `--level=err,warn`

- Category: `Logowanie i monitorowanie systemu`
- Risk: `unclassified`
- Tags: `troubleshooting`, `level-err-warn`
- Examples:
  - `--level=err,warn`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Logowanie i monitorowanie systemu`

### `/var/log/messages`

- Category: `Logowanie i monitorowanie systemu`
- Risk: `unclassified`
- Tags: `troubleshooting`, `var-log-messages`
- Examples:
  - `/var/log/messages`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Logowanie i monitorowanie systemu`

### `cat /var/log/secure`

- Category: `Logowanie i monitorowanie systemu`
- Risk: `unclassified`
- Tags: `troubleshooting`, `cat`
- Examples:
  - `cat /var/log/secure`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Logowanie i monitorowanie systemu`

### `ls /etc/logrotate.d/`

- Category: `Logowanie i monitorowanie systemu`
- Risk: `unclassified`
- Tags: `troubleshooting`, `ls`
- Examples:
  - `ls /etc/logrotate.d/`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Logowanie i monitorowanie systemu`

### `cat /var/log/cron`

- Category: `Logowanie i monitorowanie systemu`
- Risk: `unclassified`
- Tags: `troubleshooting`, `cat`
- Examples:
  - `cat /var/log/cron`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Logowanie i monitorowanie systemu`

### `cat /var/log/maillog`

- Category: `Logowanie i monitorowanie systemu`
- Risk: `unclassified`
- Tags: `troubleshooting`, `cat`
- Examples:
  - `cat /var/log/maillog`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Logowanie i monitorowanie systemu`

### `udit.log`

- Category: `Logowanie i monitorowanie systemu`
- Risk: `unclassified`
- Tags: `troubleshooting`, `udit.log`
- Examples:
  - `udit.log`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Logowanie i monitorowanie systemu`

### `grep 'Failed`

- Category: `Logowanie i monitorowanie systemu`
- Risk: `unclassified`
- Tags: `troubleshooting`, `grep`
- Examples:
  - `grep 'Failed`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Logowanie i monitorowanie systemu`

### `grep 'Accepted'`

- Category: `Logowanie i monitorowanie systemu`
- Risk: `unclassified`
- Tags: `troubleshooting`, `grep`
- Examples:
  - `grep 'Accepted'`
- Troubleshooting hint:
  - Quote patterns explicitly to avoid shell expansion when matching text.
- Provenance:
  - RHCSA section: `Logowanie i monitorowanie systemu`
```

## `runtime/knowledge/troubleshooting/zarzdzanie-procesami.md`

- size: 6250 bytes
- sha256: `152c55739440bf1044828cd7e32a24d55e721f087f371fcdf000d4e642f3cfa1`
- category: knowledge

```markdown
---
title: Zarz■dzanie procesami
topic: troubleshooting
source_section: Zarz■dzanie procesami
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [cat, ctrl+c, ctrl+d, ctrl+z, htop, jobs, linux, lsof, ps, pstree, rhcsa, top, troubleshooting, uptime, wait, zarzdzanie-procesami]
---

# Zarz■dzanie procesami

Imported RHCSA material for 16 commands. Primary command families: cat, ctrl+c, ctrl+d, ctrl+z, htop, jobs, lsof, ps.

## Tags

cat, ctrl+c, ctrl+d, ctrl+z, htop, jobs, linux, lsof, ps, pstree, rhcsa, top, troubleshooting, uptime, wait, zarzdzanie-procesami

## Examples

- `ps`
- `Ctrl+Z`
- `Ctrl+C`
- `Ctrl+D`
- `wait`
- `pstree`
- `lsof`
- `top`
- `htop`
- `u■ytkownika`

## Troubleshooting

- Validate command intent against current host state before applying changes in production.
- Prefer read-only inspection first, then narrow fixes to the subsystem that produced the symptom.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Zarz■dzanie procesami`

## Commands

### `ps`

- Category: `Zarz■dzanie procesami`
- Risk: `unclassified`
- Tags: `troubleshooting`, `ps`
- Examples:
  - `ps`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie procesami`

### `Ctrl+Z`

- Category: `Zarz■dzanie procesami`
- Risk: `unclassified`
- Tags: `troubleshooting`, `ctrl+z`
- Examples:
  - `Ctrl+Z`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie procesami`

### `Ctrl+C`

- Category: `Zarz■dzanie procesami`
- Risk: `unclassified`
- Tags: `troubleshooting`, `ctrl+c`
- Examples:
  - `Ctrl+C`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie procesami`

### `Ctrl+D`

- Category: `Zarz■dzanie procesami`
- Risk: `unclassified`
- Tags: `troubleshooting`, `ctrl+d`
- Examples:
  - `Ctrl+D`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie procesami`

### `wait`

- Category: `Zarz■dzanie procesami`
- Risk: `unclassified`
- Tags: `troubleshooting`, `wait`
- Examples:
  - `wait`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie procesami`

### `pstree`

- Category: `Zarz■dzanie procesami`
- Risk: `unclassified`
- Tags: `troubleshooting`, `pstree`
- Examples:
  - `pstree`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie procesami`

### `lsof`

- Category: `Zarz■dzanie procesami`
- Risk: `unclassified`
- Tags: `troubleshooting`, `lsof`
- Examples:
  - `lsof`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie procesami`

### `top`

- Category: `Zarz■dzanie procesami`
- Risk: `unclassified`
- Tags: `troubleshooting`, `top`
- Examples:
  - `top`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie procesami`

### `htop`

- Category: `Zarz■dzanie procesami`
- Risk: `unclassified`
- Tags: `troubleshooting`, `htop`
- Examples:
  - `htop`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie procesami`

### `u■ytkownika`

- Category: `Zarz■dzanie procesami`
- Risk: `unclassified`
- Tags: `troubleshooting`, `uytkownika`
- Examples:
  - `u■ytkownika`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie procesami`

### `uptime`

- Category: `Zarz■dzanie procesami`
- Risk: `unclassified`
- Tags: `troubleshooting`, `uptime`
- Examples:
  - `uptime`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie procesami`

### `jobs`

- Category: `Zarz■dzanie procesami`
- Risk: `unclassified`
- Tags: `troubleshooting`, `jobs`
- Examples:
  - `jobs`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie procesami`

### `cat /proc/PID/status`

- Category: `Zarz■dzanie procesami`
- Risk: `unclassified`
- Tags: `troubleshooting`, `cat`
- Examples:
  - `cat /proc/PID/status`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie procesami`

### `cat /proc/PID/maps`

- Category: `Zarz■dzanie procesami`
- Risk: `unclassified`
- Tags: `troubleshooting`, `cat`
- Examples:
  - `cat /proc/PID/maps`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie procesami`

### `cat /proc/loadavg`

- Category: `Zarz■dzanie procesami`
- Risk: `unclassified`
- Tags: `troubleshooting`, `cat`
- Examples:
  - `cat /proc/loadavg`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie procesami`

### `cat /proc/meminfo`

- Category: `Zarz■dzanie procesami`
- Risk: `unclassified`
- Tags: `troubleshooting`, `cat`
- Examples:
  - `cat /proc/meminfo`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie procesami`
```

## `runtime/knowledge/users/README.md`

- size: 398 bytes
- sha256: `dd521b7f7a4da905c14814ffa4884519c7bd373de2808a538e5ad82498aca364`
- category: knowledge

```markdown
# Users

User, group, identity, and account lifecycle operations.

## Modules

- `users/zarzdzanie-grupami.md`: 3 imported commands from `Zarz■dzanie grupami`
- `users/zarzdzanie-uytkownikami.md`: 46 imported commands from `Zarz■dzanie u■ytkownikami`

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
```

## `runtime/knowledge/users/zarzdzanie-grupami.md`

- size: 1737 bytes
- sha256: `4ab3e9e0eeea2b2099f33862557dd003696bc7c781688fa0ef1a3040bba5c7b3`
- category: knowledge

```markdown
---
title: Zarz■dzanie grupami
topic: users
source_section: Zarz■dzanie grupami
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [group, linux, rhcsa, usermod, users, zarzdzanie-grupami]
---

# Zarz■dzanie grupami

Imported RHCSA material for 3 commands. Primary command families: group, usermod.

## Tags

group, linux, rhcsa, usermod, users, zarzdzanie-grupami

## Examples

- `group`
- `usermod -aG wheel`
- `usermod -aG docker`

## Troubleshooting

- Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Zarz■dzanie grupami`

## Commands

### `group`

- Category: `Zarz■dzanie grupami`
- Risk: `unclassified`
- Tags: `users`, `group`
- Examples:
  - `group`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie grupami`

### `usermod -aG wheel`

- Category: `Zarz■dzanie grupami`
- Risk: `unclassified`
- Tags: `users`, `usermod`
- Examples:
  - `usermod -aG wheel`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie grupami`

### `usermod -aG docker`

- Category: `Zarz■dzanie grupami`
- Risk: `unclassified`
- Tags: `users`, `usermod`
- Examples:
  - `usermod -aG docker`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie grupami`
```

## `runtime/knowledge/users/zarzdzanie-uytkownikami.md`

- size: 16125 bytes
- sha256: `c3474eb64d5f661160cb9aed5b2f0b9449d9a5f4cdb76fe0f792616637c086d0`
- category: knowledge

```markdown
---
title: Zarz■dzanie u■ytkownikami
topic: users
source_section: Zarz■dzanie u■ytkownikami
source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf
generated_from: knowledge/canonical/rhcsa_commands.json
tags: [cat, dniach, grpck, id, last, lastb, lastlog, linux, lslogins, pwck, rhcsa, user, useradd, usermod, users, vigr, vipw, visudo, w, who, whoami, zalogowanego, zarzdzanie-uytkownikami]
---

# Zarz■dzanie u■ytkownikami

Imported RHCSA material for 46 commands. Primary command families: cat, dniach, grpck, id, last, lastb, lastlog, lslogins.

## Tags

cat, dniach, grpck, id, last, lastb, lastlog, linux, lslogins, pwck, rhcsa, user, useradd, usermod, users, vigr, vipw, visudo, w, who, whoami, zalogowanego, zarzdzanie-uytkownikami

## Examples

- `useradd username`
- `useradd -m username`
- `useradd -m -s`
- `useradd -u 1500 user`
- `useradd -g group`
- `user`
- `useradd -G g1,g2`
- `useradd -d`
- `useradd -c 'Imi■`
- `useradd -e`

## Troubleshooting

- Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.

## Provenance

- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`
- Canonical import: `knowledge/canonical/rhcsa_commands.json`
- Source section: `Zarz■dzanie u■ytkownikami`

## Commands

### `useradd username`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `useradd`
- Examples:
  - `useradd username`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `useradd -m username`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `useradd`
- Examples:
  - `useradd -m username`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `useradd -m -s`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `useradd`
- Examples:
  - `useradd -m -s`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `useradd -u 1500 user`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `useradd`
- Examples:
  - `useradd -u 1500 user`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `useradd -g group`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `useradd`
- Examples:
  - `useradd -g group`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `user`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `user`
- Examples:
  - `user`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `useradd -G g1,g2`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `useradd`
- Examples:
  - `useradd -G g1,g2`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `useradd -d`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `useradd`
- Examples:
  - `useradd -d`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `useradd -c 'Imi■`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `useradd`
- Examples:
  - `useradd -c 'Imi■`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `useradd -e`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `useradd`
- Examples:
  - `useradd -e`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `id`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `id`
- Examples:
  - `id`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `useradd -f 30 user`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `useradd`
- Examples:
  - `useradd -f 30 user`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `whoami`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `whoami`
- Examples:
  - `whoami`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `dniach`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `dniach`
- Examples:
  - `dniach`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `useradd -r sysuser`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `useradd`
- Examples:
  - `useradd -r sysuser`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `who`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `who`
- Examples:
  - `who`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `useradd -M user`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `useradd`
- Examples:
  - `useradd -M user`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `w`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `w`
- Examples:
  - `w`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `useradd -N user`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `useradd`
- Examples:
  - `useradd -N user`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `last`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `last`
- Examples:
  - `last`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `usermod -l newname`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `usermod`
- Examples:
  - `usermod -l newname`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `lastlog`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `lastlog`
- Examples:
  - `lastlog`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `usermod -d /new/home`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `usermod`
- Examples:
  - `usermod -d /new/home`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `lastb`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `lastb`
- Examples:
  - `lastb`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `usermod -s /bin/zsh`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `usermod`
- Examples:
  - `usermod -s /bin/zsh`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `usermod -u 1600 user`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `usermod`
- Examples:
  - `usermod -u 1600 user`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `usermod -g group`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `usermod`
- Examples:
  - `usermod -g group`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `usermod -G g1,g2`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `usermod`
- Examples:
  - `usermod -G g1,g2`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `usermod -aG group`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `usermod`
- Examples:
  - `usermod -aG group`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `usermod -c 'Nowy`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `usermod`
- Examples:
  - `usermod -c 'Nowy`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `usermod -e`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `usermod`
- Examples:
  - `usermod -e`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `usermod -L user`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `usermod`
- Examples:
  - `usermod -L user`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `visudo`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `visudo`
- Examples:
  - `visudo`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `usermod -U user`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `usermod`
- Examples:
  - `usermod -U user`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `cat /etc/passwd`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `cat`
- Examples:
  - `cat /etc/passwd`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `usermod -e '' user`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `usermod`
- Examples:
  - `usermod -e '' user`
- Troubleshooting hint:
  - Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `cat /etc/shadow`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `cat`
- Examples:
  - `cat /etc/shadow`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `trwa■e)`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `trwae`
- Examples:
  - `trwa■e)`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `cat /etc/group`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `cat`
- Examples:
  - `cat /etc/group`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `cat /etc/gshadow`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `cat`
- Examples:
  - `cat /etc/gshadow`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `zalogowanego`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `zalogowanego`
- Examples:
  - `zalogowanego`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `vipw`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `vipw`
- Examples:
  - `vipw`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `vigr`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `vigr`
- Examples:
  - `vigr`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `pwck`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `pwck`
- Examples:
  - `pwck`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `grpck`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `grpck`
- Examples:
  - `grpck`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`

### `lslogins`

- Category: `Zarz■dzanie u■ytkownikami`
- Risk: `unclassified`
- Tags: `users`, `lslogins`
- Examples:
  - `lslogins`
- Troubleshooting hint:
  - Validate command intent against current host state before applying changes in production.
- Provenance:
  - RHCSA section: `Zarz■dzanie u■ytkownikami`
```

## `runtime/knowledge/validator/__init__.py`

- size: 46 bytes
- sha256: `e84eff1926853a1d5945bd846668fa4f066828346c705e7fd0a10d7e3112c6a0`
- category: knowledge

```python
"""AOIA knowledge pack validation package."""
```

## `runtime/knowledge/validator/validation_report.md`

- size: 773 bytes
- sha256: `7f8800f37b822121f9a6d840c26e81abc891ab471bfa90923080d6b296c63ea9`
- category: knowledge

```markdown
# AOIA Knowledge Validator Report

## Scope

This validator checks local JSON knowledge pack entries only. It does not
perform retrieval, ranking, routing, AI integration, embeddings, or database
operations.

## Implemented Checks

- invalid JSON detection
- invalid filename detection
- missing required field detection
- unknown top-level field detection
- category validation
- tag validation
- risk-level validation
- OS and shell validation
- malformed example validation
- duplicate command detection

## CLI

```text
python validator.py knowledge/
```

## Runtime Behavior

- deterministic file ordering
- fail-fast on the first invalid file or duplicate command
- stdout-only result reporting
- no file mutation
- no external services
- no third-party dependencies
```

## `runtime/knowledge/validator/validation_rules.py`

- size: 1353 bytes
- sha256: `e213a89ddf183561d3c0da5130573109519ef2b8734c9a292f37c85b7d7952ab`
- category: knowledge

```python
"""Deterministic AOIA knowledge pack validation rules."""

from __future__ import annotations

import re

REQUIRED_FIELDS = (
    "id",
    "command",
    "description",
    "category",
    "tags",
    "risk",
    "os",
    "shell",
    "examples",
)

OPTIONAL_FIELDS = (
    "notes",
    "related_commands",
)

ALLOWED_FIELDS = frozenset(REQUIRED_FIELDS + OPTIONAL_FIELDS)

ALLOWED_CATEGORIES = frozenset(
    (
        "archive",
        "diagnostic",
        "filesystem",
        "network",
        "package",
        "process",
        "security",
        "service",
        "system",
        "user",
    )
)

ALLOWED_RISKS = frozenset(("low", "medium", "high", "critical"))

ALLOWED_OS = frozenset(("linux", "rhel", "ubuntu", "debian", "fedora", "macos"))

ALLOWED_SHELLS = frozenset(("bash", "sh", "zsh"))

ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FILENAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.json$")
TAG_RE = ID_RE
RELATED_COMMAND_RE = re.compile(r"^[a-z0-9._+-]+$")


def is_valid_identifier(value: str) -> bool:
    return bool(ID_RE.fullmatch(value))


def is_valid_filename(value: str) -> bool:
    return bool(FILENAME_RE.fullmatch(value))


def is_valid_tag(value: str) -> bool:
    return bool(TAG_RE.fullmatch(value))


def is_valid_related_command(value: str) -> bool:
    return bool(RELATED_COMMAND_RE.fullmatch(value))
```

## `runtime/knowledge/validator/validator.py`

- size: 8047 bytes
- sha256: `0882c8c7078065cf5b2113226e00871bd4abe3364f1d6d1844fe57259fe536bf`
- category: knowledge

```python
"""Deterministic local validator for AOIA knowledge packs."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from .validation_rules import (
        ALLOWED_CATEGORIES,
        ALLOWED_FIELDS,
        ALLOWED_OS,
        ALLOWED_RISKS,
        ALLOWED_SHELLS,
        REQUIRED_FIELDS,
        is_valid_filename,
        is_valid_identifier,
        is_valid_related_command,
        is_valid_tag,
    )
except ImportError:  # Allows direct execution: python knowledge/validator/validator.py knowledge/
    from validation_rules import (  # type: ignore
        ALLOWED_CATEGORIES,
        ALLOWED_FIELDS,
        ALLOWED_OS,
        ALLOWED_RISKS,
        ALLOWED_SHELLS,
        REQUIRED_FIELDS,
        is_valid_filename,
        is_valid_identifier,
        is_valid_related_command,
        is_valid_tag,
    )


@dataclass(frozen=True)
class ValidationReport:
    ok: bool
    checked_files: int
    message: str


def discover_entry_files(root: Path) -> list[Path]:
    """Return knowledge entry files in stable order."""
    examples_dir = root / "examples"
    search_root = examples_dir if examples_dir.is_dir() else root
    return sorted(path for path in search_root.rglob("*.json") if path.is_file())


def validate_path(root: str | Path) -> ValidationReport:
    root_path = Path(root)
    if not root_path.exists():
        return ValidationReport(False, 0, f"root does not exist: {root_path}")
    if not root_path.is_dir():
        return ValidationReport(False, 0, f"root is not a directory: {root_path}")

    files = discover_entry_files(root_path)
    if not files:
        return ValidationReport(False, 0, f"no knowledge entry files found: {root_path}")

    seen_commands: dict[str, Path] = {}
    checked = 0

    for path in files:
        checked += 1
        file_error = validate_filename(path)
        if file_error:
            return ValidationReport(False, checked, f"{path}: {file_error}")

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return ValidationReport(False, checked, f"{path}: invalid JSON: {exc.msg}")

        entry_error = validate_entry(data)
        if entry_error:
            return ValidationReport(False, checked, f"{path}: {entry_error}")

        command = data["command"]
        if command in seen_commands:
            return ValidationReport(
                False,
                checked,
                f"{path}: duplicate command '{command}' also defined in {seen_commands[command]}",
            )
        seen_commands[command] = path

    return ValidationReport(True, checked, f"validated {checked} knowledge entry file(s)")


def validate_filename(path: Path) -> str | None:
    if not is_valid_filename(path.name):
        return "invalid filename; expected lowercase kebab-case .json"
    return None


def validate_entry(data: Any) -> str | None:
    if not isinstance(data, dict):
        return "entry must be a JSON object"

    unknown_fields = sorted(set(data) - ALLOWED_FIELDS)
    if unknown_fields:
        return f"unknown field(s): {', '.join(unknown_fields)}"

    for field in REQUIRED_FIELDS:
        if field not in data:
            return f"missing required field: {field}"

    scalar_error = validate_scalar_fields(data)
    if scalar_error:
        return scalar_error

    list_error = validate_list_fields(data)
    if list_error:
        return list_error

    examples_error = validate_examples(data["examples"])
    if examples_error:
        return examples_error

    optional_error = validate_optional_fields(data)
    if optional_error:
        return optional_error

    return None


def validate_scalar_fields(data: dict[str, Any]) -> str | None:
    if not isinstance(data["id"], str) or not is_valid_identifier(data["id"]):
        return "invalid id; expected lowercase kebab-case"
    if not isinstance(data["command"], str) or not data["command"].strip():
        return "invalid command; expected non-empty string"
    if not isinstance(data["description"], str) or not data["description"].strip():
        return "invalid description; expected non-empty string"
    if len(data["description"]) > 240:
        return "invalid description; maximum length is 240"
    if data["category"] not in ALLOWED_CATEGORIES:
        return f"invalid category: {data['category']}"
    if data["risk"] not in ALLOWED_RISKS:
        return f"invalid risk: {data['risk']}"
    return None


def validate_list_fields(data: dict[str, Any]) -> str | None:
    tag_error = validate_string_list("tags", data["tags"])
    if tag_error:
        return tag_error
    for tag in data["tags"]:
        if not is_valid_tag(tag):
            return f"invalid tag: {tag}"

    os_error = validate_string_list("os", data["os"])
    if os_error:
        return os_error
    for os_name in data["os"]:
        if os_name not in ALLOWED_OS:
            return f"invalid os: {os_name}"

    shell_error = validate_string_list("shell", data["shell"])
    if shell_error:
        return shell_error
    for shell_name in data["shell"]:
        if shell_name not in ALLOWED_SHELLS:
            return f"invalid shell: {shell_name}"

    return None


def validate_string_list(name: str, value: Any) -> str | None:
    if not isinstance(value, list) or not value:
        return f"invalid {name}; expected non-empty array"
    if any(not isinstance(item, str) or not item for item in value):
        return f"invalid {name}; expected non-empty strings"
    if len(set(value)) != len(value):
        return f"invalid {name}; duplicate values are not allowed"
    return None


def validate_examples(value: Any) -> str | None:
    if not isinstance(value, list) or not value:
        return "invalid examples; expected non-empty array"
    for index, example in enumerate(value):
        if not isinstance(example, dict):
            return f"invalid examples[{index}]; expected object"
        unknown_fields = sorted(set(example) - {"input", "expected_effect"})
        if unknown_fields:
            return f"invalid examples[{index}]; unknown field(s): {', '.join(unknown_fields)}"
        if "input" not in example:
            return f"invalid examples[{index}]; missing input"
        if "expected_effect" not in example:
            return f"invalid examples[{index}]; missing expected_effect"
        if not isinstance(example["input"], str) or not example["input"].strip():
            return f"invalid examples[{index}].input; expected non-empty string"
        effect = example["expected_effect"]
        if not isinstance(effect, str) or not effect.strip():
            return f"invalid examples[{index}].expected_effect; expected non-empty string"
        if len(effect) > 240:
            return f"invalid examples[{index}].expected_effect; maximum length is 240"
    return None


def validate_optional_fields(data: dict[str, Any]) -> str | None:
    if "notes" in data:
        if not isinstance(data["notes"], str):
            return "invalid notes; expected string"
        if len(data["notes"]) > 500:
            return "invalid notes; maximum length is 500"
    if "related_commands" in data:
        error = validate_string_list("related_commands", data["related_commands"])
        if error:
            return error
        for command in data["related_commands"]:
            if not is_valid_related_command(command):
                return f"invalid related command: {command}"
    return None


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: python validator.py knowledge/")
        return 2

    report = validate_path(args[0])
    status = "OK" if report.ok else "ERROR"
    print(f"{status}: {report.message}")
    print(f"checked_files={report.checked_files}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

