# Tooling And Execution

Execution engine, shell/filesystem/browser adapters, validators, and local tools.

Commit: `04adfbdb5a6b34d2969d67ac7e84c704c8e0915a`

Files in this chunk: 12

## `runtime/tools/__init__.py`

- size: 50 bytes
- sha256: `e3e2fa3a3a5c2056cc16a3e364c2fef5b8ce607d7aef0ce43396d64d6207f259`
- category: tooling

```python
"""Tool layer for the local AI terminal agent."""
```

## `runtime/tools/browser_tools.py`

- size: 10150 bytes
- sha256: `3b7838e75a6f4b5053b2551492ca1df611897ca7d9e1ea06b574f71808107b57`
- category: tooling

```python
from __future__ import annotations

import time
from pathlib import Path

try:
    from playwright.sync_api import BrowserContext, Page, TimeoutError, sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when Playwright is absent
    BrowserContext = Page = object  # type: ignore[assignment]
    TimeoutError = RuntimeError  # type: ignore[assignment]
    sync_playwright = None  # type: ignore[assignment]
    PLAYWRIGHT_AVAILABLE = False


class BrowserBridge:
    """Persistent Playwright bridge kept alive across agent actions."""

    def __init__(
        self,
        user_data_dir: Path,
        screenshots_dir: Path,
        headless: bool = True,
        timeout_ms: int = 15000,
    ) -> None:
        self.user_data_dir = user_data_dir
        self.screenshots_dir = screenshots_dir
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.playwright = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.last_selector: str | None = None

    def browser_start(self) -> dict:
        """Start Playwright and keep a persistent browser context alive."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not installed. Install requirements to enable browser tools.")
        if self.context is not None:
            return self._state_message("Browser session already running.")

        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        self.playwright = sync_playwright().start()
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.user_data_dir),
            headless=self.headless,
            viewport={"width": 1440, "height": 900},
            accept_downloads=False,
            chromium_sandbox=False,
            args=["--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        self.context.set_default_timeout(self.timeout_ms)

        if self.context.pages:
            self.page = self.context.pages[-1]
        else:
            self.page = self.context.new_page()
            self.page.goto("about:blank", wait_until="domcontentloaded")

        self._wait_for_page_ready(self.page)
        return self._state_message("Browser session started.")

    def browser_open(self, url: str) -> dict:
        """Open a URL in the current page."""
        page = self._ensure_page()
        page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
        self._wait_for_page_ready(page)
        self.last_selector = None
        return self._state_message(f"Opened {url}")

    def browser_click(self, selector: str) -> dict:
        """Click a visible element with retries and post-click waits."""
        page = self._ensure_page()
        locator = self._find_selector(page, selector)
        locator.click(timeout=self.timeout_ms)
        page.wait_for_timeout(350)
        self._wait_for_page_ready(page)
        self.last_selector = selector
        return self._state_message(f"Clicked {selector}")

    def browser_type(self, selector: str, text: str) -> dict:
        """Type or fill text into an input field."""
        page = self._ensure_page()
        locator = self._find_selector(page, selector)
        try:
            locator.fill(text, timeout=self.timeout_ms)
            locator.evaluate("element => element.focus()")
        except TimeoutError:
            locator.evaluate("element => element.focus()")
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.keyboard.type(text, delay=25)
        self.last_selector = selector
        return self._state_message(f"Typed into {selector}")

    def browser_press(self, key: str) -> dict:
        """Press one keyboard key on the active page."""
        page = self._ensure_page()
        if self.last_selector:
            try:
                locator = self._find_selector(page, self.last_selector)
                locator.press(key, timeout=self.timeout_ms)
            except TimeoutError:
                page.keyboard.press(key)
        else:
            page.keyboard.press(key)
        page.wait_for_timeout(300)
        self._wait_for_page_ready(page)
        return self._state_message(f"Pressed {key}")

    def browser_read_html(self) -> dict:
        """Return full HTML for the current page."""
        page = self._ensure_page()
        html = page.content()
        return {
            **self._state_message("Read current page HTML."),
            "html": html,
        }

    def browser_get_visible_text(self) -> dict:
        """Return visible body text from the current page."""
        page = self._ensure_page()
        text = page.locator("body").inner_text(timeout=self.timeout_ms)
        return {
            **self._state_message("Read visible page text."),
            "text": text,
        }

    def browser_screenshot(self, path: str | None = None) -> dict:
        """Save a screenshot of the current page."""
        page = self._ensure_page()
        if path:
            screenshot_path = Path(path).expanduser()
            if not screenshot_path.is_absolute():
                screenshot_path = self.screenshots_dir / screenshot_path
        else:
            timestamp = int(time.time() * 1000)
            screenshot_path = self.screenshots_dir / f"screenshot_{timestamp}.png"

        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot_path), full_page=True)
        return {
            **self._state_message(f"Saved screenshot to {screenshot_path}"),
            "screenshot_path": str(screenshot_path),
        }

    def browser_current_url(self) -> dict:
        """Return the current page URL."""
        page = self._ensure_page()
        return {
            **self._state_message("Read current browser URL."),
            "current_url": page.url,
        }

    def browser_close(self) -> dict:
        """Close the persistent browser session cleanly."""
        if self.context is not None:
            self.context.close()
        if self.playwright is not None:
            self.playwright.stop()
        self.context = None
        self.page = None
        self.playwright = None
        self.last_selector = None
        return {
            "success": True,
            "message": "Browser session closed.",
            "current_url": "",
            "open_tabs": [],
        }

    # -----------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------
    def _ensure_page(self) -> Page:
        if self.context is None:
            self.browser_start()
        assert self.context is not None

        if self.page is not None and not self.page.is_closed():
            return self.page

        if self.context.pages:
            self.page = self.context.pages[-1]
        else:
            self.page = self.context.new_page()
            self.page.goto("about:blank", wait_until="domcontentloaded")
        return self.page

    def _wait_for_page_ready(self, page: Page) -> None:
        for state in ("domcontentloaded", "load"):
            try:
                page.wait_for_load_state(state, timeout=self.timeout_ms)
            except TimeoutError:
                pass
        page.wait_for_timeout(250)

    def _find_selector(self, page: Page, selector: str):
        last_error: Exception | None = None
        for _ in range(3):
            locator = page.locator(selector).first
            try:
                locator.wait_for(state="visible", timeout=self.timeout_ms)
                return locator
            except TimeoutError as error:
                last_error = error
                page.wait_for_timeout(400)
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"Selector not found: {selector}")

    def _state_message(self, message: str) -> dict:
        page = self.page
        current_url = ""
        if page is not None and not page.is_closed():
            current_url = page.url
        tabs = []
        if self.context is not None:
            tabs = [candidate.url for candidate in self.context.pages if not candidate.is_closed()]
        return {
            "success": True,
            "message": message,
            "current_url": current_url,
            "open_tabs": tabs,
        }


_BROWSER_BRIDGE: BrowserBridge | None = None


def configure_browser_bridge(
    user_data_dir: Path,
    screenshots_dir: Path,
    headless: bool = True,
    timeout_ms: int = 15000,
) -> None:
    """Bind the module-level browser bridge used by tool functions."""
    global _BROWSER_BRIDGE
    _BROWSER_BRIDGE = BrowserBridge(
        user_data_dir=user_data_dir,
        screenshots_dir=screenshots_dir,
        headless=headless,
        timeout_ms=timeout_ms,
    )


def get_browser_bridge() -> BrowserBridge:
    """Return the configured browser bridge."""
    if _BROWSER_BRIDGE is None:
        raise RuntimeError("Browser bridge is not configured.")
    return _BROWSER_BRIDGE


def browser_start() -> dict:
    return get_browser_bridge().browser_start()


def browser_open(url: str) -> dict:
    return get_browser_bridge().browser_open(url)


def browser_click(selector: str) -> dict:
    return get_browser_bridge().browser_click(selector)


def browser_type(selector: str, text: str) -> dict:
    return get_browser_bridge().browser_type(selector, text)


def browser_press(key: str) -> dict:
    return get_browser_bridge().browser_press(key)


def browser_read_html() -> dict:
    return get_browser_bridge().browser_read_html()


def browser_get_visible_text() -> dict:
    return get_browser_bridge().browser_get_visible_text()


def browser_screenshot(path: str | None = None) -> dict:
    return get_browser_bridge().browser_screenshot(path)


def browser_close() -> dict:
    return get_browser_bridge().browser_close()


def browser_current_url() -> dict:
    return get_browser_bridge().browser_current_url()
```

