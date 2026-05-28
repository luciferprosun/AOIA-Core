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
