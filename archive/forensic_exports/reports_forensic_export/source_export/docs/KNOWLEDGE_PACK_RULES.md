# AOIA Knowledge Pack Rules

Knowledge packs are local, static, JSON-only reference files. They support
future deterministic routing work but do not implement routing.

## Naming Rules

- Schema files use `*.schema.json`.
- Example files use lowercase kebab-case names.
- Entry `id` values use lowercase kebab-case.
- Tags use lowercase kebab-case.
- Categories and risk levels use lowercase names from the canonical lists.

## Validation Rules

- Every entry must validate against `knowledge/schema/command.schema.json`.
- Unknown top-level fields are not allowed.
- Required fields must be present.
- `tags`, `os`, `shell`, and `examples` must be non-empty arrays.
- `risk` must be one of: `low`, `medium`, `high`, `critical`.
- `category` must be one of the canonical categories in the spec.
- `examples[].expected_effect` must describe the expected result without
  promising external state.

## Risk Classification Rules

- Use `low` for read-only inspection commands.
- Use `medium` for local changes with clear recovery paths.
- Use `high` for service-impacting or broad filesystem changes.
- Use `critical` for destructive, secret-exposing, or access-breaking commands.
- When uncertain, choose the higher risk level.

## Tagging Rules

- Tags should describe function, not intent speculation.
- Use a small number of precise tags.
- Do not encode user names, dates, hostnames, or environment-specific data.
- Prefer stable tags such as `read-only`, `permissions`, `service-status`,
  `network-inspection`, or `package-management`.

## Mutation Rules

- Runtime code must not rewrite knowledge pack files.
- Generated knowledge pack updates must be reviewed before use.
- Knowledge pack files are source artifacts, not cache files.

## Dependency Rules

- Knowledge packs are JSON only.
- No database engine is required.
- No vector store is allowed.
- No embedding model is required.
- No external API is required.
