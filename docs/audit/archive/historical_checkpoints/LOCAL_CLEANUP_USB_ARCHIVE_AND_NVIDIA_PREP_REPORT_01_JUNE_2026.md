# Local Cleanup USB Archive and NVIDIA Prep Report — 01 June 2026

## USB and Archive Paths
- USB mountpoint: `/media/l/LSC_DATA1`
- Backup root: `/media/l/LSC_DATA1/AIOA_SYSTEM_ARCHIVE_2026-06-01`
- USB trash path: `/media/l/LSC_DATA1/AIOA_USB_TRASH_2026-06-01`
- AOIA-Core backup path: `/media/l/LSC_DATA1/AIOA_SYSTEM_ARCHIVE_2026-06-01/projects/AOIA-Core`

## Internal Disk Usage
- Before archive moves: `/dev/mmcblk0p2` `57G` total, `50G` used, `3.7G` free, `94%` used
- After archive moves: `/dev/mmcblk0p2` `57G` total, `50G` used, `4.1G` free, `93%` used

## AOIA-Core
- AOIA-Core remained local at `/home/l/Desktop/AOIA-Core`
- AOIA-Core was backed up to USB with `rsync`
- Local AOIA-Core was not moved or deleted

## Old Repos Moved to USB
- `/home/l/Desktop/app2terminl_opened`
- `/home/l/Desktop/LSC-Research`
- `/home/l/Desktop/MHLM_MDLH`
- `/home/l/Desktop/luciferBOT`
- `/home/l/Desktop/agent lilly 3`

Each item was copied to the USB archive, then moved into the USB trash/quarantine area, and a local `__MOVED_TO_USB.txt` pointer file was left on Desktop.

## Old Archives Moved to USB
- `AOIA-Recovery-Archive-2026-05-26`
- `AOIA-Recovery-Archive-2026-05-30`
- `AOIA_28_MAY_SESSION_ARCHIVE`
- `AOIA_TUI_PHASE3_WIP_BACKUP_28_MAY`
- `KRKN_GT6_BACKUP_20260527T134758Z`
- `raporty z calrgo repo po V2`
- `kopia biblioteki rhcsa`
- `MHLM_MDLH_Ultra_Master_Library_2026-05-26_v2`
- `kopia biblioteki rhcsa.zip`
- `kopia_biblioteki_rhcsa_JEDEN_MARKDOWN.md`
- `prezentacja.md`
- `prezentacja.pdf`

## Downloads
- Large old Downloads report written to `/media/l/LSC_DATA1/AIOA_SYSTEM_ARCHIVE_2026-06-01/reports/downloads_large_old_files.txt`
- No qualifying Downloads files were moved in this task

## Cache Cleanup
- Cache usage was inspected and reported
- No direct cache deletion was executed in this task
- Main later-review candidates: `~/.cache/google-chrome`, `~/.npm`, `/var/cache/apt`

## NVIDIA Local Feasibility
- Weak local hardware remains a constraint
- No local NVIDIA GPU detected
- No full NeMo installation performed
- No Docker pull performed
- Documentation-only scaffold created at `experiments/nemo_guardrails_probe/`
- This scaffold is not runtime-integrated and requires explicit approval before any install

## Safety Confirmations
- No full NeMo installed
- No Docker pull performed
- No disk clone performed
- No formatting or repartitioning performed
- No permanent deletion of user projects performed
- No runtime/provider/router/executor/Memory Hats runtime code was modified

## Restore Instructions
1. Open the local Desktop `__MOVED_TO_USB.txt` pointer file for the item you want to restore.
2. Copy the corresponding directory or file back from the USB archive or USB trash path to Desktop.
3. Verify restored contents before removing any pointer file.
