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
