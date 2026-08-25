# Dated Evidence Review

## Purpose

`runtime/evidence_review/` compares a bounded candidate answer with a small, dated evidence registry. It is a deterministic AOIA-Core module for surfacing known stale values, conflicting values, missing temporal scope, and missing official attribution.

It is not a general legal reasoner, crawler, retrieval system, approval gate, or source of legal advice.

## One implementation, three surfaces

All surfaces call `evidence_review.review_candidate()`:

- CLI: `/review`, `/review corrected`, or `/review TEXT`
- web API: `GET /api/review/scenario` and `POST /api/review`
- web console: **Evidence review** view served by `runtime/webapp.py`

There is no second package, process, server, model selector, or authority model for this capability.

## Data path

```text
candidate text
  -> type, emptiness, and 20,000-character checks
  -> isolated copy of the bundled dated registry
  -> deterministic amount/marker comparison
  -> evidence-set SHA-256 + answer-snapshot SHA-256
  -> findings and source records
  -> HUMAN_REVIEW_REQUIRED
```

The engine uses no model provider, subprocess, outbound request, persistence API, or telemetry. The web request limit is 24,000 bytes, and the AOIA-Core server accepts loopback bindings only.

## Authority contract

Every successful result includes:

```json
{
  "decision_state": "HUMAN_REVIEW_REQUIRED",
  "authority": "METADATA_ONLY_NO_AUTHORITY",
  "legal_advice": false,
  "network_used": false
}
```

A corroborated value does not approve an answer. Hashes prove deterministic binding to the bundled records and candidate snapshot; they do not prove source authenticity, factual completeness, legal applicability, or truth.

## Bundled scenario

The current registry contains one German employment-law example. It distinguishes the EUR 12.82 value effective in 2025 from EUR 13.90 effective on 1 January 2026. The three official source records were checked on 2026-08-25:

- [BMAS minimum-wage overview](https://www.bmas.de/DE/Arbeit/Arbeitsrecht/Mindestlohn/Informationen-zum-Mindestlohn/informationen-zum-mindestlohn-deutsch.html)
- [BMAS official rate history](https://www.bmas.de/DE/Arbeit/Arbeitsrecht/Mindestlohn/Glossar/G/Gesetzlicher-Mindestlohn.html)
- [Fifth Minimum Wage Adjustment Regulation](https://www.gesetze-im-internet.de/milov5/MiLoV5.pdf)

The checked date is provenance metadata, not a promise of future currency. Operators must inspect current official material before relying on the result.

## Extension rule

The current comparison logic is deliberately scenario-specific. Adding another jurisdiction, domain, currency, or claim type requires:

1. a documented scenario contract and official-source review,
2. a data-driven matcher appropriate to the claim type,
3. deterministic and fail-closed tests,
4. explicit authority and limitation text,
5. API/UI compatibility checks,
6. operator approval before activation.

Do not silently treat arbitrary evidence records as compatible with the current euro-value matcher.

## Validation

Focused coverage lives in:

- `tests/test_evidence_review.py`
- `tests/test_evidence_review_web.py`

The tests cover stale/current/conflicting/unknown values, deterministic hashes, registry isolation, invalid input, CLI delegation, no provider/process imports, no write-mode file access, unified UI identity, loopback binding, security headers, request limits, scenario API, and review API.
