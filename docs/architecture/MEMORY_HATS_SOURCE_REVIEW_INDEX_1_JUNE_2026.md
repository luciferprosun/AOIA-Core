# AOIA-Core WhiteHat / Memory Hats - Source Review Index - 1 June 2026

This index records the GT1 source re-audit status for the Memory Hats architecture line. The exact 31 May PDF filenames listed in the GT1 prompt were not found under `/home/l/Desktop`, `/home/l/Desktop/AOIA-Core`, or `/home/l/Downloads`. One related local PDF was found and inspected:

- `/home/l/Desktop/MHLM_Ultra_Master_25maj/modele llm raporty/DeepSeek_AOIA_Memory_Semantics_Audit.pdf`

Because the expected architecture PDFs were missing under their requested names, this index separates local extraction status from the checkpoint conclusions supplied in the GT1 task. No PDF files were moved or edited.

## 1. DeepSeek

Source file path:
- Expected: `DeepSeek_AOIA_Memory_Hat_Architecture_Response_31_May_2026.pdf`
- Exact file found: not found
- Related file inspected: `/home/l/Desktop/MHLM_Ultra_Master_25maj/modele llm raporty/DeepSeek_AOIA_Memory_Semantics_Audit.pdf`

Summary:
- Reframes AOIA's memory problem as a semantics and contamination problem, not a raw storage problem.
- Strongly separates operational logs, reasoning traces, provenance, evidence, and contradiction records.
- Supports immutable evidence chains and explicit provenance boundaries.
- Warns against recursive self-conditioning and runtime state becoming persistent truth.
- Supports contradiction preservation as first-class records without truth-engine claims.
- Aligns with a local, deterministic, operator-supervised Memory Hats design.

Keep / defer / reject:
- Keep: semantic firewall, evidence boundary discipline, contradiction isolation, deterministic hashes.
- Keep: split retrieval/storage from future visualization.
- Defer: any broad autonomous memory promotion.
- Reject: recursive prompt conditioning, uncontrolled swarm memory, runtime-state-to-truth promotion.

Risk notes:
- Memory Hats must not collapse operational logs into evidence.
- Tags must remain advisory records, not authority or truth.

Direct relevance:
- High. Supports the v0.1 design boundary: local tags, deterministic hashes, no executor authority.

## 2. Kimi

Source file path:
- Expected: `Kimi_AOIA_Memory_Hat_Architecture_Review_31_May_2026.pdf`
- Exact file found: not found

Summary:
- Checkpoint conclusion: define canonical naming before implementation.
- Checkpoint conclusion: keep Memory Hats outside executor policy.
- Checkpoint conclusion: keep safety boundaries explicit and reviewer-readable.
- Checkpoint conclusion: avoid broad feature naming that implies autonomous cognition.
- Checkpoint conclusion: document what is deferred before coding.

Keep / defer / reject:
- Keep: canonical terms for Memory Hats, Pheromone Correction Tags, Leaf-Vein Routing.
- Keep: explicit non-goals and bounded v0.1.
- Defer: multi-hat stacking and shared tag packs.
- Reject: ambiguous names that imply safety proof or factual correctness.

Risk notes:
- Naming can overclaim. The docs must say advisory and local.

Direct relevance:
- High for documentation discipline and implementation boundaries.

## 3. Gemini

Source file path:
- Expected: `Gemini_AOIA_Chat_Hats_Memory_Hats_Architecture_31_May_2026.pdf`
- Exact file found: not found

Summary:
- Checkpoint conclusion: Memory Hats can become a future product pipeline, but not v0.1 scope.
- Checkpoint conclusion: one-pass detector concepts may help later, but should not drive first implementation.
- Checkpoint conclusion: the first useful version is small, testable, and local.
- Checkpoint conclusion: future UX and Memory Garden ideas should be separated from storage/retrieval.
- Checkpoint conclusion: avoid model-weight or prompt-injection assumptions.

Keep / defer / reject:
- Keep: product-roadmap framing only as future work.
- Defer: one-pass detector, Memory Garden, multi-hat UX.
- Reject: any claim that hats cure hallucination or prove truth.

Risk notes:
- Product framing can pull scope too wide before storage contracts are stable.

Direct relevance:
- Medium. Useful for roadmap, not for GT-HAT-1 implementation.

## 4. Claude Sonnet

Source file path:
- Expected: `Claude_Sonnet_AOIA_WhiteHat_Memory_Hats_Architecture_Review_31_May_2026.pdf`
- Exact file found: not found

