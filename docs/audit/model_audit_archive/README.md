# AOIA Model Audit Archive

This directory is a lightweight index for AOIA-Core model audit artifacts.
It records what external model reviews, snapshots, consensus reports, and
methodology reports exist without storing large PDF or archive payloads here.

Large PDFs, full repository snapshots, ZIP archives, and generated audit packs
should remain external artifacts. Suitable storage targets include a Desktop
archive, a GitHub Release asset, Zenodo, or another checksum-addressable
artifact store.

Model outputs are advisory review material. They can suggest issues, identify
questions, and provide comparison signals, but they are not canonical truth.
Authoritative evidence remains the source code, tests, commits, CI results,
reproducible artifacts, and explicit human review decisions.

## Index Files

- [AUDIT_INDEX_2026-06-06.md](AUDIT_INDEX_2026-06-06.md) lists known audit artifacts from 02-06 June 2026.
- [AUDIT_MANIFEST_2026-06-06.csv](AUDIT_MANIFEST_2026-06-06.csv) provides a machine-readable artifact manifest.
- [AUDIT_CLASSIFICATION_GUIDE.md](AUDIT_CLASSIFICATION_GUIDE.md) defines artifact classes and interpretation rules.
- [AUDIT_EVIDENCE_POLICY.md](AUDIT_EVIDENCE_POLICY.md) defines evidence weight and authority.
- [external_artifacts/README.md](external_artifacts/README.md) explains where large artifacts should live.

## Storage Boundary

This archive is intentionally metadata-only. Do not commit large PDFs or
full snapshots into this directory. Add references, checksums, and summary
records instead.
