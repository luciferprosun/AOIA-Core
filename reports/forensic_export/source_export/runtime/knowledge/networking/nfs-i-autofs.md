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
