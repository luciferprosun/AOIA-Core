# AOIA-Core Shell-Action Threat Model

## 1. Purpose

AOIA-Core is a local-first pre-execution command inspection and audit layer for AI-agent proposed shell commands.

This threat model defines what AOIA-Core currently tries to inspect, what it does not protect against, and what must remain out of scope until future milestones.

## 2. Assets

- User filesystem and shell environment.
- Proposed shell commands generated or suggested by AI agents.
- Project repository and runtime state.
- Command classification rules.
- Audit artifacts and event ledgers.
- Human approval boundary.

## 3. Actors

- Human user or reviewer.
- AI model or agent proposing commands.
- AOIA-Core classifier or validator.
- AOIA-Core audit or logging layer.
- Shell execution environment.
- Potential attacker influencing model output through prompt injection or misleading instructions.

## 4. Trust Boundaries

- LLM or model output is untrusted.
- Proposed shell commands are untrusted until classified and reviewed.
- The classification layer is a pre-execution inspection layer, not a sandbox.
- Human approval is required before any future execution path.
- The shell execution environment is high-risk and currently outside GT-RUNTIME-7A.

## 5. In-Scope Threats

- Destructive shell suggestions.
- Remote-code-execution patterns such as pipe-to-shell.
- Privilege escalation indicators.
- Filesystem destructive patterns.
- Misleading AI-generated command advice.
- Prompt-injection-induced command suggestions.
- Obfuscated command strings that may bypass simple rules.
- Ambiguous administrative commands requiring human review.

## 6. Out-of-Scope Threats

- OS-level containment.
- Kernel or privilege-escalation vulnerabilities.
- Attacks bypassing AOIA-Core entirely.
- Sandboxing.
- Malware analysis.
- Formal verification.
- Complete shell safety.
- Social engineering of the human reviewer.
- Supply-chain security.
- Cloud or provider infrastructure.
- GUI or terminal-agent security.

## 7. Known Bypasses and Limitations

- The current GT-RUNTIME-6 corpus is 12 curated internal cases.
- The current classifier is rule/regex-style.
- There is no shell AST parser yet.
- There is no sandbox yet.
- There is no adversarial obfuscation benchmark yet.
- There is no large external corpus yet.
- There is no formal proof of complete protection.
- Simple regexes may miss quoting, variable interpolation, command substitution, heredoc, encoded payload indicators, chained commands, and context-dependent danger.

## 8. Mitigations Already Present

- Controlled command classification regression harness.
- Inert test corpus.
- No execution of corpus commands.
- Auditable metrics output.
- Event ledger artifact generation for GT-RUNTIME-6 validation.
- Human-approved execution boundary as a design requirement.
- 372 tests, 4 skipped at GT-RUNTIME-6 validation.

## 9. Planned Mitigations

- Benchmark limitations document.
- Reproduction guide.
- Reviewer quick-start.
- Glossary.
- GT-RUNTIME roadmap.
- Future GT-RUNTIME-7B inert CommandProposal DTO.
- Future approval-gate control-flow tests.
- Future adversarial corpus v0.2 plan or stub.
- No execution until after non-execution layers are reviewed.

## 10. Non-Goals

AOIA-Core is not a replacement for ShellCheck, sandboxing, seccomp, firejail, nsjail, bubblewrap, or OS-level containment.
AOIA-Core is not a complete security sandbox.
AOIA-Core does not prove complete real-world shell safety.
GT-RUNTIME-7A adds documentation only and no execution capability.
