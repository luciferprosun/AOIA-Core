# DEV-TOOLS-2 IOA Lab Clone Report

## Phase

DEV-TOOLS-2 - IOA Lab Clone Main Version / AOIA Hologram Workspace

## Repository State

- Repository: `/home/l/Desktop/AOIA-Core`
- Branch: `dev/gt-runtime-8-bash-safety-planning`
- Base HEAD before DEV-TOOLS-2 commit: `fa15330 feat: add DEV-TOOLS-1 terminal provider switcher`
- GT-RUNTIME-8 status: closed
- GT-RUNTIME-9 status: not started
- Cloudflare stash: untouched

## Scope

This checkpoint adds a local lab clone utility and docs:

- `scripts/dev/create_ioa_lab_clone.py`
- `docs/dev/IOA_LAB_CLONE_QUICKSTART.md`
- `docs/audit/DEV_TOOLS_2_IOA_LAB_CLONE_REPORT.md`

The utility creates or inspects:

- Production/source-of-truth repo: `/home/l/Desktop/AOIA-Core`
- Lab root: `/home/l/Desktop/IOA-LAB`
- Hologram clone target: `/home/l/Desktop/IOA-LAB/IOA-Lab-Klon-Main-Version`

## Safety Boundary

This work is not GT-RUNTIME-9 and does not modify AOIA runtime behavior.

No capability was added for:

- autonomous command execution
- model-output execution
- browser automation
- OAuth or login handling
- API credential storage
- background daemon operation
- GUI or web app operation
- sudo usage
- destructive cleanup
- production GitHub pushes from the lab clone

## Remote Safety Design

When `--init --copy-current-repo` is used, the utility creates a local no-hardlink Git clone from AOIA-Core into the hologram target. It then sets the lab clone's `origin` push URL to:

```text
DISABLED_IOA_LAB_HOLOGRAM_NO_PRODUCTION_PUSH
```

When `--disable-remote` is also passed, the utility removes `origin` from the lab clone.

The utility refuses to overwrite a non-empty non-Git hologram target and does not implement cleanup or deletion behavior. If the hologram target already exists as a Git repository, the utility reports the existing clone and leaves it intact.

## Supported Commands

```bash
python3 scripts/dev/create_ioa_lab_clone.py --status
python3 scripts/dev/create_ioa_lab_clone.py --dry-run
python3 scripts/dev/create_ioa_lab_clone.py --init
python3 scripts/dev/create_ioa_lab_clone.py --init --copy-current-repo
python3 scripts/dev/create_ioa_lab_clone.py --init --copy-current-repo --disable-remote
```

## Files Intentionally Not Modified

- Runtime files
- Tests
- Bash Safety parser
- `event_ledger.py`
- `shell_tools.py`
- Executor files
- Provider/routing runtime
- Cloudflare files
- `docs/future`
- NiFe runtime/planning docs
- GT-RUNTIME-9 files

## Validation Result

Validated on June 3, 2026:

- Static AST parse: PASS
- `--status`: PASS
- `--dry-run`: PASS
- `--dry-run --copy-current-repo`: PASS
- `--dry-run --copy-current-repo --disable-remote`: PASS
- `--init`: PASS; created or confirmed `/home/l/Desktop/IOA-LAB`.
- `--init --copy-current-repo`: PASS; existing Git hologram was reported without overwrite.
- `--init --copy-current-repo --disable-remote`: PASS; existing Git hologram was reported without overwrite and had no origin remote.
- Initial clone creation: PASS; hologram clone created at `/home/l/Desktop/IOA-LAB/IOA-Lab-Klon-Main-Version`.
- Hologram remote safety: PASS; `origin` was removed after clone creation.
- Hologram status after validation: clean at `fa15330`.
- Production repo dirty state during validation was limited to the staged DEV-TOOLS-2 files.
- Cloudflare stash remained untouched.

## Result

DEV-TOOLS-2 establishes the IOA lab hologram workspace mechanism. Future model-assisted experiments can be pointed at the lab clone while AOIA-Core remains the production source of truth.
