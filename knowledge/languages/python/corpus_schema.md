# Python Knowledge Library Entry Schema

Each entry should use the following fields:

- `id`
- `title`
- `domain`
- `difficulty`
- `tags`
- `unsafe_or_wrong_pattern`
- `corrected_pattern`
- `explanation`
- `safety_notes`
- `verification_steps`
- `related_linux_rhcsa_links`
- `review_status`
- `evidence_refs`
- `execution_policy`

Field notes:

- `id`: stable unique identifier for the record
- `title`: short human-readable topic name
- `domain`: broad category such as `subprocess`, `files`, or `packaging`
- `difficulty`: suggested level such as `beginner`, `intermediate`, or `advanced`
- `tags`: list of searchable labels
- `unsafe_or_wrong_pattern`: the pattern to avoid
- `corrected_pattern`: safer or more correct replacement pattern
- `explanation`: short reasoning for the correction
- `safety_notes`: explicit risk boundaries and operator cautions
- `verification_steps`: review-only verification guidance
- `related_linux_rhcsa_links`: optional bridge to Linux/RHCSA operational context
- `review_status`: `candidate`, `confirmed`, or `rejected`
- `evidence_refs`: human-review sources such as official docs or standards
- `execution_policy`: for this scaffold, use `advisory_only_no_execution`
