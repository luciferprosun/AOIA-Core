# Level 6 Security Pitfalls

## Purpose
Level 6 security pitfalls collect high-risk and critical Python patterns where dynamic execution, deserialization, filesystem mutation, shell invocation, or namespace mutation can create security or data-loss hazards.

## Current Status
This is a draft advisory layer only. Records are not runtime-integrated and are not promoted.

## Policy
- High and critical risk records default to `never_execute` or `advisory_only_no_execution`.
- Examples and corrected patterns are inert strings only.
- Official documentation references may be listed as future verification targets.
- A reference is not treated as checked unless a later official-docs review records that status separately.
- Runtime integration remains forbidden until a future governance gate.