## `runtime/tools/build_rhcsa_library.py`

- size: 40708 bytes
- sha256: `e545762a03831471c5c73ba99ad7e6f4c90f7d23516ab06edebae328b49f7efb`
- category: tooling

```python
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
        result = subprocess.run(
            ["bash", "-lc", f"man {command} | col -b"],
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )
        if result.stdout.strip():
            return result.stdout.strip()
    executable = command.split(".", 1)[0]
    if shutil.which(executable):
        result = subprocess.run(
            [executable, "--help"],
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )
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
```

## `runtime/tools/executor.py`

- size: 8928 bytes
- sha256: `b91a9d63b2a794f10110d3a8ad05b8c9d8aadf8caae65394fcc911eb41f0f21a`
- category: tooling

```python
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .browser_tools import (
    browser_click,
    browser_close,
    browser_current_url,
    browser_get_visible_text,
    browser_open,
    browser_press,
    browser_read_html,
    browser_screenshot,
    browser_start,
    browser_type,
    configure_browser_bridge,
)
from .filesystem_tools import (
    append_file,
    create_file,
    create_folder,
    delete_file,
    move_file,
    read_file,
    resolve_path,
    search_in_project,
    write_file,
)
from .memory import MemoryStore
from .project_scanner import scan_project
from .shell_tools import shell_execute
from .validator import classify_shell_command, validate_shell_command


ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ToolSpec:
    """Runtime tool metadata used by the executor registry."""

    name: str
    handler: ToolHandler
    description: str


class ExecutionEngine:
    """Dispatch structured tool actions to shell, filesystem, or browser."""

    def __init__(self, project_dir: Path, memory_store: MemoryStore) -> None:
        self.project_dir = project_dir
        self.memory_store = memory_store
        self.cwd = Path(memory_store.memory.cwd)
        self.command_log_dir = memory_store.paths.command_logs_dir
        configure_browser_bridge(
            user_data_dir=memory_store.paths.state_dir / "browser_profile",
            screenshots_dir=memory_store.paths.screenshots_dir,
            headless=True,
        )
        self.tools = self._build_tool_registry()

    def tool_names(self) -> list[str]:
        return sorted(self.tools)

    def execute(self, action: dict[str, Any], require_approval: bool = True) -> dict[str, Any]:
        """Execute one validated JSON action."""
        name = action["action"]
        tool = self.tools.get(name)
        if tool is None:
            raise ValueError(f"Unhandled action: {name}")

        if require_approval and name != "respond":
            approved = self._request_approval(action)
            if not approved:
                result = {
                    "success": False,
                    "cancelled": True,
                    "message": "Action rejected by user.",
                    "action": name,
                }
                self._record_execution(action, result)
                return result

        result = tool.handler(action)
        self._record_execution(action, result)
        return result

    def _build_tool_registry(self) -> dict[str, ToolSpec]:
        return {
            "respond": ToolSpec("respond", self._respond, "Return a final answer."),
            "shell_execute": ToolSpec("shell_execute", self._execute_shell_action, "Run a validated shell command."),
            "write_file": ToolSpec("write_file", lambda action: write_file(action["path"], action["content"], self.cwd), "Write a text file."),
            "append_file": ToolSpec("append_file", lambda action: append_file(action["path"], action["content"], self.cwd), "Append to a text file."),
            "read_file": ToolSpec("read_file", lambda action: read_file(action["path"], self.cwd), "Read a text file."),
            "create_file": ToolSpec("create_file", lambda action: create_file(action["path"], self.cwd, action["content"]), "Create a file."),
            "create_folder": ToolSpec("create_folder", lambda action: create_folder(action["path"], self.cwd), "Create a folder."),
            "move_file": ToolSpec("move_file", lambda action: move_file(action["src"], action["dst"], self.cwd), "Move a file or folder."),
            "delete_file": ToolSpec("delete_file", lambda action: delete_file(action["path"], self.cwd), "Delete a file or empty folder."),
            "search_in_project": ToolSpec("search_in_project", lambda action: search_in_project(action["pattern"], action["path"], self.cwd), "Search text in project files."),
            "change_directory": ToolSpec("change_directory", lambda action: self._change_directory(action["path"]), "Change runtime directory."),
            "browser_start": ToolSpec("browser_start", lambda action: browser_start(), "Start browser session."),
            "browser_open": ToolSpec("browser_open", lambda action: browser_open(action["url"]), "Open a URL."),
            "browser_click": ToolSpec("browser_click", lambda action: browser_click(action["selector"]), "Click an element."),
            "browser_type": ToolSpec("browser_type", lambda action: browser_type(action["selector"], action["text"]), "Type into an element."),
            "browser_press": ToolSpec("browser_press", lambda action: browser_press(action["key"]), "Press a key."),
            "browser_read_html": ToolSpec("browser_read_html", lambda action: browser_read_html(), "Read current page HTML."),
            "browser_get_visible_text": ToolSpec("browser_get_visible_text", lambda action: browser_get_visible_text(), "Read visible page text."),
            "browser_screenshot": ToolSpec("browser_screenshot", lambda action: browser_screenshot(action.get("path") or None), "Save browser screenshot."),
            "browser_close": ToolSpec("browser_close", lambda action: browser_close(), "Close browser session."),
            "browser_current_url": ToolSpec("browser_current_url", lambda action: browser_current_url(), "Read current browser URL."),
            "scan_project": ToolSpec("scan_project", lambda action: scan_project(action["path"], self.cwd), "Scan a repository or project tree."),
        }

    @staticmethod
    def _respond(action: dict[str, Any]) -> dict[str, Any]:
        return {
            "success": True,
            "message": action["message"],
            "confidence_label": action.get("confidence_label", "unknown"),
            "stop_loop": True,
        }

    def _execute_shell_action(self, action: dict[str, Any]) -> dict[str, Any]:
        command = action["command"]
        allowed, reason = validate_shell_command(command)
        if not allowed:
            return {
                "success": False,
                "command": command,
                "message": f"Command blocked by validator: {reason}",
            }

        permission = classify_shell_command(command)
        if permission.interactive:
            print("[INFO] Interactive command may ask for password or package confirmation.")

        self.memory_store.record_command(command)
        return {
            **shell_execute(command, self.cwd, interactive=permission.interactive),
            "permission_mode": permission.mode,
            "permission_reason": permission.reason,
        }

    def _request_approval(self, action: dict[str, Any]) -> bool:
        print("\nPROPOSED ACTION")
        print(f"Action: {action['action']}")
        if action.get("reason"):
            print(f"Reason: {action['reason']}")
        for field in ("command", "path", "src", "dst", "url", "selector", "key"):
            if field in action and action[field]:
                print(f"{field}: {action[field]}")
        answer = input("Press ENTER to approve, or type n/cancel to reject: ").strip().lower()
        return answer not in {"n", "no", "cancel", "reject", "stop"}

    def _change_directory(self, path_text: str) -> dict:
        target = resolve_path(path_text, self.cwd)
        if not target.exists() or not target.is_dir():
            return {
                "success": False,
                "path": str(target),
                "message": f"Directory does not exist: {target}",
            }
        self.cwd = target
        self.memory_store.update_cwd(target)
        return {
            "success": True,
            "path": str(target),
            "message": f"Current directory changed to {target}",
        }

    def _record_execution(self, action: dict[str, Any], result: dict[str, Any]) -> None:
        payload = {
            "timestamp": dt.datetime.now().isoformat(),
            "authority": {
                "classification": "operational_event",
                "retention": "replay_only",
                "non_authoritative": True,
                "canonical_evidence": False,
            },
            "action": action,
            "result": result,
            "cwd": str(self.cwd),
        }
        filename = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f.json")
        (self.command_log_dir / filename).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self.memory_store.record_result(result)
        self.memory_store.append_history("action_result", payload)
        # AOIA Phase 2A containment boundary
        # Runtime operational outputs must NEVER become canonical evidence.
        if action["action"].startswith("browser_"):
            self.memory_store.append_browser_event(payload)
```

