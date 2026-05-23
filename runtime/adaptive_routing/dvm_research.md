# Adaptive Oceanic Intelligence Architecture - DVM Foundation

## Scope

This document captures the first biological reference layer for AOIA. It is not
an autonomous system design. It is a small research foundation for future
adaptive routing based on time, energy cost, pressure, and layered operation.

## Biological DVM Summary

Diel Vertical Migration (DVM) is a daily movement pattern observed in many
marine and freshwater organisms, especially zooplankton and micronekton. The
common pattern is:

- daylight: descend into deeper, darker water
- dusk: migrate upward
- darkness: feed closer to the surface
- dawn: descend again before visual predation risk increases

The behavior is adaptive because surface waters often contain more food, while
deeper waters provide protection from predators that hunt visually.

## Migration Layers

Surface layer:
- higher food availability
- higher exposure to light
- higher risk from visual predators during the day
- useful when darkness lowers predation pressure

Intermediate layer:
- transition zone between feeding and protection
- useful during dusk and dawn
- can become the preferred layer when environmental pressure is mixed

Deep layer:
- lower light
- lower visual predation risk
- often colder and metabolically cheaper
- may reduce energy use during daylight periods

## Environmental Triggers

Daylight:
- increases visibility
- increases visual predation risk
- pushes many organisms toward deeper water

Darkness:
- lowers predator visibility
- enables safer feeding near the surface
- triggers upward migration in normal nocturnal DVM

Predation:
- one of the strongest selective pressures behind DVM
- organisms trade feeding opportunity against survival risk
- migration depth can increase when predator pressure is high

Energy conservation:
- deeper, colder water can reduce metabolic cost
- organisms may conserve energy by remaining deeper when feeding benefit is low
- migration itself has a cost, so movement must produce net benefit

Environmental pressure:
- oxygen, temperature, salinity, turbulence, moonlight, ice cover, and artificial
  light can modify migration depth and timing
- strong stratification can limit vertical movement
- low oxygen can make deep layers costly even when they are safer

Network and ecosystem conditions:
- DVM couples surface and deep food webs
- predators may track migrating prey
- carbon and nutrients are moved downward through feeding, respiration, and waste
- local ecosystem state changes whether upward movement is beneficial

## Adaptive Behavior Pattern

DVM is not a simple clock. It is a recurring decision pattern shaped by:

- time of day
- light field
- risk level
- energy cost
- food availability
- physical constraints
- ecosystem feedback

The organism chooses a layer that balances opportunity and risk. That balance
can shift daily, seasonally, and geographically.

## AI Architecture Analogies

Deep mode:
- local/cache-first behavior
- low token usage
- reduced external calls
- conservative operation under pressure
- analogous to organisms staying deeper during high-risk daylight

Surface mode:
- high reasoning behavior
- greater external provider use
- broader context gathering
- higher token and compute cost
- analogous to organisms moving upward when opportunity outweighs risk

Transition mode, future phase:
- possible intermediate routing layer
- useful when conditions are mixed
- not implemented in this first step

Environmental pressure, future phase:
- network latency
- provider availability
- token budget
- local cache confidence
- user urgency
- system load

## First Implementation Report

Implemented foundation:
- created `adaptive_routing/`
- added this DVM research document
- added `routing_modes.json` with minimal routing mode definitions
- added `circadian_router.py` with local-hour based routing

Current router behavior:
- `18:00` through `23:00` maps to `deep_mode`
- all other hours map to `surface_mode`

Design constraints respected:
- no external APIs
- no autonomous agents
- no backend rewrite
- no vector database
- no distributed infrastructure
- no application-wide integration yet

Next safe expansion:
- add optional network-pressure input
- add optional token-budget input
- add tests once the routing contract is stable
- integrate into the main runtime only after explicit approval

