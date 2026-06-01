# Python Master Library Official Docs Cross-Check Plan

## Purpose
This plan defines the documentation-only workflow for verifying imported Python Master Library records before any future promotion work is considered.

Imported PDFs, imported indexes, and external model reviews are unverified inputs. They must be checked against official Python documentation and PEPs before any record may move toward a higher trust state.

This phase does not perform the cross-check itself. It only defines the allowed process, checkpoints, and documentation requirements for later human review work.

## Canonical Verification Sources
Allowed verification source categories:
- docs.python.org Python language reference
- docs.python.org Python library reference
- docs.python.org data model documentation
- docs.python.org built-in functions documentation
- docs.python.org exceptions documentation
- docs.python.org subprocess documentation
- docs.python.org pathlib/os/shutil/tempfile documentation
- docs.python.org pickle/json/tomllib documentation
- peps.python.org for PEP-specific features
- official package documentation only for external packages, if later needed

## What Must Be Checked First
Priority order:
1. dangerous built-ins and APIs:
   - eval
   - exec
   - compile
   - import
   - open
   - input
   - globals
   - locals
   - getattr
   - setattr
   - delattr
2. subprocess and shell safety
3. filesystem deletion/overwrite:
   - os.remove
   - os.unlink
   - pathlib.Path.unlink
   - shutil.rmtree
4. serialization:
   - pickle.load
   - pickle.loads
   - json.loads
   - tomllib.load
   - yaml only if external docs are available
5. keywords and language syntax
6. built-in type methods
7. exceptions
8. magic/dunder methods
9. Python 3.10-3.13 version-specific features

## Verification Rules
- imported PDFs remain imported_reference_unverified until checked
- Kimi/DeepSeek remain external_model_review_unverified
- no model-generated statement is canonical
- no record becomes official_docs_checked without exact official source reference
- no record becomes promoted during this phase
- official docs links should be stored as references, not copied as full text
- if official docs contradict imported source, official docs win
- if uncertainty remains, mark disputed or needs_human_review
- do not scrape the web
- do not execute Python examples during cross-check preparation

## Review Status Lifecycle
Allowed movement for future phases:
- imported_unverified -> candidate
- candidate -> human_reviewed
- human_reviewed -> official_docs_checked
- official_docs_checked -> promoted

Additional rules:
- H18 does not perform status movement.
- H18 only prepares the process.
- H18 does not mark any record official_docs_checked.
- H18 does not promote any record.

## Required Cross-Check Output Per Record
Each future cross-check should produce:
- the record identifier or term being reviewed
- the exact official source reference used
- the Python version scope reviewed
- a short summary of what was verified
- any discrepancy between imported text and official docs
- safety note changes, if any
- risk-level change recommendation, if any
- a next-status recommendation
- a do-not-promote reason if uncertainty remains

## Discrepancy Handling
If a discrepancy is found:
- log it in `DISCREPANCY_LOG.jsonl`
- keep the imported material non-canonical
- prefer the official documentation statement
- require human review before any status recommendation is advanced

If the imported source is incomplete:
- record the missing detail
- keep the item unverified
- do not infer canonical behavior from model output or PDF wording alone

## Constraints For Future H19+
- No copied large chunks of official documentation
- No web scraping
- No runtime integration
- No provider/router/executor changes
- No Memory Hats runtime changes
- No automatic promotion
- No claim that imported PDFs or external reviews are canonical
