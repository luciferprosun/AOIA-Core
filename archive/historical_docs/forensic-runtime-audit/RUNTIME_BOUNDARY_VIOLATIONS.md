# Runtime Boundary Violations

Status: forensic mapping only. No runtime changes made.

## 1. `runtime/main.py`

Severity: **CRITICAL**

Violations:

- too many responsibilities in one coordinator
- builds prompts and also owns runtime policy
- performs local routing, deterministic knowledge routing, legacy knowledge routing, and orchestrator dispatch
- owns unknown-response policy and logging policy
- mixes runtime state assembly with model-facing prompt construction

Relevant lines:

- imports and runtime assembly: [`runtime/main.py:24-36`](../../runtime/main.py#L24-L36)
- runtime state / prompt payload: [`runtime/main.py:167-227`](../../runtime/main.py#L167-L227)
- route selection and model loop: [`runtime/main.py:306-420`](../../runtime/main.py#L306-L420)
- knowledge routing bridge: [`runtime/main.py:698-760`](../../runtime/main.py#L698-L760)
- reasoning logging: [`runtime/main.py:915-918`](../../runtime/main.py#L915-L918)

## 2. `runtime/tools/memory.py`

Severity: **CRITICAL**

Violations:

- state, logs, evidence, reasoning, and Obsidian projection share one persistence layer
- runtime state and notebook projection are not separated
- append-only assumptions are not enforced by type boundary
- live mutable state is written back to disk on many different code paths

Relevant lines:

- path creation: [`runtime/tools/memory.py:50-121`](../../runtime/tools/memory.py#L50-L121)
- state file + log file setup: [`runtime/tools/memory.py:124-145`](../../runtime/tools/memory.py#L124-L145)
- evidence/reasoning/history methods: [`runtime/tools/memory.py:153-181`](../../runtime/tools/memory.py#L153-L181)
- command/result/state mutation: [`runtime/tools/memory.py:197-230`](../../runtime/tools/memory.py#L197-L230)
- vault note projection: [`runtime/tools/memory.py:232-260`](../../runtime/tools/memory.py#L232-L260)

## 3. `runtime/tools/executor.py`

Severity: **HIGH**

Violations:

- execution registry, approval UI, execution dispatch, and memory recording are coupled
- result recording writes to command logs and memory in the same method
- browser actions trigger browser-specific logs inside the same recorder

Relevant lines:

- tool registry: [`runtime/tools/executor.py:92-116`](../../runtime/tools/executor.py#L92-L116)
- approval gate: [`runtime/tools/executor.py:69-90`](../../runtime/tools/executor.py#L69-L90)
- execution recording: [`runtime/tools/executor.py:175-191`](../../runtime/tools/executor.py#L175-L191)

## 4. `runtime/providers/config.py`

Severity: **HIGH**

Violations:

- loads API env files into process environment
- persists model selection and provider chain state
- constructs provider instances
- makes fallback policy decisions

Relevant lines:

- env loading and config setup: [`runtime/providers/config.py:50-84`](../../runtime/providers/config.py#L50-L84)
- fallback generation: [`runtime/providers/config.py:89-111`](../../runtime/providers/config.py#L89-L111)
- model switching persistence: [`runtime/providers/config.py:113-121`](../../runtime/providers/config.py#L113-L121)
- provider availability and fallback chain: [`runtime/providers/config.py:126-149`](../../runtime/providers/config.py#L126-L149)

## 5. `runtime/adaptive_routing/epistemic_kernel.py`

Severity: **HIGH**

Violations:

- provenance, contradiction, routing depth, confidence, and response generation are coupled
- local retrieval and output formatting are handled in one class
- manual review is emitted from the same evaluator

Relevant lines:

- registry loading and artifact indexing: [`runtime/adaptive_routing/epistemic_kernel.py:84-102`](../../runtime/adaptive_routing/epistemic_kernel.py#L84-L102)
- evaluate path: [`runtime/adaptive_routing/epistemic_kernel.py:104-153`](../../runtime/adaptive_routing/epistemic_kernel.py#L104-L153)
- evidence merge/confidence/contradiction: [`runtime/adaptive_routing/epistemic_kernel.py:191-260`](../../runtime/adaptive_routing/epistemic_kernel.py#L191-L260)

## 6. `runtime/orchestrator/knowledge_router.py`

Severity: **HIGH**

Violations:

- overlaps conceptually with `AOIAEpistemicKernel`
- encodes local routing, thresholding, and savings accounting in one unit
- is a second authority for local RHCSA routing

Relevant lines:

- routing decision path: [`runtime/orchestrator/knowledge_router.py:62-81`](../../runtime/orchestrator/knowledge_router.py#L62-L81)
- report accounting: [`runtime/orchestrator/knowledge_router.py:83-106`](../../runtime/orchestrator/knowledge_router.py#L83-L106)

## 7. `runtime/orchestrator/gemini_gemma.py`

Severity: **HIGH**

Violations:

- strategic planning, worker action generation, RHCSA context injection, and memory replay are coupled
- worker path is currently disabled yet still present as transitional architecture

Relevant lines:

- planner and worker responsibilities: [`runtime/orchestrator/gemini_gemma.py:17-73`](../../runtime/orchestrator/gemini_gemma.py#L17-L73)
- prompt construction with RHCSA context and worker memory: [`runtime/orchestrator/gemini_gemma.py:122-180`](../../runtime/orchestrator/gemini_gemma.py#L122-L180)

## 8. `runtime/webapp.py`

Severity: **MEDIUM**

Violations:

- thin but still shares a single runtime object across requests
- model switching and prompt execution are exposed via the same service process

Relevant lines:

- shared runtime adapter: [`runtime/webapp.py:28-63`](../../runtime/webapp.py#L28-L63)
- HTTP API surface: [`runtime/webapp.py:74-144`](../../runtime/webapp.py#L74-L144)

## 9. `runtime/tools/build_rhcsa_library.py`

Severity: **MEDIUM**

Violations:

- build/generation tool still references `memory/rhcsa_context.py` as a runtime integration point
- this points to a missing/generated boundary rather than a canonical in-repo module

Relevant lines:

- integration point list: [`runtime/tools/build_rhcsa_library.py:1087-1099`](../../runtime/tools/build_rhcsa_library.py#L1087-L1099)

## 10. Missing runtime module boundary

Severity: **CRITICAL**

Observed issue:

- `runtime/main.py` imports `memory.rhcsa_context` and `memory.gemma_worker_memory`
- the repository tree contains only `memory/README.md`
- no in-repo Python package for `memory.*` is present

Why this matters:

- the runtime currently depends on a generated or out-of-tree module boundary
- this is a hard architectural ambiguity before any refactor

Relevant lines:

- imports: [`runtime/main.py:25-34`](../../runtime/main.py#L25-L34)
- generator hint: [`runtime/tools/build_rhcsa_library.py:1087-1099`](../../runtime/tools/build_rhcsa_library.py#L1087-L1099)

## Future L0-L5 violations

Likely violations against the planned ontology:

- `L0` ephemeral state is mixed with durable state in `MemoryStore`
- `L1` operational logs are mixed with evidence and notebook projections
- `L2` reasoning traces are persisted alongside execution records
- `L3` provenance is embedded in retrieval runtime rather than isolated
- `L4` evidence is written through the same recorder as operational history
- `L5` contradiction handling is loaded into runtime routing rather than read-only verification

