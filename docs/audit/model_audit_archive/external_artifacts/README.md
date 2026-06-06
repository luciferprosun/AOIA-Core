# External Model Audit Artifacts

Large model audit PDFs, full repository snapshots, generated archive ZIPs, and
similar payloads should live outside this Git directory.

Recommended storage locations:

- Desktop archive for local working copies.
- GitHub Release assets for project-tied distribution.
- Zenodo for citable long-term preservation.
- Checksum-based references for reproducible lookup.

When referencing an external artifact, record:

- Filename.
- Date.
- Artifact type.
- Related commit if known.
- External location.
- SHA256 checksum when available.
- Notes about whether it is current or historical.

This directory should contain indexes and summaries only. Do not place large
PDF or ZIP payloads here.
