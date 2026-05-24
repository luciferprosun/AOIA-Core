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