## `runtime/tools/filesystem_tools.py`

- size: 4101 bytes
- sha256: `dff0e15f0f51ee025c5d4f0d8bd4b45f5b7e2c6cb91284727b1795f8f8aff0b7`
- category: tooling

```python
from __future__ import annotations

import shutil
from pathlib import Path


def resolve_path(path_text: str, cwd: Path) -> Path:
    """Resolve user-provided paths against the current working directory."""
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = cwd / path
    return path.resolve()


def ensure_parent(path: Path) -> None:
    """Create parent directories before writing files."""
    path.parent.mkdir(parents=True, exist_ok=True)


def create_folder(path_text: str, cwd: Path) -> dict:
    """Create a directory and verify it exists."""
    path = resolve_path(path_text, cwd)
    path.mkdir(parents=True, exist_ok=True)
    return {
        "success": path.exists() and path.is_dir(),
        "path": str(path),
        "message": f"Folder ready at {path}",
    }


def create_file(path_text: str, cwd: Path, content: str = "") -> dict:
    """Create a new text file with optional initial content."""
    path = resolve_path(path_text, cwd)
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")
    return {
        "success": True,
        "path": str(path),
        "bytes_written": len(content.encode("utf-8")),
        "message": f"Created file {path}",
    }


def write_file(path_text: str, content: str, cwd: Path) -> dict:
    """Overwrite a text file with exact content."""
    path = resolve_path(path_text, cwd)
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")
    return {
        "success": True,
        "path": str(path),
        "bytes_written": len(content.encode("utf-8")),
        "message": f"Wrote file {path}",
    }


def append_file(path_text: str, content: str, cwd: Path) -> dict:
    """Append text content to an existing file."""
    path = resolve_path(path_text, cwd)
    ensure_parent(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(content)
    return {
        "success": True,
        "path": str(path),
        "bytes_written": len(content.encode("utf-8")),
        "message": f"Appended to file {path}",
    }


def read_file(path_text: str, cwd: Path) -> dict:
    """Read a UTF-8 text file."""
    path = resolve_path(path_text, cwd)
    content = path.read_text(encoding="utf-8")
    return {
        "success": True,
        "path": str(path),
        "content": content,
        "message": f"Read file {path}",
    }


def move_file(src_text: str, dst_text: str, cwd: Path) -> dict:
    """Move or rename a file or directory."""
    src = resolve_path(src_text, cwd)
    dst = resolve_path(dst_text, cwd)
    ensure_parent(dst)
    shutil.move(str(src), str(dst))
    return {
        "success": True,
        "src": str(src),
        "dst": str(dst),
        "message": f"Moved {src} to {dst}",
    }


def delete_file(path_text: str, cwd: Path) -> dict:
    """Delete a file or an empty directory."""
    path = resolve_path(path_text, cwd)
    if path.is_dir():
        path.rmdir()
    else:
        path.unlink()
    return {
        "success": True,
        "path": str(path),
        "message": f"Deleted {path}",
    }


def search_in_project(pattern: str, path_text: str, cwd: Path) -> dict:
    """Search for literal text in project files."""
    root = resolve_path(path_text, cwd)
    matches: list[dict] = []

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            if pattern in line:
                matches.append(
                    {
                        "path": str(file_path),
                        "line_number": line_number,
                        "line": line,
                    }
                )
        if len(matches) >= 100:
            break

    return {
        "success": True,
        "root": str(root),
        "pattern": pattern,
        "matches": matches,
        "message": f"Found {len(matches)} matches for {pattern!r}",
    }
```

