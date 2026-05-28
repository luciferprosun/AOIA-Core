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
