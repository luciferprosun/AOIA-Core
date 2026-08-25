# One Concrete Reviewer Example

## Scenario

A candidate answer says that Germany's statutory minimum wage is EUR 12.82 gross per hour in July 2026. The amount was valid from 1 January 2025, while the bundled official records state EUR 13.90 from 1 January 2026.

## Reproduce it

Start the CLI and run:

```text
/review
```

Or start `./runtime/run_web.sh`, open <http://127.0.0.1:4311>, select **Evidence review**, and run the bundled example.

## What AOIA-Core does

1. Validates that the candidate is non-empty text within the size limit.
2. Takes an isolated copy of the curated scenario and three dated source records.
3. Extracts known euro values and checks temporal/source markers.
4. Identifies the prior value as stale for the scenario date.
5. Computes SHA-256 hashes for the evidence set and bound candidate snapshot.
6. Returns findings plus the official source metadata.
7. Stops at `HUMAN_REVIEW_REQUIRED` with `METADATA_ONLY_NO_AUTHORITY`.

The same engine is used by the CLI and web API. It makes no provider call, does not execute a tool, does not persist the candidate, and does not fetch a source during review.

## What becomes evidence?

The bundled records are inputs to a bounded comparison, not automatic proof of truth. The result, findings, and hashes remain review metadata. They do not enter canonical Evidence Memory or gain execution authority.

## What this example does not prove

- It does not prove that the entire candidate answer is correct or incorrect.
- It does not decide whether the law applies to a real person's circumstances.
- It does not prove current source authenticity merely because a URL is bundled.
- It does not provide legal advice.
- It does not validate external model output in general.
- It does not prove production readiness or scientific validity.

The operator must inspect current official sources, verify scope and exceptions, and obtain qualified advice where appropriate. See `docs/modules/DATED_EVIDENCE_REVIEW.md` for the full boundary contract.
