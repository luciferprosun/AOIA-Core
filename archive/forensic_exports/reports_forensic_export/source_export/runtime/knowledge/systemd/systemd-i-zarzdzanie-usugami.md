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
