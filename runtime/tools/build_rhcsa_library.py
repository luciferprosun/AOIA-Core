#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
from pathlib import Path
from textwrap import dedent
from typing import Any

from runtime.safety.subprocess_env import build_subprocess_env
from runtime.safety.bounded_subprocess import (
    SUBPROCESS_HARD_TIMEOUT_REASON_CODE,
    SubprocessResourceProfileName,
    run_bounded_subprocess,
)


CATEGORIES = [
    "commands",
    "manpages",
    "recovery",
    "lvm",
    "storage",
    "networking",
    "systemd",
    "selinux",
    "users_permissions",
    "bash",
    "podman",
    "scripting",
    "troubleshooting",
    "boot",
    "security",
    "ssh",
    "cron",
    "logs",
    "packages",
    "archives",
    "summaries",
    "indexes",
    "json_indexes",
    "workflows",
    "examples",
    "sources",
]

RHCSA_MANPAGE_HARD_TIMEOUT_SECONDS = 20
RHCSA_HELP_HARD_TIMEOUT_SECONDS = 15


class RhcsaUtilityHardTimeoutError(RuntimeError):
    """An RHCSA documentation utility exceeded its hard process deadline."""

    reason_code = SUBPROCESS_HARD_TIMEOUT_REASON_CODE

    def __init__(self, operation: str) -> None:
        self.operation = operation
        super().__init__(
            f"{self.reason_code}: RHCSA utility timed out during {operation} "
            "and was terminated"
        )

MANPAGE_COMMANDS = [
    "awk",
    "bash",
    "blkid",
    "cat",
    "chmod",
    "chown",
    "cp",
    "crontab",
    "df",
    "dnf",
    "du",
    "find",
    "findmnt",
    "firewall-cmd",
    "grep",
    "groupadd",
    "grub2-mkconfig",
    "ip",
    "journalctl",
    "ln",
    "ls",
    "lsblk",
    "lsof",
    "lvcreate",
    "lvdisplay",
    "lvextend",
    "lvremove",
    "lvresize",
    "man",
    "mkdir",
    "mkfs",
    "mkfs.ext4",
    "mkfs.xfs",
    "mount",
    "mv",
    "nmcli",
    "passwd",
    "podman",
    "ps",
    "pvcreate",
    "pvdisplay",
    "restorecon",
    "rm",
    "rsync",
    "sed",
    "semanage",
    "setenforce",
    "setfacl",
    "ssh",
    "ss",
    "sudo",
    "systemctl",
    "tar",
    "timedatectl",
    "umount",
    "useradd",
    "usermod",
    "vgcreate",
    "vgdisplay",
    "xfs_growfs",
]

PUBLIC_SOURCE_REGISTRY = [
    {
        "name": "Red Hat documentation",
        "url": "https://docs.redhat.com",
        "kind": "official_docs",
        "usage": "Reference source for RHEL administration concepts. Fetch only public pages.",
    },
    {
        "name": "Red Hat Customer Portal public documentation",
        "url": "https://access.redhat.com/documentation",
        "kind": "official_docs",
        "usage": "Reference source for public RHEL guides. Do not bypass authentication.",
    },
    {
        "name": "Fedora Docs",
        "url": "https://docs.fedoraproject.org",
        "kind": "official_docs",
        "usage": "Reference source for Fedora/RHEL-adjacent administration workflows.",
    },
    {
        "name": "GNU Coreutils Manual",
        "url": "https://www.gnu.org/software/coreutils/manual/",
        "kind": "official_docs",
        "usage": "Reference source for GNU userspace command semantics.",
    },
    {
        "name": "The Linux Documentation Project",
        "url": "https://tldp.org",
        "kind": "public_docs",
        "usage": "Reference source for public Linux administration HOWTOs.",
    },
    {
        "name": "waseem-h/rhcsa-cheatsheet",
        "url": "https://github.com/waseem-h/rhcsa-cheatsheet",
        "kind": "github_reference",
        "usage": "Candidate public cheat sheet. Verify license before mirroring content.",
    },
    {
        "name": "Jani-shiv/rhcsa-study-guide",
        "url": "https://github.com/Jani-shiv/rhcsa-study-guide",
        "kind": "github_reference",
        "usage": "Candidate public RHCSA guide. Verify license before mirroring content.",
    },
    {
        "name": "RamtinTJB/RHCSA9-Notes",
        "url": "https://github.com/RamtinTJB/RHCSA9-Notes",
        "kind": "github_reference",
        "usage": "Candidate public notes. Verify license before mirroring content.",
    },
    {
        "name": "RHCSA/RHCSA.github.io",
        "url": "https://github.com/RHCSA/RHCSA.github.io",
        "kind": "github_reference",
        "usage": "Candidate public course site. Verify license before mirroring content.",
    },
    {
        "name": "fdicarlo/RHCSA_cs",
        "url": "https://github.com/fdicarlo/RHCSA_cs",
        "kind": "github_reference",
        "usage": "Candidate public cheat sheet. Verify license before mirroring content.",
    },
    {
        "name": "ivanmorenoj/RHCSA-Notes",
        "url": "https://github.com/ivanmorenoj/RHCSA-Notes",
        "kind": "github_reference",
        "usage": "Candidate public notes. Verify license before mirroring content.",
    },
]


