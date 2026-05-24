# Phase 2B Routing Boundary

Status: implemented minimal deterministic routing repair
Mode: surgical implementation
Date: 2026-05-23

## Objective

Prevent external URLs and GitHub/GitLab repository review requests from activating AOIA deterministic RHCSA/local Linux knowledge retrieval.

This phase only repairs the routing boundary. It does not implement external repository inspection, crawling, browser automation, embeddings, AI classification, retrieval redesign, orchestration redesign, provider changes, governance, or memory architecture changes.

## Files Changed

Runtime:

- `runtime/main.py`

Tests:

- `tests/test_routing_boundary.py`

Report:

- `docs/reports/PHASE_2B_ROUTING_BOUNDARY.md`

## Routing Flow Before

Before Phase 2B:

```text
user request
  -> local route
  -> AOIAEpistemicKernel.evaluate()
  -> RHCSA deterministic retrieval
  -> local_knowledge response if evidence found
  -> model/browser/planner fallback
```

Failure:

```text
https://github.com/luciferprosun/AOIA-Core
  -> AOIAEpistemicKernel.evaluate()
  -> RHCSA/local Linux retrieval
  -> unrelated local knowledge activation
```

This allowed external repository requests to contaminate local RHCSA routing.

## Routing Flow After

After Phase 2B:

```text
user request
  -> local route
  -> deterministic external review classification
     -> external_repository_review placeholder
     -> external_link_review placeholder
  -> AOIAEpistemicKernel.evaluate()
  -> RHCSA deterministic retrieval
```

Boundary placement:

- The new external classification runs before `handle_knowledge_route()`.
- If the input is an external URL, GitHub/GitLab URL, or repository-review intent, the request stops before RHCSA retrieval.
- The route is logged as an external review placeholder.

## Deterministic Detection Added

URL detection:

- `http://`
- `https://`

Repository host detection:

- `github.com`
- `gitlab.com`

Repository intent detection examples:

- `check github project`
- `analyze repository`
- `describe repo`
- `check this github`
- `can you check github repository`
- Polish equivalents including `sprawdź`, `przeanalizuj`, `opisz`, `repozytorium`, `projekt`

## Placeholder Routes

Implemented placeholder route names:

- `external_repository_review`
- `external_link_review`

Current controlled responses:

```text
External repository inspection path detected. Browser inspection path available.
```

```text
External URL detected. Browser inspection path available.
```

These placeholders intentionally do not inspect, crawl, browse, or analyze external repositories yet.

## RHCSA Contamination Status

Fixed:

- GitHub URLs no longer trigger `AOIAEpistemicKernel.evaluate()`.
- GitLab URLs no longer trigger `AOIAEpistemicKernel.evaluate()`.
- Explicit GitHub/repository review intents no longer trigger RHCSA retrieval.

Preserved:

- Plain Linux/RHCSA operational requests can still reach the deterministic kernel.
- Normal non-external model requests are not classified as external review.

## Validation Tests

Command:

```text
PYTHONPATH=runtime python3 -m unittest tests.test_routing_boundary
```

Result:

```text
......
----------------------------------------------------------------------
Ran 6 tests

OK
```

Covered cases:

- `jakim jestes modelem` is not classified as external review.
- `jakim jestes modelem` can still use the normal runtime response path.
- `https://github.com/luciferprosun/AOIA-Core` returns external repository placeholder and does not call RHCSA kernel.
- `can you check github repository` returns external repository placeholder and does not call RHCSA kernel.
- `can you inspect github repository` returns external repository placeholder and does not call RHCSA kernel.
- `how to create folder in linux` still calls RHCSA/local knowledge path.

Regression check:

```text
PYTHONPATH=runtime python3 -m unittest tests.test_executor_containment
```

Result:

```text
.
----------------------------------------------------------------------
Ran 1 test

OK
```

## Unresolved Routing Risks

- External repository review is only a placeholder route.
- No safe browser/repository inspection workflow exists yet.
- No external source provenance capture policy exists yet.
- URLs are blocked from RHCSA retrieval, but full external-link handling is not implemented.
- `build_plan_request()` still injects RHCSA context for model planning in non-external flows.
- Legacy `KnowledgeRouter` remains behind the AOIA kernel for Linux/RHCSA requests.

## Next Safest Routing Step

The next safe routing step should be documentation or a new narrow phase for external review capability.

Recommended next phase:

- Define external repository review doctrine before implementation.

Do not implement next without a new phase:

- crawling
- autonomous scraping
- browser-based repository inspection
- AI repository classifiers
- embeddings
- external execution
- retrieval over external content

## Final Judgment

Deterministic URL boundary exists.

External placeholder route exists.

GitHub URLs no longer trigger RHCSA deterministic retrieval.

Runtime continuity is preserved because the change only inserts a deterministic pre-knowledge-route boundary and does not alter memory, providers, routing internals, retrieval implementation, or executor behavior.