## `runtime/tools/memory.py`

- size: 10112 bytes
- sha256: `6fc6b06471f559b9f198542738e36f12f216d61c3be0886ab3ea1c92b6e36992`
- category: memory

```python
from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RuntimePaths:
    project_dir: Path
    state_dir: Path
    memory_dir: Path
    screenshots_dir: Path
    browser_logs_dir: Path
    session_logs_dir: Path
    command_logs_dir: Path
    error_logs_dir: Path


@dataclass
class ObsidianVaultPaths:
    vault_dir: Path
    daily_dir: Path
    sessions_dir: Path
    inbox_dir: Path
    projects_dir: Path
    logs_dir: Path
    prompts_dir: Path
    knowledge_dir: Path
    templates_dir: Path
    evidence_dir: Path
    reasoning_dir: Path


@dataclass
class AgentMemory:
    session_id: str
    cwd: str
    current_task: str = ""
    previous_commands: list[str] = field(default_factory=list)
    recent_outputs: list[dict[str, Any]] = field(default_factory=list)
    open_tabs: list[str] = field(default_factory=list)
    current_browser_page: str = ""
    screenshots: list[str] = field(default_factory=list)
    browser_active: bool = False


def build_runtime_paths(project_dir: Path) -> RuntimePaths:
    """Create and return the directory layout for memory, browser, and logs."""
    paths = RuntimePaths(
        project_dir=project_dir,
        state_dir=project_dir / "state",
        memory_dir=project_dir / "memory",
        screenshots_dir=project_dir / "screenshots",
        browser_logs_dir=project_dir / "logs" / "browser",
        session_logs_dir=project_dir / "logs" / "sessions",
        command_logs_dir=project_dir / "logs" / "commands",
        error_logs_dir=project_dir / "logs" / "errors",
    )
    for path in asdict(paths).values():
        if isinstance(path, Path):
            path.mkdir(parents=True, exist_ok=True)
    return paths


def build_obsidian_vault_paths(project_dir: Path) -> ObsidianVaultPaths:
    vault_dir = project_dir / "obsidian_vault"
    paths = ObsidianVaultPaths(
        vault_dir=vault_dir,
        daily_dir=vault_dir / "Daily",
        sessions_dir=vault_dir / "Sessions",
        inbox_dir=vault_dir / "Inbox",
        projects_dir=vault_dir / "Projects",
        logs_dir=vault_dir / "Logs",
        prompts_dir=vault_dir / "Prompts",
        knowledge_dir=vault_dir / "Knowledge",
        templates_dir=vault_dir / "Templates",
        evidence_dir=vault_dir / "Evidence",
        reasoning_dir=vault_dir / "Reasoning",
    )
    for path in asdict(paths).values():
        if isinstance(path, Path):
            path.mkdir(parents=True, exist_ok=True)

    obsidian_config = vault_dir / ".obsidian"
    obsidian_config.mkdir(parents=True, exist_ok=True)
    app_json = obsidian_config / "app.json"
    if not app_json.exists():
        app_json.write_text(
            json.dumps(
                {
                    "theme": "obsidian",
                    "baseFontSize": 16,
                    "accentColor": "",
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    start_here = vault_dir / "00_START_HERE.md"
    if not start_here.exists():
        start_here.write_text(
            "\n".join(
                [
                    "# Obsidian Vault",
                    "",
                    "This vault stores lightweight runtime memory for the local-first agent.",
                    "",
                    "## Layout",
                    "- Daily: append-only day notes",
                    "- Sessions: append-only JSONL session records",
                    "- Inbox: manual captures",
                    "- Projects: active notes",
                ]
            ),
            encoding="utf-8",
        )
    return paths


class MemoryStore:
    """Persist lightweight runtime state to disk after each step."""

    def __init__(self, project_dir: Path, cwd: Path) -> None:
        self.paths = build_runtime_paths(project_dir)
        self.vault_paths = build_obsidian_vault_paths(project_dir)
        self.vault_dir = self.vault_paths.vault_dir
        session_id = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.state_file = self.paths.state_dir / "agent_state.json"
        self.history_file = self.paths.memory_dir / "history.jsonl"
        self.evidence_file = self.paths.memory_dir / "evidence_memory.jsonl"
        self.reasoning_file = self.paths.memory_dir / "reasoning_trace.jsonl"
        self.browser_log_file = self.paths.browser_logs_dir / f"browser_{session_id}.jsonl"
        self.memory = AgentMemory(session_id=session_id, cwd=str(cwd))
        self.save()
        self.append_vault_note(
            "session_start",
            {
                "session_id": session_id,
                "cwd": str(cwd),
            },
        )

    def save(self) -> None:
        self.state_file.write_text(
            json.dumps(asdict(self.memory), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def append_history(self, kind: str, payload: dict[str, Any]) -> None:
        record = {
            "timestamp": dt.datetime.now().isoformat(),
            "kind": kind,
            "payload": payload,
        }
        with self.history_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.append_vault_note(kind, payload)

    def append_evidence(self, kind: str, payload: dict[str, Any]) -> None:
        record = {
            "timestamp": dt.datetime.now().isoformat(),
            "kind": kind,
            "payload": payload,
        }
        with self.evidence_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._append_channel_note(self.vault_paths.evidence_dir, kind, payload)

    def append_reasoning(self, kind: str, payload: dict[str, Any]) -> None:
        record = {
            "timestamp": dt.datetime.now().isoformat(),
            "kind": kind,
            "payload": payload,
        }
        with self.reasoning_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._append_channel_note(self.vault_paths.reasoning_dir, kind, payload)

    def append_browser_event(self, payload: dict[str, Any]) -> None:
        with self.browser_log_file.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "timestamp": dt.datetime.now().isoformat(),
                        "payload": payload,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        self.append_vault_note("browser_event", payload)

    def set_current_task(self, task: str) -> None:
        self.memory.current_task = task
        self.save()

    def update_cwd(self, cwd: Path) -> None:
        self.memory.cwd = str(cwd)
        self.save()

    def record_command(self, command: str) -> None:
        self.memory.previous_commands.append(command)
        self.memory.previous_commands = self.memory.previous_commands[-20:]
        self.save()

    def record_result(self, result: dict[str, Any]) -> None:
        compact = {
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "path": result.get("path"),
            "current_url": result.get("current_url"),
            "exit_code": result.get("exit_code"),
        }
        self.memory.recent_outputs.append(compact)
        self.memory.recent_outputs = self.memory.recent_outputs[-20:]

        if "current_url" in result:
            self.memory.current_browser_page = result.get("current_url", "")
        if "open_tabs" in result:
            self.memory.open_tabs = result.get("open_tabs", [])
            self.memory.browser_active = bool(self.memory.open_tabs or self.memory.current_browser_page)
        if "screenshot_path" in result:
            self.memory.screenshots.append(result["screenshot_path"])
            self.memory.screenshots = self.memory.screenshots[-20:]

        self.save()

    def append_vault_note(self, kind: str, payload: dict[str, Any]) -> None:
        day = dt.datetime.now().strftime("%Y-%m-%d")
        note_path = self.vault_paths.daily_dir / f"{day}.md"
        session_path = self.vault_paths.sessions_dir / f"{self.memory.session_id}.jsonl"
        block = self._vault_block(kind, payload)
        note_path.write_text(
            (note_path.read_text(encoding="utf-8") if note_path.exists() else f"# {day}\n\n")
            + block,
            encoding="utf-8",
        )
        with session_path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "timestamp": dt.datetime.now().isoformat(),
                        "kind": kind,
                        "payload": payload,
                        "cwd": self.memory.cwd,
                        "task": self.memory.current_task,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    def _append_channel_note(self, directory: Path, kind: str, payload: dict[str, Any]) -> None:
        note_path = directory / f"{self.memory.session_id}.md"
        header = f"# {directory.name} {self.memory.session_id}\n\n"
        note_path.write_text(
            (note_path.read_text(encoding="utf-8") if note_path.exists() else header)
            + self._vault_block(kind, payload),
            encoding="utf-8",
        )

    def _vault_block(self, kind: str, payload: dict[str, Any]) -> str:
        summary = payload.get("message") or payload.get("summary") or payload.get("error") or ""
        return "\n".join(
            [
                f"## {dt.datetime.now().isoformat()} - {kind}",
                f"- cwd: {self.memory.cwd}",
                f"- task: {self.memory.current_task or '(none)'}",
                f"- note: {str(summary).strip()[:600] or '(empty)'}",
                "",
            ]
        )
```