def topic(
    category: str,
    filename: str,
    title: str,
    keywords: list[str],
    commands: list[str],
    related: list[str],
    body: str,
    phase: str,
) -> dict[str, Any]:
    return {
        "category": category,
        "filename": filename,
        "topic": title,
        "keywords": keywords,
        "commands": commands,
        "related_topics": related,
        "body": dedent(body).strip(),
        "phase": phase,
    }


TOPICS = [
    topic(
        "commands",
        "core_command_operations.txt",
        "Core Linux Command Operations",
        ["ls", "cp", "mv", "rm", "find", "grep", "tar", "rsync", "inspection"],
        ["ls -la", "cp -a SRC DST", "mv OLD NEW", "find /etc -name '*.conf'", "grep -R PATTERN /etc", "tar -tvf archive.tar"],
        ["Bash Safety Patterns", "Filesystem Management"],
        """
        Core command work starts with observation, then controlled modification.

        Operational workflow:
        1. Confirm current directory with pwd.
        2. Inspect target with ls -la or ls -ld.
        3. Use find/grep for discovery.
        4. Copy with metadata preservation when backing up.
        5. Make one change.
        6. Verify result.

        Troubleshooting:
        - If a path is unexpected, use readlink -f and namei -l.
        - If a recursive command is needed, inspect the target first.
        - If a command produces too much output, pipe to less or narrow with grep.

        Safe notes:
        - Never generate destructive commands without an explicit absolute path.
        - Prefer dry inspection commands before rm, chmod -R, chown -R, mkfs, or dd.
        """,
        "phase_1_core_commands",
    ),
    topic(
        "bash",
        "bash_safety_patterns.txt",
        "Bash Safety Patterns",
        ["bash", "set -euo pipefail", "variables", "loops", "quoting", "automation"],
        ["bash -n script.sh", "set -euo pipefail", "for item in *; do printf '%s\\n' \"$item\"; done"],
        ["Core Linux Command Operations", "Cron and Timers"],
        """
        RHCSA-level scripting should be predictable and easy to review.

        Recommended script skeleton:
        - Use #!/usr/bin/env bash.
        - Use set -euo pipefail for strict mode when appropriate.
        - Quote variable expansions.
        - Validate input paths before using them.
        - Log each operational step.

        Troubleshooting:
        - Use bash -n for syntax checks.
        - Use set -x only for temporary tracing.
        - Check exit codes and stderr before continuing.

        Safe notes:
        - Avoid eval.
        - Avoid unbounded globs in destructive operations.
        """,
        "phase_8_bash_automation",
    ),
    topic(
        "systemd",
        "systemd_service_management.txt",
        "Systemd Service Management",
        ["systemd", "systemctl", "service", "unit", "enable", "restart", "daemon-reload"],
        ["systemctl status sshd", "systemctl enable --now firewalld", "systemctl list-units --failed", "systemctl daemon-reload"],
        ["Journalctl Log Analysis", "Boot Targets and Recovery"],
        """
        Systemd manages services, targets, timers, sockets, and mounts. The normal RHCSA service flow is inspect, change, reload if needed, restart, verify.

        Operational workflow:
        1. systemctl status NAME
        2. systemctl cat NAME
        3. Edit config or unit override.
        4. systemctl daemon-reload if a unit file changed.
        5. systemctl restart NAME
        6. systemctl status NAME
        7. journalctl -u NAME -b

        Troubleshooting:
        - Failed services: systemctl list-units --failed.
        - Unit dependency issue: systemctl list-dependencies NAME.
        - Config failure: inspect service-specific validation commands before restart.

        Safe notes:
        - Restarting sshd or network services can disconnect remote sessions.
        """,
        "phase_2_systemd_services",
    ),
    topic(
        "logs",
        "journalctl_log_analysis.txt",
        "Journalctl Log Analysis",
        ["journalctl", "logs", "boot", "errors", "service troubleshooting"],
        ["journalctl -b", "journalctl -u sshd -b", "journalctl -p err -b", "journalctl -xe"],
        ["Systemd Service Management", "Troubleshooting Decision Tree"],
        """
        Logs are the first evidence source after status checks. Use journalctl to narrow by boot, unit, priority, and time window.

        Operational workflow:
        1. journalctl -b
        2. journalctl -u SERVICE -b
        3. journalctl -p err -b
        4. journalctl --since '10 min ago'
        5. Match log evidence to the last configuration change.

        Troubleshooting:
        - If logs are empty, verify the unit name.
        - If persistent logs are needed, inspect /var/log/journal.
        - Use dmesg for kernel/device level issues.
        """,
        "phase_2_systemd_services",
    ),
    topic(
        "networking",
        "networkmanager_nmcli_workflows.txt",
        "NetworkManager and nmcli Workflows",
        ["nmcli", "NetworkManager", "ip", "dns", "route", "connection", "interface"],
        ["nmcli device status", "nmcli connection show", "nmcli connection up NAME", "ip addr show", "ip route"],
        ["SSH Troubleshooting", "Firewalld Operations"],
        """
        RHEL networking is normally persistent through NetworkManager connection profiles. nmcli separates runtime device state from persistent profile configuration.

        Operational workflow:
        1. nmcli device status
        2. nmcli connection show
        3. ip addr show
        4. ip route
        5. nmcli connection show NAME
        6. Modify the profile.
        7. nmcli connection up NAME

        Troubleshooting:
        - Device name and connection profile name may differ.
        - Current kernel networking state can differ from saved profile state.
        - DNS failures require checking DNS servers and name resolution separately.

        Safe notes:
        - Do not change remote network settings without a rollback path.
        """,
        "phase_3_networking",
    ),
    topic(
        "ssh",
        "ssh_troubleshooting.txt",
        "SSH Troubleshooting",
        ["ssh", "sshd", "systemctl", "firewall", "keys", "permissions"],
        ["systemctl status sshd", "journalctl -u sshd -b", "ssh -vvv user@host", "ss -tulpn | grep :22"],
        ["NetworkManager and nmcli Workflows", "Users Groups Permissions"],
        """
        SSH troubleshooting combines service state, listener state, firewall rules, user permissions, and key file permissions.

        Operational workflow:
        1. systemctl status sshd
        2. ss -tulpn | grep :22
        3. firewall-cmd --list-services
        4. journalctl -u sshd -b
        5. ssh -vvv user@host from the client.

        Common fixes:
        - ~/.ssh must usually be 700 and authorized_keys 600.
        - sshd_config changes require config validation and service restart.
        - SELinux context can block unusual key or chroot paths.
        """,
        "phase_3_networking",
    ),
    topic(
        "security",
        "firewalld_operations.txt",
        "Firewalld Operations",
        ["firewalld", "firewall-cmd", "zone", "service", "port", "runtime", "permanent"],
        ["firewall-cmd --state", "firewall-cmd --get-active-zones", "firewall-cmd --add-service=http --permanent", "firewall-cmd --reload"],
        ["NetworkManager and nmcli Workflows", "SSH Troubleshooting"],
        """
        Firewalld has runtime and permanent configuration. RHCSA tasks normally require making changes persistent and then reloading.

        Operational workflow:
        1. firewall-cmd --state
        2. firewall-cmd --get-active-zones
        3. firewall-cmd --list-all
        4. firewall-cmd --add-service=SERVICE --permanent
        5. firewall-cmd --reload
        6. firewall-cmd --list-services

        Safe notes:
        - Do not remove ssh access from a remote system.
        - Prefer service names over raw ports when available.
        """,
        "phase_3_networking",
    ),
    topic(
        "storage",
        "filesystem_management.txt",
        "Filesystem Management",
        ["mount", "umount", "fstab", "xfs", "ext4", "blkid", "findmnt"],
        ["lsblk -f", "blkid", "findmnt", "mount -a", "xfs_growfs MOUNTPOINT"],
        ["LVM Creation Workflow", "Boot Targets and Recovery"],
        """
        Filesystem work requires identifying the block device, filesystem type, mountpoint, and persistence in /etc/fstab.

        Operational workflow:
        1. lsblk -f
        2. blkid
        3. mkdir -p /mountpoint
        4. mount DEVICE /mountpoint
        5. Add UUID-based entry to /etc/fstab.
        6. mount -a
        7. findmnt /mountpoint

        Troubleshooting:
        - A bad /etc/fstab entry can break boot.
        - Use mount -a immediately after editing fstab.
        - XFS grows online but does not shrink.

        Safe notes:
        - mkfs destroys existing filesystem data.
        """,
        "phase_4_storage_lvm",
    ),
    topic(
        "lvm",
        "lvm_creation_and_resize.txt",
        "LVM Creation and Resize Workflow",
        ["lvm", "pvcreate", "vgcreate", "lvcreate", "lvextend", "xfs_growfs", "resize2fs"],
        ["pvcreate /dev/sdb1", "vgcreate vgdata /dev/sdb1", "lvcreate -n lvdata -L 5G vgdata", "lvextend -r -L +1G /dev/vgdata/lvdata"],
        ["Filesystem Management", "Storage Recovery Procedures"],
        """
        LVM separates physical volumes, volume groups, and logical volumes. Use pvs, vgs, and lvs to verify each layer.

        Creation workflow:
        1. lsblk
        2. pvcreate /dev/DEVICE
        3. vgcreate VG /dev/DEVICE
        4. lvcreate -n LV -L SIZE VG
        5. mkfs.xfs /dev/VG/LV
        6. mount and persist with /etc/fstab.

        Resize workflow:
        1. lvs
        2. vgs
        3. lvextend -r -L +SIZE /dev/VG/LV
        4. df -h

        Safe notes:
        - Confirm device names before pvcreate.
        - Prefer lvextend -r to resize filesystem and LV together when supported.
        """,
        "phase_4_storage_lvm",
    ),
    topic(
        "selinux",
        "selinux_contexts_and_booleans.txt",
        "SELinux Contexts and Booleans",
        ["SELinux", "getenforce", "sestatus", "restorecon", "semanage", "boolean", "context"],
        ["getenforce", "sestatus", "ls -Z /path", "restorecon -Rv /path", "semanage fcontext -a -t TYPE '/path(/.*)?'"],
        ["SSH Troubleshooting", "Firewalld Operations"],
        """
        SELinux failures often look like normal permission problems. Check Unix permissions and SELinux labels together.

        Operational workflow:
        1. getenforce
        2. sestatus
        3. ls -Z TARGET
        4. restorecon -Rv TARGET
        5. semanage fcontext -a -t TYPE 'PATH_REGEX'
        6. restorecon -Rv TARGET

        Troubleshooting:
        - Use audit logs for AVC denials where available.
        - Prefer fixing contexts or booleans instead of disabling SELinux.
        - setenforce 0 is temporary diagnostic mode, not a permanent fix.
        """,
        "phase_5_selinux",
    ),
    topic(
        "users_permissions",
        "users_groups_permissions_acl.txt",
        "Users Groups Permissions and ACLs",
        ["useradd", "usermod", "passwd", "chmod", "chown", "setfacl", "getfacl", "sudo"],
        ["useradd alice", "passwd alice", "usermod -aG wheel alice", "chmod 640 file", "chown user:group file", "setfacl -m u:alice:rwx file"],
        ["SSH Troubleshooting", "Bash Safety Patterns"],
        """
        User access depends on identity, group membership, path traversal permissions, file modes, ACLs, sudoers rules, and sometimes SELinux.

        Operational workflow:
        1. id USER
        2. groups USER
        3. namei -l /path/to/file
        4. ls -l /path/to/file
        5. getfacl /path/to/file
        6. Apply minimal chmod/chown/setfacl change.

        Safe notes:
        - usermod -aG appends groups; missing -a replaces supplementary groups.
        - Directory execute bit allows traversal.
        """,
        "phase_6_users_permissions",
    ),
    topic(
        "boot",
        "boot_targets_and_recovery.txt",
        "Boot Targets and Recovery",
        ["boot", "rescue", "emergency", "grub", "rd.break", "fstab", "password reset"],
        ["systemctl rescue", "systemctl emergency", "journalctl -xb", "mount -o remount,rw /", "grub2-mkconfig -o /boot/grub2/grub.cfg"],
        ["Filesystem Management", "Journalctl Log Analysis"],
        """
        Recovery work should identify the boot failure class first: broken fstab, missing service, bad kernel/initramfs, bootloader issue, or authentication recovery.

        Operational workflow:
        1. Enter rescue or emergency mode.
        2. journalctl -xb.
        3. Check /etc/fstab and mount -a.
        4. Remount root writable only when required.
        5. Fix one cause.
        6. Reboot and verify.

        Safe notes:
        - Bootloader commands vary by BIOS/UEFI and distribution version.
        - Always identify root filesystem and boot mode before GRUB repair.
        """,
        "phase_7_recovery_troubleshooting",
    ),
    topic(
        "troubleshooting",
        "troubleshooting_decision_tree.txt",
        "Troubleshooting Decision Tree",
        ["troubleshooting", "logs", "service", "network", "storage", "permissions", "selinux"],
        ["systemctl status SERVICE", "journalctl -u SERVICE -b", "ip addr show", "lsblk -f", "getenforce"],
        ["Journalctl Log Analysis", "SELinux Contexts and Booleans", "Filesystem Management"],
        """
        Use a stable troubleshooting loop: observe, narrow, change one thing, verify, document.

        Decision tree:
        - Service down: systemctl status, journalctl -u, config validation.
        - Network down: nmcli device, ip addr, ip route, DNS, firewall.
        - Access denied: id, namei -l, ls -l, getfacl, ls -Z.
        - Disk issue: lsblk -f, findmnt, df -h, journalctl -p err.
        - Boot issue: journalctl -xb, fstab, rescue target.

        Safe notes:
        - Do not stack multiple unknown changes.
        - Keep before/after evidence.
        """,
        "phase_7_recovery_troubleshooting",
    ),
    topic(
        "cron",
        "cron_and_systemd_timers.txt",
        "Cron and Systemd Timers",
        ["cron", "crontab", "systemd timer", "automation", "schedule"],
        ["crontab -l", "crontab -e", "systemctl list-timers", "systemctl status NAME.timer"],
        ["Bash Safety Patterns", "Systemd Service Management"],
        """
        Scheduled automation can use cron or systemd timers. Cron is simple; timers integrate with systemd logs and dependency handling.

        Operational workflow:
        1. Identify owner and schedule requirement.
        2. Use absolute paths in scripts.
        3. Log output.
        4. Test command manually.
        5. Add schedule.
        6. Verify logs after next run.

        Troubleshooting:
        - Cron has a limited environment.
        - Use full paths for commands.
        - Check mail/log destination or journal for timer output.
        """,
        "phase_8_bash_automation",
    ),
    topic(
        "podman",
        "podman_operational_basics.txt",
        "Podman Operational Basics",
        ["podman", "container", "image", "volume", "logs", "rootless"],
        ["podman images", "podman ps -a", "podman run --rm IMAGE", "podman logs CONTAINER", "podman inspect CONTAINER"],
        ["SELinux Contexts and Booleans", "Firewalld Operations"],
        """
        Podman is daemonless and supports rootless containers. Operational tasks focus on images, containers, logs, ports, volumes, and SELinux labels.

        Operational workflow:
        1. podman images
        2. podman ps -a
        3. podman logs CONTAINER
        4. podman inspect CONTAINER
        5. Validate bind mount labels and port mappings.

        Troubleshooting:
        - Rootless and rootful storage/networking differ.
        - Bind mounts may need SELinux label options.
        - Container logs are first evidence source.
        """,
        "phase_9_podman",
    ),
    topic(
        "packages",
        "dnf_package_management.txt",
        "DNF Package Management",
        ["dnf", "yum", "rpm", "repositories", "packages", "updates"],
        ["dnf search NAME", "dnf info PACKAGE", "dnf install PACKAGE", "dnf history", "rpm -qa"],
        ["Systemd Service Management", "Troubleshooting Decision Tree"],
        """
        Package work should identify package name, repository availability, dependencies, and transaction history.

        Operational workflow:
        1. dnf search NAME
        2. dnf info PACKAGE
        3. dnf install PACKAGE
        4. rpm -ql PACKAGE
        5. dnf history

        Troubleshooting:
        - Check repository configuration and network/DNS if package metadata fails.
        - Use dnf history to review or undo transactions where supported.
        """,
        "phase_1_core_commands",
    ),
]