Summary:
- Checkpoint conclusion: strict scope reduction is required.
- Checkpoint conclusion: RHCSA Hat first is the safest implementation slice.
- Checkpoint conclusion: architecture note should come before runtime code.
- Checkpoint conclusion: avoid router, executor, provider, memory, provenance, web, or TUI changes in early GTs.
- Checkpoint conclusion: v0.1 should be testable as isolated modules.

Keep / defer / reject:
- Keep: RHCSA/Linux hat first.
- Keep: docs-first approach.
- Defer: runtime integration until local storage and lookup tests pass.
- Reject: broad refactors and main merge before NLnet decision.

Risk notes:
- The largest risk is scope creep into runtime authority or UI before data contracts exist.

Direct relevance:
- Very high. Drives the GT-HAT-0 through GT-HAT-4 sequence.

## 5. Perplexity 1

Source file path:
- Expected: `Perplexity_AOIA_WhiteHat_Memory_Hats_Web_Grounded_Architecture_Research_31_May_2026.pdf`
- Exact file found: not found

Summary:
- Checkpoint conclusion: use web-grounded patterns only as architecture references, not dependencies.
- Checkpoint conclusion: materialized paths are a practical local-first retrieval structure.
- Checkpoint conclusion: SQLite plus JSONL backup is enough for v0.1.
- Checkpoint conclusion: phyllotaxis and Memory Garden are visualization ideas, not indexing foundations.
- Checkpoint conclusion: shared/global tags should wait until local semantics are stable.

Keep / defer / reject:
- Keep: materialized paths, local SQLite, JSONL export/import later.
- Defer: phyllotaxis visualization, network sync, global tag packs.
- Reject: web service dependency for core Memory Hats.

Risk notes:
- External patterns must not become external runtime dependencies.

Direct relevance:
- High for storage/retrieval shape and future visualization boundary.

## 6. Perplexity 2

Source file path:
- Expected: `Perplexity2_AOIA_WhiteHat_SQLite_Path_Optimization_EXPLAIN_31_May_2026.pdf`
- Exact file found: not found

Summary:
- Checkpoint conclusion: use SQLite path optimization carefully.
- Checkpoint conclusion: prefix lookup should prefer range / BETWEEN style over broad LIKE scans where appropriate.
- Checkpoint conclusion: `EXPLAIN QUERY PLAN` is a debug tool, not runtime policy.
- Checkpoint conclusion: defer FTS5 until baseline v0.1 is measured.
- Checkpoint conclusion: partial and covering indexes should wait until observed query patterns justify them.

Keep / defer / reject:
- Keep: one table, primary key hash, path index, hat/status index.
- Keep: path range lookup guidance.
- Defer: FTS5, advanced indexes, query planner tooling in normal runtime.
- Reject: premature optimization before a small table and tests exist.

Risk notes:
- Optimization work can obscure the safety contract if done before storage semantics are settled.

Direct relevance:
- High for GT-HAT-4 storage design.

## 7. Canonical Architecture Library

Source file path:
- Expected: `AOIA_WhiteHat_Memory_Hats_Canonical_Architecture_Library_31_May_2026.pdf`
- Exact file found: not found
- Related combined source expected: `AOIA_Memory_Hats_Architecture_DeepSeek_Kimi_Combined_31_May_2026.pdf` was also not found.

Summary:
- Checkpoint conclusion: final path is Leaf-Vein Routing plus SQLite tags.
- Checkpoint conclusion: deterministic hashes anchor deduplication.
- Checkpoint conclusion: Pheromone Correction Tags are local advisory correction records.
- Checkpoint conclusion: Golden Ratio / Golden Angle belongs only to future visualization.
- Checkpoint conclusion: v0.1 should avoid scoring, review queues, sync, UI, Android, global tags, and multi-hat stacking.
- Checkpoint conclusion: implementation should proceed in small tested GT-HAT steps.

Keep / defer / reject:
- Keep: minimal v0.1 data model, one-table SQLite store, leaf path builder.
- Defer: Memory Garden, signed packs, global sharing, vector search.
- Reject: any automatic prompt injection, command execution, or authority over executor policy.

Risk notes:
- The canonical library is missing locally, so this GT1 uses the supplied checkpoint conclusions as the consolidation baseline.

Direct relevance:
- Very high. Defines the implementation phase plan and non-goals.
