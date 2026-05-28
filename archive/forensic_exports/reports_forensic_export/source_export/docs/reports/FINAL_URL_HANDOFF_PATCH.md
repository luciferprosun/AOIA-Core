# Final URL Handoff Patch

Status: implemented minimal deterministic external URL handoff
Mode: final micro-patch
Date: 2026-05-23

## Scope

This patch keeps external URLs and repository inspection requests out of AOIA deterministic RHCSA/local knowledge routing.

It does not implement autonomous browsing, crawling, scraping, AI repository analysis, embeddings, retrieval redesign, orchestration redesign, provider changes, governance changes, or memory architecture changes.

## Exact Files Changed

- `runtime/main.py`
- `tests/test_routing_boundary.py`
- `docs/reports/PHASE_2B_ROUTING_BOUNDARY.md`
- `docs/reports/FINAL_URL_HANDOFF_PATCH.md`

## Old Routing Behavior

Before the boundary:

```text
external URL / GitHub request
  -> AOIA deterministic epistemic kernel
  -> local_knowledge
  -> RHCSA retrieval
  -> unrelated local Linux knowledge response
```

This allowed GitHub and external repository requests to contaminate the RHCSA path.

## New Routing Behavior

After the boundary:

```text
external URL / GitHub request
  -> deterministic external review classifier
  -> external_repository_review or external_link_review
  -> controlled browser-inspection handoff response
  -> stop before RHCSA/local knowledge retrieval
```

Current controlled responses:

```text
External repository inspection path detected. Browser inspection path available.
```

```text
External URL detected. Browser inspection path available.
```

## RHCSA Contamination Status

Fixed for this scope:

- `https://` and `http://` inputs are detected before RHCSA retrieval.
- `github.com` and `gitlab.com` inputs are detected before RHCSA retrieval.
- Repository inspection intents such as `can you inspect github repository` are detected before RHCSA retrieval.
- Matching external requests do not call `AOIAEpistemicKernel.evaluate()`.

Preserved:

- Normal non-external requests remain on the existing runtime path.
- Linux/RHCSA questions can still use deterministic local knowledge.

## Browser Handoff Status

Browser handoff now opens the detected URL through the existing browser bridge and reads the visible page text.

The patch still does not crawl a repository, perform autonomous browsing, analyze repository contents deeply, or create provenance records from external content.

## Validation

Commands:

```text
PYTHONPATH=runtime python3 -m unittest tests.test_routing_boundary
PYTHONPATH=runtime python3 -m unittest tests.test_executor_containment
```

Results:

```text
tests.test_routing_boundary: Ran 6 tests OK
tests.test_executor_containment: Ran 1 test OK
```

Expected coverage:

- `jakim jestes modelem` remains a normal runtime request.
- `https://github.com/luciferprosun/AOIA-Core` does not trigger RHCSA retrieval.
- `can you check github repository` does not trigger RHCSA retrieval.
- `can you inspect github repository` does not trigger RHCSA retrieval.
- `https://github.com/luciferprosun/AOIA-Core` is opened via browser handoff instead of local knowledge.
- `how to create folder in linux` still reaches the RHCSA/local knowledge path.

## Unresolved Browser Limitations

- No safe browser execution policy is frozen for deeper repository inspection.
- No external-source provenance capture exists for browser content.
- No contradiction handling exists for external repository claims.
- No retrieval guard exists for external browser output.
- Browser text must not become evidence without a future provenance and authority boundary.

## Safest Next Future Routing Step

Freeze a small external inspection doctrine before adding any browser execution:

- allowed external inputs
- provenance capture requirements
- browser output quarantine rules
- retrieval exclusion rules
- operator approval requirements

Do not implement autonomous browsing or repository analysis without a dedicated phase.
