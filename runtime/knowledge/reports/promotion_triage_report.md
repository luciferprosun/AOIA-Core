# Candidate Promotion Triage Report

This report is triage-only. No canonical index files were modified.

## Summary

- Total candidates processed: 3152
- ACCEPT: 1267
- REVIEW: 1788
- REJECT: 97
- Gemini additions isolated: 25
- Unresolved provenance count: 1021
- Schema-invalid projected records: 68

## Contamination Reasons

- path_not_command: 74
- probable_pdf_merge_artifact: 16
- invalid_base_command: 2
- likely_contamination_or_comment: 7
- suspicious_formatting: 76
- multi_command_ambiguity: 130
- gemini_expansion_addition: 25

## Most Common Rejection Reasons

- malformed: 76
- suspicious_formatting: 76
- path_not_command: 74
- weak_description: 36
- duplicate_ambiguity: 30
- unresolved: 21
- probable_pdf_merge_artifact: 16
- schema_invalid: 11
- likely_contamination_or_comment: 7
- multi_command_ambiguity: 3
- invalid_base_command: 2
- missing_source_page: 2

## Schema Validation Summary

Candidate records were projected into `command.schema.json` shape for validation.
Broken records were not silently repaired; schema failures stayed in REVIEW or REJECT.

## Recommended Manual Review Priorities

1. Review `review_queue.json` entries with `gemini_expansion_addition` first; do not auto-promote.
2. Review duplicate ambiguity against canonical/index records before accepting.
3. Review weak descriptions and missing source pages against the canonical PDF.
4. Reject or rewrite suspicious snippets only after independent source verification.
