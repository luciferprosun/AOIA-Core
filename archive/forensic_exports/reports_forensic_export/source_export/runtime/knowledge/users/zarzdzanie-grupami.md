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
