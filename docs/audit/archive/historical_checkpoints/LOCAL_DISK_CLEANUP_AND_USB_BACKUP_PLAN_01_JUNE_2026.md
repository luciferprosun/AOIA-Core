# Local Disk Cleanup and USB Backup Plan - 01 June 2026

## Purpose
Record the safe local disk inspection, USB backup preparation, and clone planning performed on 01 June 2026.

## Internal Disk Usage Summary
- Host: `l`
- Kernel: `Linux l 6.17.0-23-generic #23~24.04.1-Ubuntu SMP PREEMPT_DYNAMIC Tue Apr 14 16:11:48 UTC 2 x86_64 GNU/Linux`
- Internal root/home filesystem: `/dev/mmcblk0p2`
- Internal filesystem usage: `57G` total, `51G` used, `3.7G` available, `94%` used.
- Home top-level total from `du`: about `13G`.
- Desktop total: about `1.3G`.
- Downloads total: about `230M`.
- Cache total: about `1.6G`.

## USB Mountpoint
- Confirmed USB data mountpoint: `/media/l/LSC_DATA1`
- Device/partition: `/dev/sda3`
- Label: `LSC_DATA`
- Filesystem: `ext4`
- USB data partition usage: `419G` total, `26G` used, `372G` available, `7%` used.
- Additional USB buffer partition observed: `/media/l/LSC_BUF1`.

## Backup Root Path
- `/media/l/LSC_DATA1/AIOA_SYSTEM_BACKUP_2026-06-01`

## What Was Copied
- Copied with `rsync`, without `--delete`:
  - `/home/l/Desktop/AOIA-Core/`
  - destination: `/media/l/LSC_DATA1/AIOA_SYSTEM_BACKUP_2026-06-01/projects/AOIA-Core/`
  - rsync transferred about `265M`.

## What Was Not Copied
- `/home/l/Documents/` was dry-run only; it appeared empty.
- `/home/l/Downloads/` was not copied automatically because it requires manual review before backup/cleanup.
- Full `/home/l/Desktop/` was not copied automatically because it contains multiple unrelated folders and should be reviewed before bulk copy.
- No browser profiles, SSH keys, GPG keys, `.config`, `.local/share`, or secrets were copied separately beyond what exists inside the AOIA-Core repository backup.

## Inventory Reports Saved To USB
- `reports/lsblk_f.txt`
- `reports/lsblk_full.txt`
- `reports/df_h.txt`
- `reports/home_du.txt`
- `reports/desktop_du.txt`
- `reports/downloads_du.txt`
- `reports/cache_du.txt`
- `reports/CLEANUP_CANDIDATES.md`
- `reports/SYSTEM_CLONE_PLAN.md`

## Cleanup Candidates
- `/var/cache/apt`: about `1.8G`.
- `/home/l/.cache`: about `1.6G`.
- `/home/l/.cache/google-chrome`: about `1.3G`.
- `/home/l/.npm`: about `729M`.
- `/home/l/Downloads`: about `230M`, manual review required.
- No `/home/l` files over `500M` were reported by the read-only large-file scan.

## Safe Later Cleanup Commands
These commands were not run. They require explicit user confirmation before any cleanup:

```bash
du -sh ~/.cache ~/.cache/google-chrome ~/.cache/mozilla ~/.npm /var/cache/apt 2>/dev/null
find ~/Downloads -maxdepth 1 -type f -printf '%s\t%p\n' 2>/dev/null | sort -n | tail -50
sudo apt clean
npm cache clean --force
find ~/.cache/thumbnails -type f -delete
```

Chrome cache cleanup should be done through browser UI first or only after Chrome is closed and the user explicitly confirms the exact cache paths.

## Clone Plan
- No clone was performed.
- Recommended near-term strategy: continue file-level backups with `rsync`.
- Full disk clone should use Clonezilla from a live USB if needed.
- Raw `dd` or `ddrescue` must not be executed without exact source/target confirmation and explicit user approval.

## Safety Confirmations
- No deletion was performed.
- No disk clone was performed.
- No formatting was performed.
- No repartitioning was performed.
- No `dd` command was run.
- No project repositories were removed.
- No home directory data was removed.
- No secrets, configs, SSH keys, API keys, or browser profiles were removed.
- No `sudo` write action was performed.

## Recommended Next Manual Step
Review `/media/l/LSC_DATA1/AIOA_SYSTEM_BACKUP_2026-06-01/reports/CLEANUP_CANDIDATES.md`, then explicitly choose one small cleanup action, preferably `sudo apt clean` or browser cache cleanup, after confirming current backups are sufficient.
