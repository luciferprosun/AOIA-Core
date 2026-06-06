# Model Audit Artifact Classification Guide

This guide defines the artifact types used by the AOIA model audit archive.
The classification describes how an artifact should be interpreted, not how
truthful or authoritative it is.

## Artifact Types

`full_repo_snapshot`

Captured repository or application state, usually as a large PDF, archive, or
generated report. Treat it as a state reference. Verify claims against source,
commits, tests, and CI.

`multi_model_consensus`

An audit report that compares or consolidates output from multiple models.
Treat it as a stronger advisory signal than a single-model report, but not as
canonical evidence.

`single_model_audit`

An audit or review produced by one model or one model family. Treat it as one
advisory opinion. Confirm every material claim independently.

`methodology_report`

A document describing audit process, scoring, review structure, or model audit
methodology. It can explain how reviews were produced, but it is not direct
evidence of code behavior.

`ci_packaging_audit`

An audit focused on packaging, import layout, editable installs, CI setup, or
reviewer workflow. Validate findings against workflow files, packaging files,
local commands, and GitHub Actions results.

`historical_snapshot`

An older state capture. Use it for timeline reconstruction and regression
analysis. Do not treat it as current unless its commit and file state match
the present branch.

`nested_archive`

A ZIP, tarball, or other archive that contains one or more audit artifacts.
Keep it external and reference it with checksums where possible.

## Current vs Historical

Current artifacts are still relevant to the active branch or the current audit
phase. Historical artifacts document earlier states and should be interpreted
against the commit and date they reviewed.

## Single-Model vs Multi-Model

Single-model artifacts provide one perspective. Multi-model artifacts can
reduce blind spots but may still repeat shared assumptions. Both require
verification against authoritative project evidence.
