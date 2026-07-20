# AOIA-Core Development Prototype

AOIA-Core is a local-first, human-controlled epistemic control system. This
repository is a development prototype for inspecting provider suggestions,
preserving provenance, routing knowledge queries, and presenting evidence to a
human before any separately controlled action.

Current status: development prototype. The validated repository baseline is
3,255 passed, 4 skipped, 0 failures, and 0 errors. The current UNIX evidence
freeze is `aoia-unix-unit-1a-r1`.

## What AOIA-Core does

- keeps provider output untrusted and critic output metadata-only;
- builds inert `ActionProposal` and `ArtifactPreview` review objects;
- protects controlled writes with the separate canonical human barrier;
- records append-only Durable Audit Ledger evidence;
- provides Knowledge Foundation provenance and validation schemas;
- exposes Linux, Bash, Python, and UNIX knowledge Hats;
- performs deterministic local ingestion, lexical retrieval, and no-dispatch routing;
- renders and verifies an offline static UNIX review prototype;
- retains deterministic validation, freeze, sponsor, and architect-handoff evidence.

## What AOIA-Core does not do

AOIA-Core does not grant autonomous execution authority. A route, retrieval
result, score, critic verdict, preview, freeze, manifest, or passing test is not
approval. The offline prototype does not call providers or the network, start a
server, open a browser, execute a command, write controlled artifacts, invoke
Git, install packages, or connect to the human authorization barrier.

Some controlled execution and write modules are retained for architectural and
compatibility review. They remain bounded by their existing exact human-gated
contracts and are not reachable through the developer entrypoints documented
below.

## Authority model

Provider output is never authority. Critic output, knowledge records, Hat
descriptors, route proposals, retrieval results, scores, previews, audit
records, and generated evidence are metadata only. Only the existing separate
canonical human barrier may authorize its exact controlled path. Packaging and
console scripts add no authority.

See [AUTHORITY_SCOPE.md](AUTHORITY_SCOPE.md) and
[docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) for the governing boundary.

## Implemented components

- Provider Runtime, Selector, and Critic
- Artifact Preview, controlled write, and canonical human-gate bindings
- ActionProposal and Durable Audit Ledger
- static capability-boundary and adversarial suites
- Knowledge Foundation schemas and provenance
- Linux/RHCSA retrieval compatibility
- Bash safety inspection
- Python knowledge Hat data and read-only loader
- UNIX corpus, retrieval adapter, inert Hat, deterministic routing, and visible prototype
- deterministic UNIX validation/freeze and architect-handoff manifests

## Knowledge Hats

- **Linux Hat:** local Linux/RHCSA library and deterministic retrieval compatibility.
- **Bash Hat:** command parsing and pre-execution safety classification; it does not execute shell text.
- **Python Hat:** curated Python knowledge, validation records, and a read-only loader.
- **UNIX Hat:** capability-empty descriptor, deterministic no-dispatch routing, explicit read-only retrieval, and offline review rendering.

All Hat results are non-authoritative metadata.

## Repository structure

- `runtime/` — production runtime, safety boundaries, Hats, retrieval, routing, and stable developer entrypoints
- `tests/` — production, compatibility, authority, adversarial, and static-boundary tests
- `knowledge/` and `corpus/` — retained Hat libraries and approved/source knowledge material
- `data/` — deterministic corpus, index, routing, prototype, freeze, sponsor, and handoff evidence
- `docs/` — architecture, threat model, governance, reviewer material, and historical audit records
- `archive/` — retained forensic and historical material; never runtime authority
- `web/` and `tui/` — protected compatibility surfaces, not required by the default offline path

## System requirements

- Python 3.12 or newer
- Git only for cloning; the documented runtime commands do not invoke Git
- no provider credentials, network service, browser, Node.js, or external Python package for the default offline path

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

## Installation

From the repository root with the environment active:

```bash
PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 python -m pip install --no-deps --no-build-isolation -e .
```

`pyproject.toml` is the canonical dependency and entrypoint declaration. The
supported default path uses only the standard library. `runtime/requirements.txt`
is a compatibility pointer and must not be used as a second dependency source.

## Smoke test

```bash
aoia-smoke-test --repository-root .
```

This imports the core and all four Hats, confirms the stable entrypoints, and
verifies the current architect-handoff manifest without executing actions.

## Knowledge Module control plane

The provider-independent control plane lists logical modules and concrete
read-only instances without activating either:

```bash
aoia-knowledge-hub list-modules --repository-root . --format json
aoia-knowledge-hub list-instances --repository-root . --module de-law-federal-1a --format json
aoia-knowledge-hub query --repository-root . --question "Explain evidence and authority." --format json
```

The zero-module query is valid and returns `NO_KNOWLEDGE_MODULE_SELECTED`.
Selections are explicit and request-only; provider selection remains separate.

## Full test suite

```bash
CI=1 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p 'test*.py' -q < /dev/null
```

The verified baseline before this documentation/packaging step is 3,255 passed,
4 skipped, 0 failures, and 0 errors. A passing suite is evidence, not authority.

## Offline prototype

Choose a new output directory whose parent already exists:

```bash
aoia-offline-prototype --repository-root . --output-root /tmp/aoia-offline-prototype-1a
```

The command creates deterministic static HTML and text only in that explicit
new directory. It starts no server and opens no browser. Open the generated
`index.html` manually if desired.

## Artifact verification

```bash
aoia-verify-artifacts --repository-root .
```

This read-only command verifies the architect handoff manifest, approved UNIX
corpus, retrieval index, Hat descriptor, routing policy, visible prototype,
current `aoia-unix-unit-1a-r1` freeze, and sponsor bundle. It fails closed and
does not repair or regenerate artifacts.

## Security and authority boundaries

The repository contains tightly controlled process, write, provider, browser,
package, patch, and Git-related modules because the complete architecture and
their negative tests are part of the handoff. Their presence is not a grant of
capability to the stable offline entrypoints. Do not bypass the human barrier,
reuse metadata as approval, broaden subprocess environments, or add automatic
fallback, retry, streaming, provider, or network behavior.

Report security concerns according to [CONTRIBUTING.md](CONTRIBUTING.md) while
preserving sensitive values.

## Current limitations

- This is not production 1.0 and is not a complete terminal security product.
- The UNIX corpus contains 13 canonical normalized records from one approved extracted source; it is not all UNIX knowledge.
- UNIX retrieval is local and lexical, without remote embeddings or provider reasoning.
- Scores and deterministic routes may be incomplete or wrong and remain metadata.
- The prototype does not administer a real machine and executes no command.
- Human review remains required before consequential use.
- The current freeze is a local dirty-worktree evidence record, not a Git release.

## Architect and programmer handoff

Start with [START_HERE_ARCHITECT.md](START_HERE_ARCHITECT.md), then inspect
`data/architect_handoff_manifest_1a.json`, `CURRENT_STATE.md`, and the tests
protecting the subsystem you plan to change. Retained generated artifacts are
intentional: they allow immediate offline inspection and deterministic
verification without the original workstation.

## License and contributions

AOIA-Core is released under the [MIT License](LICENSE). Contributions should
follow [CONTRIBUTING.md](CONTRIBUTING.md): keep changes small, evidence-backed,
and explicit about authority and compatibility effects.
