# AOIA Step 2 - Environmental Network Patterns

## Scope

This is a lightweight environmental awareness foundation for future adaptive
routing. It does not monitor live networks, call external APIs, or optimize
production traffic. It documents broad static patterns that can later inform
local-first routing decisions.

## Regional Traffic Patterns

Europe:
- work traffic commonly rises during business hours
- consumer traffic often peaks in the evening after work
- streaming, gaming, and social use commonly increase from 18:00 to 22:00
- low-traffic windows are usually late night to early morning, around 01:00 to
  05:00 local time

USA:
- business traffic follows local office hours across time zones
- residential traffic often peaks from late afternoon into evening
- streaming and gaming load commonly increases from 17:00 to 21:00 local time
- low-traffic windows are usually around 02:00 to 05:00 local time

Asia:
- usage varies strongly by country and time zone
- dense urban regions can show strong evening entertainment peaks
- mobile-first usage can keep traffic elevated later into the night
- low-traffic windows often occur around 02:00 to 05:00 local time

South America:
- work and education traffic often rises during daytime
- entertainment and messaging traffic commonly increases in the evening
- peak consumer windows often sit around 18:00 to 22:00 local time
- lower traffic commonly appears after midnight through early morning

## Infrastructure Windows

Nighttime and early morning windows are often better suited for heavier local
workloads because user demand is lower. Future AOIA routing can use these
windows for cache refresh, batch analysis, index updates, or provider-heavy
reasoning when those actions become explicitly integrated.

## AI Infrastructure Analogies

High traffic:
- conserve tokens
- prefer local cache
- delay heavy external work when possible
- avoid broad context expansion

Low traffic:
- allow deeper reasoning
- allow batch preparation
- allow larger cache maintenance tasks
- prepare knowledge for later peak windows

## Step 2 Implementation Report

Implemented:
- `adaptive_routing/environment/network_patterns.md`
- `adaptive_routing/environment/traffic_profiles.json`
- `adaptive_routing/environment/environment_router.py`

Routing logic:
- lookup the requested region in static local profiles
- if the hour is in `peak_hours`, return `high_traffic`
- if the hour is in `off_peak_hours`, return `low_traffic`
- otherwise return `low_traffic` for this first prototype

Constraints respected:
- no live monitoring
- no external APIs
- no backend integration
- no autonomous actions
- no analytics dashboard

