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
