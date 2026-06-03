# IOA Lab Clone Quickstart

## Scope

`scripts/dev/create_ioa_lab_clone.py` creates and inspects a local IOA lab hologram workspace for AOIA-Core.

- Production/source-of-truth repo: `/home/l/Desktop/AOIA-Core`
- Lab root: `/home/l/Desktop/IOA-LAB`
- Hologram clone target: `/home/l/Desktop/IOA-LAB/IOA-Lab-Klon-Main-Version`

This is DEV-TOOLS-2. It is not GT-RUNTIME-9, not autonomous execution, not browser automation, not OAuth, and not Cloudflare work.

## Boundary

The tool does not add:

- autonomous command running
- model-output execution
- browser automation
- login or OAuth handling
- API credential storage
- background daemon behavior
- GUI or web app behavior
- sudo usage
- destructive cleanup

## Commands

Inspect current production and lab state:

```bash
python3 scripts/dev/create_ioa_lab_clone.py --status
```

Preview lab-root creation:

```bash
python3 scripts/dev/create_ioa_lab_clone.py --dry-run
```

Create the lab root only:

```bash
python3 scripts/dev/create_ioa_lab_clone.py --init
```

Create the lab root and a local hologram clone:

```bash
python3 scripts/dev/create_ioa_lab_clone.py --init --copy-current-repo
```

Create the lab root and hologram clone, then remove `origin` from the lab clone:

```bash
python3 scripts/dev/create_ioa_lab_clone.py --init --copy-current-repo --disable-remote
```

## Remote Safety

When a hologram clone is created, the tool first blocks push behavior by setting the clone's `origin` push URL to:

```text
DISABLED_IOA_LAB_HOLOGRAM_NO_PRODUCTION_PUSH
```

When `--disable-remote` is also passed, the tool removes `origin` entirely from the lab clone after cloning.

This keeps the lab clone from accidentally pushing to the production GitHub remote. Production AOIA-Core remains untouched.

## Existing Target Behavior

The tool refuses to overwrite an existing non-empty non-Git hologram target. It does not delete, reset, or clean existing files.

If the hologram target already exists as a Git repository, the tool reports the existing clone and leaves it intact. If that existing clone still has `origin`, the tool can still block its push URL or remove `origin` when `--disable-remote` is passed.

If the lab clone already exists, inspect it with:

```bash
python3 scripts/dev/create_ioa_lab_clone.py --status
```

Manual cleanup, if ever needed, should be a separate explicit operator action outside this utility.