## `runtime/tools/memory_hats.py`

- size: 4251 bytes
- sha256: `73a8bd0d4d7e6ceb1943290d5416726a3ae8622360a1b42db1b362cb891a0c86`
- category: memory

```python
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class MemoryHat:
    name: str
    role: str
    instructions: str
    project_path: str = ""
    persistent: bool = True


DEFAULT_HATS = [
    MemoryHat(
        name="coding",
        role="coding agent",
        instructions=(
            "Focus on small, reviewable code changes. Read relevant files before editing. "
            "Prefer existing project patterns and keep execution human-approved."
        ),
    ),
    MemoryHat(
        name="linux",
        role="linux operator",
        instructions=(
            "Treat shell actions as proposed operations. Prefer inspection commands first. "
            "Avoid destructive commands and package installs unless the user explicitly asks."
        ),
    ),
    MemoryHat(
        name="research",
        role="research analyst",
        instructions=(
            "Separate sourced facts from inference. When browsing, capture relevant text and "
            "summarize concisely without inventing missing details."
        ),
    ),
]


class MemoryHatStore:
    """Persistent context overlays used by the planner prompt."""

    def __init__(self, project_dir: Path) -> None:
        self.hats_dir = project_dir / "memory" / "hats"
        self.active_file = project_dir / "state" / "active_hat.json"
        self.hats_dir.mkdir(parents=True, exist_ok=True)
        self.active_file.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_defaults()

    def list_hats(self) -> list[MemoryHat]:
        hats: list[MemoryHat] = []
        for path in sorted(self.hats_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                hats.append(MemoryHat(**payload))
            except (TypeError, json.JSONDecodeError):
                continue
        return hats

    def get_hat(self, name: str) -> MemoryHat | None:
        hat_path = self.hats_dir / f"{name}.json"
        if not hat_path.exists():
            return None
        try:
            return MemoryHat(**json.loads(hat_path.read_text(encoding="utf-8")))
        except (TypeError, json.JSONDecodeError):
            return None

    def active_hat(self) -> MemoryHat | None:
        if not self.active_file.exists():
            return None
        try:
            payload = json.loads(self.active_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        name = str(payload.get("name", "")).strip()
        if not name:
            return None
        return self.get_hat(name)

    def load_hat(self, name: str) -> MemoryHat:
        hat = self.get_hat(name)
        if hat is None:
            raise ValueError(f"Unknown memory hat: {name}")
        self.active_file.write_text(json.dumps({"name": hat.name}, indent=2), encoding="utf-8")
        return hat

    def clear_active(self) -> None:
        if self.active_file.exists():
            self.active_file.unlink()

    def save_hat(
        self,
        name: str,
        role: str,
        instructions: str,
        project_path: str = "",
        persistent: bool = True,
    ) -> MemoryHat:
        hat = MemoryHat(
            name=name,
            role=role,
            instructions=instructions,
            project_path=project_path,
            persistent=persistent,
        )
        self._write_hat(hat)
        return hat

    def prompt_block(self) -> dict:
        hat = self.active_hat()
        if hat is None:
            return {"active": False, "name": "", "role": "", "instructions": ""}
        return {
            "active": True,
            "name": hat.name,
            "role": hat.role,
            "instructions": hat.instructions,
            "project_path": hat.project_path,
        }

    def _ensure_defaults(self) -> None:
        for hat in DEFAULT_HATS:
            path = self.hats_dir / f"{hat.name}.json"
            if not path.exists():
                self._write_hat(hat)

    def _write_hat(self, hat: MemoryHat) -> None:
        path = self.hats_dir / f"{hat.name}.json"
        path.write_text(json.dumps(asdict(hat), indent=2, ensure_ascii=False), encoding="utf-8")
```

