# AOIA-Core Reviewer Quickstart

## 1. What AOIA-Core Is

AOIA-Core is a local-first pre-execution command classifier and auditable AI-agent action boundary for proposed shell commands.

The current GT-RUNTIME-6 state is a controlled command classification regression test on 12 curated internal shell-command cases. It matched all 12 internal test cases with current regex/rule logic. This is an internal regression harness and a starting point for seeking initial external technical review.

## 2. What AOIA-Core Is Not

- It is not a sandbox.
- It is not a replacement for OS-level containment.
- It is not a claim of validated safety.
- It does not prove complete real-world shell safety.
- It is not a production-ready terminal execution security layer.

## 3. What To Read First

- `README.md`
- `docs/THREAT_MODEL.md`
- `docs/BENCHMARK_LIMITATIONS.md`
- `docs/HOW_TO_REPRODUCE_GT_RUNTIME_6.md`
- `docs/GT_RUNTIME_ROADMAP.md`
- `docs/audit/`

## 4. Validation Commands

```bash
python3 -m compileall runtime tests
PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v
```

## 5. Context Boundary

LSC, MHLM or MDLH, SCEMDA or HNC, and Gary-related materials are external research or audit context and are not AOIA-Core runtime authority.
