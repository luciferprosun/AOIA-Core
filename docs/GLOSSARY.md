# AOIA-Core Glossary

## AOIA-Core

The local-first runtime repository covered by the GT-RUNTIME milestones. In the current scope it acts as a pre-execution classifier and auditable AI-agent action boundary.

## AOIA-NMS

A related but distinct AOIA project context. It is not the authority for AOIA-Core runtime claims unless explicitly documented inside this repository.

## GT-RUNTIME

The runtime hardening milestone series used to scope and review AOIA-Core runtime work.

## GT-RUNTIME-6

The milestone that added a controlled command classification regression test on 12 curated internal shell-command cases, with metrics and event-ledger-style audit artifacts.

## GT-RUNTIME-7A

The docs-only honesty pack milestone. It creates reviewer-facing documentation and does not add runtime or shell execution capability.

## Controlled Regression Harness

An internal regression test setup used to check whether current classifier logic continues to match expected labels on a limited curated corpus. It is not a general benchmark.

## Pre-Execution Classifier

A component that classifies proposed command strings before any future execution path. It inspects strings and does not execute them.

## Human-Approved Execution Boundary

A design boundary stating that any future execution path must remain behind explicit human approval.

## Event Ledger

An append-oriented audit record of runtime or validation events. In the current repository it is part of the auditable runtime boundary, not proof of command safety.

## Provenance

The record of where artifacts, knowledge records, or audit entries came from and how they were derived.

## Audit Intake

A reviewer-facing note that records external review feedback or claim-boundary concerns without modifying runtime code.

## Cloudflare Stash

The preserved unrelated Cloudflare work stored in `git stash`. It remains outside the scope of GT-RUNTIME-7A.

## LSC

External research context referenced in broader AOIA discussions. It is not AOIA-Core runtime authority by default.

## MHLM / MDLH

External research terminology or adjacent conceptual material. It is not implemented by GT-RUNTIME-7A.

## SCEMDA / HNC

External research terminology or framework context. It is not part of the AOIA-Core runtime authority layer unless explicitly brought into repo-backed runtime work later.

## CommandProposal

A future planned GT-RUNTIME-7B item for representing an inert proposed command schema or DTO. It is not implemented by GT-RUNTIME-7A.

## Adversarial Corpus v0.2

A future planned GT-RUNTIME-7B item for extending beyond the 12 curated internal cases with a more systematic non-executing adversarial test taxonomy or stub. It is not implemented by GT-RUNTIME-7A.
