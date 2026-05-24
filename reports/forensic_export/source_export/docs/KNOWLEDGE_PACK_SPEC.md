# AOIA Knowledge Pack Specification

This document defines the canonical local JSON structure for AOIA knowledge
packs. It does not define retrieval, embeddings, ranking, or runtime mutation.

## Purpose

Knowledge packs are static local JSON files that describe operational command
knowledge in a deterministic format. They are reference material only.

## Directory Layout

```text
knowledge/
├── schema/
│   └── command.schema.json
└── examples/
    └── *.json
```

## Canonical Entry Type

The first supported entry type is a command entry. Each command entry describes
one command or one narrow command family.

Required fields:

- `id`: stable lowercase identifier.
- `command`: command name or command pattern.
- `description`: short operational description.
- `category`: one canonical category.
- `tags`: deterministic lowercase tags.
- `risk`: one canonical risk level.
- `os`: supported operating system labels.
- `shell`: supported shell labels.
- `examples`: one or more deterministic usage examples.

Optional fields:

- `notes`: short implementation notes.
- `related_commands`: deterministic list of related command names.

## Risk Levels

- `low`: read-only or harmless inspection command.
- `medium`: changes local state but is normally reversible.
- `high`: can interrupt services, modify permissions, or affect many files.
- `critical`: can delete data, expose secrets, disable access, or damage system
  availability.

## Categories

Initial canonical categories:

- `filesystem`
- `process`
- `network`
- `package`
- `service`
- `user`
- `security`
- `archive`
- `diagnostic`
- `system`

New categories require documentation before use.

## Determinism Rules

- JSON object keys should be written in schema order.
- Arrays must be stable and manually sorted where practical.
- Identifiers must not include timestamps or generated random values.
- Entries must not depend on network state.
- Files must not be modified by runtime routing code.

## Out of Scope

- AI retrieval
- embeddings
- vector databases
- semantic search
- autonomous routing
- live telemetry
- runtime learning
