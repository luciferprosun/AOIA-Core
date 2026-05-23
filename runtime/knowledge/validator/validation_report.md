# AOIA Knowledge Validator Report

## Scope

This validator checks local JSON knowledge pack entries only. It does not
perform retrieval, ranking, routing, AI integration, embeddings, or database
operations.

## Implemented Checks

- invalid JSON detection
- invalid filename detection
- missing required field detection
- unknown top-level field detection
- category validation
- tag validation
- risk-level validation
- OS and shell validation
- malformed example validation
- duplicate command detection

## CLI

```text
python validator.py knowledge/
```

## Runtime Behavior

- deterministic file ordering
- fail-fast on the first invalid file or duplicate command
- stdout-only result reporting
- no file mutation
- no external services
- no third-party dependencies
