# NiFe Hat 002 — RHCSA / Linux Administration Domain

## Status

Hat 002 is a planning shell only.

- Docs-only planning.
- Not implemented in runtime.
- Does not imply validated RHCSA mastery by default.

## Root key: mV:-71

The Hat 002 domain root key is `mV:-71`.

## Why RHCSA/Linux Administration is Hat 002

RHCSA/Linux Administration is the next natural domain after Bash Safety because AOIA work already centers on shell safety, command review, and operational boundaries. Linux administration is adjacent to that work, but it requires a stricter validation layer before future tags can be promoted.

## Relationship to AOIA RHCSA/Linux knowledge library work

Hat 002 is a future planning shell for AOIA RHCSA/Linux knowledge library work.

- It can later organize Linux administration concepts into symbolic tags.
- It does not claim that the full RHCSA domain is already validated.
- It requires source registries, reviewed docs, and tested examples before promotion.

## Core knowledge scope

The intended future scope includes:

- Linux filesystem structure
- accounts and permissions
- processes and services
- packages and storage
- networking and firewall basics
- SELinux basics
- troubleshooting and safe administration patterns

## Initial placeholder tag map

```text
mV:-71          Root: RHCSA / Linux Administration Domain
mV:-71.000001  Linux filesystem hierarchy
mV:-71.000002  Users and groups
mV:-71.000003  Permissions and ownership
mV:-71.000004  Process management
mV:-71.000005  systemd services
mV:-71.000006  Package management
mV:-71.000007  Storage and partitions
mV:-71.000008  LVM basics
mV:-71.000009  Networking basics
mV:-71.000010  Firewall basics
mV:-71.000011  SELinux basics
mV:-71.000012  Logs and troubleshooting
mV:-71.000013  Bash scripting for administration
mV:-71.000014  Automation basics
mV:-71.000015  Safety boundaries for admin commands
```

## Validation requirements

Before Hat 002 can be treated as more than a planning shell:

- source registry needed
- command examples must pass Bash Safety inspection where applicable
- dangerous admin commands require human review
- no sudo/autonomous execution implied
- future RHCSA knowledge must be linked to tested docs or verified sources
- public/model-generated references remain reference_only until validated

## What is not included yet

This hat does not include:

- validated full RHCSA coverage
- runtime integration
- resolver behavior
- retrieval systems
- server storage
- execution authority
- autonomous administration

## Future expansion

Future docs may later add:

- source-linked sub-tags
- reviewed command examples
- contradiction notes
- versioned admin domain evidence packs

## Non-goals

This document does not implement:

- runtime code
- tests
- provider/routing changes
- Cloudflare changes
- server APIs
- model-ranking logic
- trading bot integration