## `runtime/tools/project_scanner.py`

- size: 3738 bytes
- sha256: `a9f68e3fafe7f8a7eebd0dac3c7025be8724c5180628f96e5f9730fb063c41e2`
- category: tooling

```python
from __future__ import annotations

import json
import os
from pathlib import Path

from .filesystem_tools import resolve_path


IGNORED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "logs",
    ".pytest_cache",
}

ENTRYPOINT_NAMES = {
    "main.py",
    "app.py",
    "server.py",
    "server.mjs",
    "index.js",
    "index.html",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "run.sh",
    "run_web.sh",
}


def scan_project(path_text: str, cwd: Path, max_files: int = 400) -> dict:
    """Map a project tree and identify likely entrypoints."""
    root = resolve_path(path_text, cwd)
    if not root.exists() or not root.is_dir():
        return {
            "success": False,
            "path": str(root),
            "message": f"Project path does not exist or is not a directory: {root}",
        }

    files: list[str] = []
    entrypoints: list[str] = []
    directories: set[str] = set()
    extension_counts: dict[str, int] = {}

    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in IGNORED_DIRS)
        current_path = Path(current_root)
        rel_dir = current_path.relative_to(root)
        if rel_dir.parts and len(rel_dir.parts) <= 2:
            directories.add(str(rel_dir))

        for filename in sorted(filenames):
            file_path = current_path / filename
            if not file_path.is_file():
                continue
            rel = str(file_path.relative_to(root))
            if len(files) < max_files:
                files.append(rel)
            suffix = file_path.suffix.lower() or "(none)"
            extension_counts[suffix] = extension_counts.get(suffix, 0) + 1
            if file_path.name in ENTRYPOINT_NAMES:
                entrypoints.append(rel)

        total_seen = sum(extension_counts.values())
        if total_seen >= max_files * 3:
            break

    architecture = _summarize_architecture(root, entrypoints, extension_counts)
    report = {
        "root": str(root),
        "directories": sorted(directories)[:80],
        "entrypoints": sorted(entrypoints),
        "extension_counts": dict(sorted(extension_counts.items())),
        "sample_files": files,
        "architecture_summary": architecture,
    }

    report_path = root / "project_scan.json"
    try:
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        report_path = None

    return {
        "success": True,
        "path": str(root),
        "project_scan": report,
        "scan_report_path": str(report_path) if report_path else "",
        "message": f"Scanned {root}. Found {len(entrypoints)} likely entrypoints.",
    }


def _summarize_architecture(root: Path, entrypoints: list[str], extension_counts: dict[str, int]) -> str:
    markers = []
    if (root / "package.json").exists():
        markers.append("JavaScript/Node project")
    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        markers.append("Python project")
    if (root / "index.html").exists():
        markers.append("static/web frontend")
    if (root / "README.md").exists():
        markers.append("README present")
    if not markers:
        markers.append("generic file tree")

    top_extensions = ", ".join(
        f"{extension}:{count}"
        for extension, count in sorted(extension_counts.items(), key=lambda item: item[1], reverse=True)[:6]
    )
    return (
        f"{'; '.join(markers)}. "
        f"Likely entrypoints: {', '.join(entrypoints[:8]) or 'none detected'}. "
        f"Dominant file types: {top_extensions or 'none'}."
    )
```

