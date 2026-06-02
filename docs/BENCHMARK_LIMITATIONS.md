# AOIA-Core GT-RUNTIME-6 Regression Harness Limitations

## 1. Summary

GT-RUNTIME-6 is a controlled command classification regression test on 12 curated internal shell-command cases.

## 2. What GT-RUNTIME-6 Shows

- The validation script can load corpus records.
- Command strings can be classified deterministically.
- All 12 curated internal cases matched expected labels with current rules.
- Metrics and event ledger artifacts can be generated.
- The harness is reproducible locally.

## 3. What GT-RUNTIME-6 Does Not Show

- It is not an external benchmark.
- It is not proof of complete shell safety.
- It is not proof of real-world adversarial robustness.
- It is not formal verification.
- It is not sandboxing.
- It is not shell execution safety.
- It is not resistance to all obfuscation.
- It is not a replacement for ShellCheck or OS containment.

## 4. Corpus Limitation

- Only 12 curated cases are included.
- The cases are internally selected.
- The current set emphasizes simple direct patterns.
- There is no large external corpus.
- There is no independent ground truth set.
- There is no adversarial v0.2 corpus yet.

## 5. Classifier Limitation

- The current classifier is rule/regex-style.
- Likely bypass classes include whitespace obfuscation, quoting tricks, variable interpolation, command substitution, encoded payload indicators, heredoc indicators, chained commands, and context-dependent danger.

This document does not provide operational exploit instructions.

## 6. Metrics Caveat

"All GT-RUNTIME-6 metric values are internal regression results over a 12-case controlled corpus. Values such as detection_rate=1.0 or false_positive_rate=0.0 must not be interpreted as general real-world safety estimates."

## 7. Safer Public Wording

Use "controlled regression harness" or "internal regression test."
Avoid unqualified "benchmark," "validated," "proves," and "AI safety benchmark."

## 8. Next Improvements

- Threat model.
- Adversarial corpus v0.2 plan.
- Inert adversarial stub later.
- Rule IDs and classifier versioning later.
- Approval-gate test later.
- External comparison note.
- Possible AST or static-analysis comparison in future.
