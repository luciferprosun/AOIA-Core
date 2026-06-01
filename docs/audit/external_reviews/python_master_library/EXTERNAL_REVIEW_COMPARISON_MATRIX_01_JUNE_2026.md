# External Review Comparison Matrix — Python Master Library — 01 June 2026

Metadata:
- project: AIOA Whitehat / AOIA-Core
- scope: Python Master Library external review consolidation
- reviews compared: Kimi, DeepSeek
- review status: external_model_review_unverified
- canonical: false
- runtime_integration: false

| topic | Kimi recommendation | DeepSeek recommendation | agreement level | accepted decision | notes |
| --- | --- | --- | --- | --- | --- |
| Python as first programming language | Python is the correct first programming-language library because it is central to Linux automation, readable, and has a manageable dangerous surface. | Python direction is technically sound if kept reference-only and reviewed before promotion. | full_agreement | Accept Python as the first programming-language knowledge library. | The accepted scope is advisory/reference only. |
| imported PDFs as unverified sources | Treat the PDF as useful but incomplete and not canonical. Cross-check all claims against official docs. | Treat the PDF as `imported_reference_unverified`; do not promote without official docs and tests. | full_agreement | Imported PDFs remain unverified source material only. | No PDF-derived record becomes truth by import. |
| schema-first development | Schema and validation suite should come before corpus expansion. | Harden schema, define enums, and validate records before expansion. | full_agreement | Schema/enums/tests are required before new corpus work. | H15 began this path. |
| JSONL validation | Validate parseability, required fields, enum values, IDs, version scopes, and promotion status. | Validate JSONL parseability, required keys, enums, duplicate IDs, execution policy, and promotion gates. | full_agreement | Keep JSONL validation mandatory. | No examples are executed by validation. |
| dangerous built-ins classification | Classify eval, exec, compile, open, input, import, subprocess, os.system, pickle, rmtree, mktemp, pip usage. | Classify eval, exec, compile, import, subprocess, os.system, pickle, rmtree, mktemp, requests, pip usage. | full_agreement | Maintain a dangerous API index and high/critical risk classification. | Naming and exact severity may be refined by human review. |
| dangerous pattern tests | Add tests for shell injection, eval/exec, pickle, destructive deletes, secrets, path traversal, pip, and no execution. | Add static dangerous-pattern tests and reject unsafe corrected patterns. | full_agreement | Static dangerous-pattern tests are required. | Tests should scan strings, not run examples. |
| no runtime integration | Runtime and Memory Hats integration must wait for a strict future gate. | Do not integrate with Memory Hats, runtime executor, router, or provider logic. | full_agreement | Runtime integration is explicitly postponed. | H17 is documentation/planning only. |
| no automatic promotion | No provider/model output or imported source may be promoted without review. | No automatic promotion; promotion requires human review and official docs checks. | full_agreement | No records are promoted during H17. | Promotion lifecycle remains locked down. |
| official docs cross-check | Build a cross-check plan against docs.python.org and log discrepancies. | Require official documentation references before `official_docs_checked` or promoted states. | full_agreement | H18 should create official docs cross-check workflow. | No web scraping or copied official docs in H18. |
| first records to build | Suggested first 25 draft topics, starting with subprocess, eval, exec, file overwrite, rmtree, pickle, pip, secrets, temp files, path traversal. | Do not expand corpus beyond current source intake until schema and tests are stable. | partial_agreement | Keep Kimi's first-record list as future candidate topics only. | DeepSeek is stricter on delaying corpus expansion. |
| Linux/RHCSA subprocess bridge | Python should act as glue and must not bypass RHCSA/Linux command safety. | Python automation must follow shell=False/list-args, dry-run, no sudo automation, and no command execution. | full_agreement | Accept Linux/RHCSA bridge principles as future advisory design input. | No runtime bridge is implemented in H17. |
| deduplication | Implied through source registry, IDs, taxonomy, and review workflow. | Required through unique IDs and schema/test controls. | partial_agreement | Add deduplication to future source registry and JSONL validation. | H17 does not implement new dedup logic. |
| integration gate | Proposed thresholds, tests, rollback, feature flag, audit, and two human reviewers. | Proposed schema freeze, tests, rollback, feature flag off, promotion gate, human safety review. | partial_agreement | Accept the gate concept, but do not bind H17 to Kimi's 100-record threshold. | Thresholds require human governance decision. |
| what to delay | Delay Level 6+ security/async/metaprogramming, network domains, runtime integration, and execution policy allowing execution. | Delay runtime integration, corpus expansion, promotion scripts, sandbox execution, and any execution of examples. | full_agreement | Delay advanced domains and runtime coupling. | Focus next on official docs cross-check planning. |
| what must never be executed | Do not execute examples during validation; do not allow execution policy without audit. | Do not execute any knowledge-library examples; high-risk items should be `never_execute` or reference-only until reviewed. | full_agreement | Examples remain inert strings. | H17 adds no executable examples. |
| what should happen next | Merge schema/reference docs/tests, then cross-check against official docs and later add draft records. | H15-style schema hardening and tests first; then official docs cross-check before promotion. | full_agreement | Next safe task: H18 official docs cross-check plan. | H18 should create checklists/templates, not scrape docs. |

## Disagreements And Deferred Decisions

- Kimi proposed enum names such as `pending_review`, `advisory_only`, `draft`, and `allow`; DeepSeek/H15 uses stricter enum names such as `imported_unverified`, `reference_only_no_execution`, `advisory_only_no_execution`, `never_execute`, and `not_promoted`. Accepted decision: keep H15 enum vocabulary for now.
- Kimi proposed a 100-reviewed-record threshold before integration; DeepSeek emphasized strict controls without making that exact number binding. Accepted decision: keep the threshold as a future governance proposal, not an H17 requirement.
- Kimi proposed first 25 records to build; DeepSeek warned against expansion before schema and tests are stable. Accepted decision: record the first 25 topics as future candidates only.