WORKFLOWS = [
    {
        "topic": "safe_file_edit_workflow",
        "category": "workflows",
        "filename": "safe_file_edit_workflow.md",
        "keywords": ["backup", "edit", "config", "verify"],
        "commands": ["cp -a FILE FILE.bak", "systemctl reload SERVICE", "journalctl -u SERVICE -b"],
        "related_topics": ["Systemd Service Management", "Troubleshooting Decision Tree"],
        "summary": "Create backup, edit one config, validate, reload/restart, verify logs.",
        "steps": [
            "Inspect file path and owner.",
            "Create timestamped backup with cp -a.",
            "Edit only the required setting.",
            "Run service-specific config validation if available.",
            "Reload or restart service.",
            "Verify status and logs.",
        ],
    },
    {
        "topic": "new_lvm_mount_workflow",
        "category": "workflows",
        "filename": "new_lvm_mount_workflow.md",
        "keywords": ["lvm", "mount", "fstab", "filesystem"],
        "commands": ["lsblk", "pvcreate", "vgcreate", "lvcreate", "mkfs.xfs", "mount -a"],
        "related_topics": ["LVM Creation and Resize Workflow", "Filesystem Management"],
        "summary": "Create PV/VG/LV, filesystem, mountpoint, fstab entry, and verify.",
        "steps": [
            "Identify unused block device with lsblk.",
            "Create PV, VG, and LV.",
            "Create filesystem.",
            "Create mountpoint.",
            "Mount temporarily.",
            "Persist by UUID in /etc/fstab.",
            "Run mount -a and findmnt.",
        ],
    },
    {
        "topic": "ssh_access_repair_workflow",
        "category": "workflows",
        "filename": "ssh_access_repair_workflow.md",
        "keywords": ["ssh", "sshd", "firewall", "permissions", "keys"],
        "commands": ["systemctl status sshd", "journalctl -u sshd -b", "ss -tulpn | grep :22", "ssh -vvv user@host"],
        "related_topics": ["SSH Troubleshooting", "Firewalld Operations"],
        "summary": "Check sshd, listener, firewall, account, permissions, key files, and logs.",
        "steps": [
            "Check sshd status.",
            "Check port listener.",
            "Check firewall zone/service.",
            "Check user account and shell.",
            "Check ~/.ssh permissions.",
            "Use ssh -vvv from client.",
        ],
    },
]

