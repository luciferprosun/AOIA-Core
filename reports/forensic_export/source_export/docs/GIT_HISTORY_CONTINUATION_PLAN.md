# Git History Continuation Plan

## Goal

Continue AOIA as a standalone runtime and infrastructure project.

## Immediate state

- This repository was physically extracted into a dedicated git root.
- Commit ancestry from the prior runtime repo is documented but was not replayed into this new root during extraction.

## Recommended continuation

1. Treat this root as the forward AOIA implementation authority.
2. Preserve references to prior runtime commits and reports externally.
3. If needed later, replay selected implementation history from `app2terminl_opened` with `git filter-repo` or subtree import.
4. Keep generated runtime state out of canonical source history.
