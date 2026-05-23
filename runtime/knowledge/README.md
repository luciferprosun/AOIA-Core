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