EXAMPLES = [
    {
        "topic": "gemma_json_action_examples",
        "category": "examples",
        "filename": "gemma_json_action_examples.md",
        "keywords": ["Gemma", "JSON", "actions", "approval"],
        "commands": ["mkdir -p PATH", "systemctl status SERVICE", "journalctl -u SERVICE -b"],
        "summary": "Safe examples of JSON actions that Gemma can propose for human approval.",
        "content": """
        # Gemma JSON Action Examples

        Gemma should generate one action at a time and never assume execution.

        ```json
        {"action":"shell_execute","command":"systemctl status sshd","reason":"Inspect sshd service before changing it."}
        ```

        ```json
        {"action":"create_folder","path":"/home/l/Desktop/test_ai","reason":"Create requested project folder."}
        ```

        ```json
        {"action":"shell_execute","command":"journalctl -u sshd -b --no-pager","reason":"Collect sshd logs for troubleshooting."}
        ```
        """,
    },
    {
        "topic": "safe_linux_command_templates",
        "category": "examples",
        "filename": "safe_linux_command_templates.md",
        "keywords": ["templates", "safe commands", "inspection", "verification"],
        "commands": ["lsblk -f", "findmnt", "systemctl status SERVICE", "journalctl -u SERVICE -b"],
        "summary": "Reusable Linux command templates for safe operational work.",
        "content": """
        # Safe Linux Command Templates

        Inspection:
        - `pwd`
        - `ls -la PATH`
        - `lsblk -f`
        - `findmnt TARGET`

        Service:
        - `systemctl status SERVICE`
        - `journalctl -u SERVICE -b --no-pager`

        Network:
        - `nmcli device status`
        - `ip addr show`
        - `ip route`

        Permissions:
        - `id USER`
        - `namei -l PATH`
        - `getfacl PATH`
        """,
    },
]