## `runtime/tools/shell_tools.py`

- size: 1407 bytes
- sha256: `7262bdd4d780fbab7292c971aca3477403d07594c64115362b59f3cd3c9cf2ac`
- category: tooling

```python
from __future__ import annotations

import subprocess
import time
from pathlib import Path


def shell_execute(
    command: str,
    cwd: Path,
    interactive: bool = False,
    timeout_seconds: int = 600,
) -> dict:
    """Execute a shell command through bash.

    `bash -lc` is used intentionally so the runtime can support:
    - quoted strings
    - redirects
    - pipes
    - `&&` and `;`

    Interactive mode is reserved for commands that may prompt the user, such as
    `sudo apt install ...`.
    """
    started = time.monotonic()
    process_args = ["bash", "-lc", command]

    if interactive:
        completed = subprocess.run(
            process_args,
            cwd=str(cwd),
            text=True,
        )
        stdout = ""
        stderr = ""
    else:
        completed = subprocess.run(
            process_args,
            cwd=str(cwd),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
        )
        stdout = completed.stdout
        stderr = completed.stderr

    duration = round(time.monotonic() - started, 3)
    return {
        "success": completed.returncode == 0,
        "command": command,
        "cwd": str(cwd),
        "mode": "interactive" if interactive else "captured",
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": completed.returncode,
        "duration_seconds": duration,
    }
```

## `runtime/tools/system_info.py`

- size: 1234 bytes
- sha256: `fb96991bb13e3f96fd1933e0fc093be5bed032a44d7b891e0b73467bfedb4f2d`
- category: tooling

```python
from __future__ import annotations

import os
from pathlib import Path


def detect_desktop_dir(home: Path | None = None) -> Path:
    """Detect the real desktop directory on Linux Mint/XDG systems."""
    home = home or Path.home()
    xdg_config = home / ".config" / "user-dirs.dirs"
    desktop = home / "Desktop"
    pulpit = home / "Pulpit"

    if xdg_config.exists():
        for raw in xdg_config.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line.startswith("XDG_DESKTOP_DIR="):
                continue

            _, value = line.split("=", 1)
            value = value.strip().strip('"').replace("$HOME", str(home))
            path = Path(os.path.expanduser(value))
            if path.exists():
                return path

    if desktop.exists():
        return desktop
    if pulpit.exists():
        return pulpit
    return home


def build_runtime_context(project_dir: Path, cwd: Path) -> dict:
    """Build a compact runtime snapshot for prompting and logs."""
    home = Path.home()
    return {
        "home_dir": str(home),
        "desktop_dir": str(detect_desktop_dir(home)),
        "current_cwd": str(cwd),
        "current_project": str(project_dir),
    }
```

## `runtime/tools/validator.py`

- size: 7844 bytes
- sha256: `31ad131ba56ea16432c680832c9bb3686f9f058d4cff96321fde41f8fbdd02ca`
- category: tooling

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from json import JSONDecodeError


ALLOWED_ACTIONS = {
    "respond",
    "shell_execute",
    "write_file",
    "append_file",
    "read_file",
    "create_file",
    "create_folder",
    "move_file",
    "delete_file",
    "search_in_project",
    "change_directory",
    "browser_start",
    "browser_open",
    "browser_click",
    "browser_type",
    "browser_press",
    "browser_read_html",
    "browser_get_visible_text",
    "browser_screenshot",
    "browser_close",
    "browser_current_url",
    "scan_project",
}

BLOCKED_SHELL_PATTERNS = (
    "\x00",
    "$(",
    "`",
    "<<",
    "<(",
    ">(",
    ":(){ :|:& };:",
    "rm -rf /",
    "curl | bash",
    "curl|bash",
    "wget -o-",
    "wget -O-",
)

CONFIRMATION_PATTERNS = (
    "sudo ",
    "apt install",
    "apt-get install",
    "pip install",
    "pip3 install",
    "npm install",
)

DANGEROUS_PATTERNS = (
    "rm -rf /",
    ":(){ :|:& };:",
    "chmod -r /",
    "chmod -R /",
    "chown -r /",
    "chown -R /",
    "mkfs",
    "dd ",
    "shutdown",
    "reboot",
)

ALLOWED_CONFIDENCE_LABELS = {"high", "medium", "low", "unknown"}


@dataclass
class PermissionDecision:
    mode: str
    requires_confirmation: bool
    interactive: bool
    reason: str


def extract_json_object(raw_text: str) -> dict:
    """Extract one JSON object from model output."""
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        data = json.loads(raw_text)
        if isinstance(data, dict):
            return data
    except JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(raw_text):
        if char != "{":
            continue
        try:
            data, _ = decoder.raw_decode(raw_text[index:])
        except JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data

    raise ValueError(f"Invalid JSON action payload: {raw_text}")