def detect_storage_root() -> Path:
    removable_candidates = [
        Path(f"/media/{os.getenv('USER', 'l')}/LSC_DATA"),
        Path(f"/media/{os.getenv('USER', 'l')}/LSC_DATA1"),
        Path("/mnt/LSC_DATA"),
    ]
    fallback_candidates = [
        Path.home() / "USB_STORAGE",
        Path.home() / "knowledge_archive",
    ]
    for candidate in removable_candidates:
        if not candidate.exists():
            continue
        try:
            test = candidate / ".rhcsa_write_test"
            test.write_text("ok", encoding="utf-8")
            test.unlink()
            return candidate
        except OSError:
            continue
    for candidate in fallback_candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            test = candidate / ".rhcsa_write_test"
            test.write_text("ok", encoding="utf-8")
            test.unlink()
            return candidate
        except OSError:
            continue
    fallback = Path.home() / "knowledge_archive"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def build_library() -> Path:
    root = detect_storage_root() / "RHCSA_LIBRARY"
    for category in CATEGORIES:
        (root / category).mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, Any]] = []
    for item in TOPICS:
        path = root / item["category"] / item["filename"]
        write_text_and_markdown(path, render_topic(item))
        entries.append(index_entry(item, path, "topic", first_sentence(item["body"])))

    for item in WORKFLOWS:
        path = root / item["category"] / item["filename"]
        content = render_workflow(item)
        path.write_text(content, encoding="utf-8")
        entries.append(index_entry(item, path, "workflow", item["summary"]))

    for item in EXAMPLES:
        path = root / item["category"] / item["filename"]
        path.write_text(dedent(item["content"]).strip() + "\n", encoding="utf-8")
        entries.append(index_entry(item, path, "example", item["summary"]))

    manpage_count = export_manpages(root)
    write_source_registry(root)
    write_indexes(root, entries)
    write_summaries(root, entries)
    write_reports(root, entries, manpage_count)
    write_archive(root)
    write_project_structure(root)
    write_reports(root, entries, manpage_count)
    return root


def write_text_and_markdown(txt_path: Path, content: str) -> None:
    txt_path.write_text(content, encoding="utf-8")
    md_path = txt_path.with_suffix(".md")
    md_path.write_text(content, encoding="utf-8")


def render_topic(item: dict[str, Any]) -> str:
    return dedent(
        f"""
        # {item['topic']}

        Phase:
        {item['phase']}

        Source basis:
        - Local Linux manpages and command help exports
        - Public GNU/Linux command behavior
        - Public Red Hat/Fedora administration concepts
        - Original operational summary generated for this legal offline vault

        Keywords:
        {', '.join(item['keywords'])}

        Related commands:
        {chr(10).join(f'- {command}' for command in item['commands'])}

        Related topics:
        {chr(10).join(f'- {topic_name}' for topic_name in item['related_topics'])}

        {item['body']}
        """
    ).strip() + "\n"


def render_workflow(item: dict[str, Any]) -> str:
    return dedent(
        f"""
        # {item['topic']}

        Summary:
        {item['summary']}

        Keywords:
        {', '.join(item['keywords'])}

        Commands:
        {chr(10).join(f'- {command}' for command in item['commands'])}

        Related topics:
        {chr(10).join(f'- {topic_name}' for topic_name in item['related_topics'])}

        Steps:
        {chr(10).join(f'{index}. {step}' for index, step in enumerate(item['steps'], start=1))}
        """
    ).strip() + "\n"


def index_entry(item: dict[str, Any], path: Path, entry_type: str, summary: str) -> dict[str, Any]:
    return {
        "topic": item["topic"],
        "type": entry_type,
        "keywords": item.get("keywords", []),
        "commands": item.get("commands", []),
        "related_topics": item.get("related_topics", []),
        "source_file": str(path),
        "file_location": str(path),
        "category": item["category"],
        "summary": summary,
    }


def first_sentence(text: str) -> str:
    compact = " ".join(dedent(text).strip().split())
    return compact.split(".")[0] + "." if "." in compact else compact[:180]