def validate_action(action: dict) -> dict:
    """Validate and normalize model-generated actions."""
    if not isinstance(action, dict):
        raise ValueError("Action must be a JSON object.")

    name = str(action.get("action") or action.get("type") or "").strip()
    if name == "terminal_command":
        name = "shell_execute"
    if name not in ALLOWED_ACTIONS:
        raise ValueError(f"Unsupported action: {name}")

    normalized = dict(action)
    normalized["action"] = name
    normalized["reason"] = str(action.get("reason", "")).strip()
    normalized["requires_confirmation"] = bool(action.get("requires_confirmation", False))
    confidence = str(action.get("confidence", action.get("confidence_label", "unknown"))).strip().lower()
    normalized["confidence_label"] = confidence if confidence in ALLOWED_CONFIDENCE_LABELS else "unknown"

    if name == "respond":
        normalized["message"] = str(action.get("message", "")).strip()
        if not normalized["message"]:
            raise ValueError("respond requires a non-empty message.")
        return normalized

    if name == "shell_execute":
        normalized["command"] = str(action.get("command", "")).strip()
        if not normalized["command"]:
            raise ValueError("shell_execute requires a command.")
        return normalized

    if name in {"write_file", "append_file", "create_file"}:
        normalized["path"] = str(action.get("path", "")).strip()
        normalized["content"] = str(action.get("content", ""))
        if not normalized["path"]:
            raise ValueError(f"{name} requires a path.")
        return normalized

    if name in {"read_file", "create_folder", "delete_file", "change_directory"}:
        normalized["path"] = str(action.get("path", "")).strip()
        if not normalized["path"]:
            raise ValueError(f"{name} requires a path.")
        return normalized

    if name == "move_file":
        normalized["src"] = str(action.get("src", "")).strip()
        normalized["dst"] = str(action.get("dst", "")).strip()
        if not normalized["src"] or not normalized["dst"]:
            raise ValueError("move_file requires src and dst.")
        return normalized

    if name == "search_in_project":
        normalized["path"] = str(action.get("path", ".")).strip() or "."
        normalized["pattern"] = str(action.get("pattern", "")).strip()
        if not normalized["pattern"]:
            raise ValueError("search_in_project requires pattern.")
        return normalized

    if name == "scan_project":
        normalized["path"] = str(action.get("path", ".")).strip() or "."
        return normalized

    if name == "browser_open":
        normalized["url"] = str(action.get("url", "")).strip()
        if not normalized["url"]:
            raise ValueError("browser_open requires url.")
        return normalized

    if name in {"browser_click"}:
        normalized["selector"] = str(action.get("selector", "")).strip()
        if not normalized["selector"]:
            raise ValueError(f"{name} requires selector.")
        return normalized

    if name in {"browser_type"}:
        normalized["selector"] = str(action.get("selector", "")).strip()
        normalized["text"] = str(action.get("text", ""))
        if not normalized["selector"]:
            raise ValueError("browser_type requires selector.")
        return normalized

    if name in {"browser_press"}:
        normalized["key"] = str(action.get("key", "")).strip()
        if not normalized["key"]:
            raise ValueError("browser_press requires key.")
        return normalized

    if name in {"browser_screenshot"}:
        normalized["path"] = str(action.get("path", "")).strip()
        return normalized

    return normalized


def validate_shell_command(command: str) -> tuple[bool, str]:
    """Allow multi-step commands while blocking dangerous shell constructs."""
    stripped = command.strip()
    if not stripped:
        return False, "Empty command."
    if "\r" in stripped or "\x00" in stripped:
        return False, "Control characters are not allowed."
    if "\n" in stripped:
        return False, "Multiline commands are not allowed."

    lowered = stripped.lower()
    for pattern in BLOCKED_SHELL_PATTERNS:
        if pattern.lower() in lowered:
            return False, f"Blocked shell pattern: {pattern}"

    return True, "OK"


def classify_shell_command(command: str) -> PermissionDecision:
    """Classify commands into safe, advanced, and dangerous execution modes."""
    lowered = command.lower().strip()

    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in lowered:
            return PermissionDecision(
                mode="dangerous",
                requires_confirmation=True,
                interactive="sudo" in lowered,
                reason=f"Dangerous pattern detected: {pattern}",
            )

    for pattern in CONFIRMATION_PATTERNS:
        if pattern in lowered:
            return PermissionDecision(
                mode="advanced",
                requires_confirmation=True,
                interactive="sudo" in lowered or "apt " in lowered or "apt-get " in lowered,
                reason=f"Confirmation required for: {pattern}",
            )

    if any(operator in command for operator in ("&&", ";", "|")):
        return PermissionDecision(
            mode="advanced",
            requires_confirmation=True,
            interactive=False,
            reason="Multi-step command requires confirmation",
        )

    return PermissionDecision(
        mode="safe",
        requires_confirmation=False,
        interactive=False,
        reason="Safe command",
    )
```

## `runtime/tools/web_reader.py`

- size: 872 bytes
- sha256: `b548c79f1f7528880a5f38188a936f7cff55de0fe7725c9475a92cfb8bb9a1e1`
- category: tooling

```python
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import hashlib

CACHE_DIR = Path("cache/web")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def cache_name(url: str):
    return CACHE_DIR / f"{hashlib.md5(url.encode()).hexdigest()}.txt"

def fetch_page(url: str):
    cache_file = cache_name(url)

    if cache_file.exists():
        return cache_file.read_text()

    response = requests.get(
        url,
        timeout=20,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    soup = BeautifulSoup(response.text, "html.parser")

    text = soup.get_text(separator="\n")

    cleaned = "\n".join(
        line.strip()
        for line in text.splitlines()
        if line.strip()
    )

    cache_file.write_text(cleaned)

    return cleaned[:15000]

if name == "main":
    url = input("URL: ")
    print(fetch_page(url))
```