def export_manpages(root: Path) -> int:
    count = 0
    for command in MANPAGE_COMMANDS:
        output = export_single_manpage(command)
        if not output:
            continue
        target = manpage_target(root, command)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(output + "\n", encoding="utf-8", errors="ignore")
        md_target = target.with_suffix(".md")
        md_target.write_text(f"# `{command}` reference\n\n```text\n{output}\n```\n", encoding="utf-8", errors="ignore")
        count += 1
    return count


def export_single_manpage(command: str) -> str:
    if shutil.which("man") and shutil.which("col"):
        try:
            result = run_bounded_subprocess(
                ["bash", "-lc", f"man {command} | col -b"],
                text=True,
                capture_output=True,
                check=False,
                env=build_subprocess_env(),
                timeout=RHCSA_MANPAGE_HARD_TIMEOUT_SECONDS,
                resource_profile=SubprocessResourceProfileName.INTERNAL_UTILITY,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RhcsaUtilityHardTimeoutError("manpage export") from exc
        if result.stdout.strip():
            return result.stdout.strip()
    executable = command.split(".", 1)[0]
    if shutil.which(executable):
        try:
            result = run_bounded_subprocess(
                [executable, "--help"],
                text=True,
                capture_output=True,
                check=False,
                env=build_subprocess_env(),
                timeout=RHCSA_HELP_HARD_TIMEOUT_SECONDS,
                resource_profile=SubprocessResourceProfileName.INTERNAL_UTILITY,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RhcsaUtilityHardTimeoutError("help export") from exc
        return (result.stdout or result.stderr).strip()
    return ""


def manpage_target(root: Path, command: str) -> Path:
    category_map = {
        "systemctl": "systemd",
        "journalctl": "logs",
        "nmcli": "networking",
        "ip": "networking",
        "ss": "networking",
        "ssh": "ssh",
        "dnf": "packages",
        "lvcreate": "lvm",
        "lvdisplay": "lvm",
        "lvextend": "lvm",
        "lvremove": "lvm",
        "lvresize": "lvm",
        "pvcreate": "lvm",
        "pvdisplay": "lvm",
        "vgcreate": "lvm",
        "vgdisplay": "lvm",
        "mount": "storage",
        "umount": "storage",
        "findmnt": "storage",
        "mkfs": "storage",
        "mkfs.ext4": "storage",
        "mkfs.xfs": "storage",
        "xfs_growfs": "storage",
        "restorecon": "selinux",
        "semanage": "selinux",
        "setenforce": "selinux",
        "useradd": "users_permissions",
        "usermod": "users_permissions",
        "groupadd": "users_permissions",
        "passwd": "users_permissions",
        "setfacl": "users_permissions",
        "bash": "bash",
        "crontab": "cron",
        "podman": "podman",
        "grub2-mkconfig": "boot",
    }
    directory = category_map.get(command, "manpages")
    safe_name = command.replace("/", "_")
    return root / directory / f"{safe_name}_manpage.txt"


def write_source_registry(root: Path) -> None:
    (root / "sources" / "public_sources_registry.json").write_text(
        json.dumps(PUBLIC_SOURCE_REGISTRY, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    lines = [
        "# Knowledge Sources",
        "",
        "This vault intentionally avoids pirated books, paid course dumps, exam dumps, torrents, and authentication bypasses.",
        "",
        "Current build mode:",
        "- Generated original operational summaries.",
        "- Exported local man/help references.",
        "- Registered public source candidates for future license-checked incremental fetching.",
        "- External downloaded topics in this build: 0.",
        "",
        "Allowed source registry:",
    ]
    for source in PUBLIC_SOURCE_REGISTRY:
        lines.append(f"- {source['name']}: {source['url']} ({source['kind']})")
    (root / "KNOWLEDGE_SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_indexes(root: Path, entries: list[dict[str, Any]]) -> None:
    for index_dir in ("indexes", "json_indexes"):
        (root / index_dir / "rhcsa_master_index.json").write_text(
            json.dumps(entries, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    command_index: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        for command in entry["commands"]:
            base = command.split()[0]
            command_index.setdefault(base, []).append(
                {
                    "command": command,
                    "topic": entry["topic"],
                    "keywords": entry["keywords"],
                    "related_topics": entry["related_topics"],
                    "source_file": entry["source_file"],
                    "summary": entry["summary"],
                }
            )

    index_payloads = {
        "commands_index.json": command_index,
        "command_index.json": command_index,
        "troubleshooting_index.json": filter_entries(entries, {"troubleshooting", "logs", "recovery", "boot", "selinux", "networking", "ssh"}),
        "workflows_index.json": [entry for entry in entries if entry["type"] == "workflow"],
        "networking_index.json": filter_entries(entries, {"networking", "ssh", "security"}),
        "selinux_index.json": filter_entries(entries, {"selinux"}),
        "storage_index.json": filter_entries(entries, {"storage", "lvm"}),
        "recovery_index.json": filter_entries(entries, {"recovery", "boot", "troubleshooting"}),
        "examples_index.json": [entry for entry in entries if entry["type"] == "example"],
    }
    for filename, payload in index_payloads.items():
        for index_dir in ("indexes", "json_indexes"):
            (root / index_dir / filename).write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )


def filter_entries(entries: list[dict[str, Any]], categories: set[str]) -> list[dict[str, Any]]:
    return [entry for entry in entries if entry["category"] in categories]


def write_summaries(root: Path, entries: list[dict[str, Any]]) -> None:
    lines = ["# RHCSA Local Library Summary", ""]
    for entry in entries:
        lines.append(f"- {entry['topic']} [{entry['category']}]: {entry['summary']}")
    (root / "summaries" / "rhcsa_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_reports(root: Path, entries: list[dict[str, Any]], manpage_count: int) -> None:
    files = [path for path in root.rglob("*") if path.is_file()]
    total_size = sum(path.stat().st_size for path in files)
    command_examples = sum(len(entry["commands"]) for entry in entries)
    categories = sorted({entry["category"] for entry in entries})

    topic_lines = ["# RHCSA Topic Map", ""]
    for entry in entries:
        topic_lines.append(f"## {entry['topic']}")
        topic_lines.append(f"- Type: {entry['type']}")
        topic_lines.append(f"- Category: {entry['category']}")
        topic_lines.append(f"- File: {entry['source_file']}")
        topic_lines.append(f"- Keywords: {', '.join(entry['keywords'])}")
        topic_lines.append(f"- Commands: {', '.join(entry['commands'])}")
        topic_lines.append(f"- Related topics: {', '.join(entry['related_topics'])}")
        topic_lines.append("")
    (root / "RHCSA_TOPIC_MAP.md").write_text("\n".join(topic_lines), encoding="utf-8")

    report = dedent(
        f"""
        # RHCSA Library Report

        Generated: {dt.datetime.now().isoformat()}

        Storage path:
        `{root}`

        Build mode:
        Step-by-step legal offline operational vault.

        External downloaded topics:
        0

        Generated original operational topics:
        {len([entry for entry in entries if entry['type'] == 'topic'])}

        Generated workflows:
        {len([entry for entry in entries if entry['type'] == 'workflow'])}

        Generated examples:
        {len([entry for entry in entries if entry['type'] == 'example'])}

        Exported local man/help pages:
        {manpage_count}

        Indexed command examples:
        {command_examples}

        Total files:
        {len(files)}

        Storage size bytes:
        {total_size}

        Search coverage:
        {', '.join(categories)}

        Gemini integration points:
        - `memory/rhcsa_context.py`
        - `tools/rhcsa_search.py`
        - `summaries/rhcsa_summary.md`
        - `json_indexes/troubleshooting_index.json`
        - `json_indexes/workflows_index.json`

        Gemma operational integration points:
        - `json_indexes/commands_index.json`
        - `examples/gemma_json_action_examples.md`
        - `examples/safe_linux_command_templates.md`
        - exported local man/help files
        - operational workflows requiring human approval before execution
        """
    ).strip()
    (root / "RHCSA_LIBRARY_REPORT.md").write_text(report + "\n", encoding="utf-8")

    storage = dedent(
        f"""
        # Storage Report

        Active vault path:
        `{root}`

        Total files:
        {len(files)}

        Size:
        {total_size} bytes

        Preferred storage detection order:
        - /media/$USER/LSC_DATA
        - /media/$USER/LSC_DATA1
        - /mnt/LSC_DATA
        - ~/USB_STORAGE
        - ~/knowledge_archive

        Current policy:
        Completeness and readability are preferred over aggressive compression.
        """
    ).strip()
    (root / "STORAGE_REPORT.md").write_text(storage + "\n", encoding="utf-8")

    token_plan = dedent(
        """
        # Token Savings Plan

        Before using Gemini or external web search:
        1. Search `json_indexes/rhcsa_master_index.json`.
        2. Search `json_indexes/commands_index.json`.
        3. Search `json_indexes/workflows_index.json`.
        4. Load only the top matching topic or workflow.
        5. Give Gemini summaries and decision trees, not full manpages.
        6. Give Gemma command patterns, examples, and operational snippets only.

        Expected savings:
        - Gemini avoids repeated Linux explanations.
        - Gemma receives local command examples for JSON action generation.
        - External APIs are used only when local knowledge is insufficient or fresh information is required.
        """
    ).strip()
    (root / "TOKEN_SAVINGS_PLAN.md").write_text(token_plan + "\n", encoding="utf-8")


def write_archive(root: Path) -> None:
    archive_path = root / "archives" / f"rhcsa_library_snapshot_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.make_archive(str(archive_path), "gztar", root_dir=root, base_dir=".")


def write_project_structure(root: Path) -> None:
    lines = [str(root)]
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        depth = len(relative.parts) - 1
        marker = "  " * depth + ("- " if path.is_file() else "+ ")
        lines.append(f"{marker}{relative}")
    (root / "UPDATED_PROJECT_STRUCTURE.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    print(build_library())
