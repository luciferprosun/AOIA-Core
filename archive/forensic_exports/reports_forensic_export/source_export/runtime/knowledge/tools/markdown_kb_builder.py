#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_PATH = ROOT / "canonical" / "rhcsa_commands.json"
TOPIC_DIRS = (
    "filesystem",
    "networking",
    "users",
    "permissions",
    "selinux",
    "systemd",
    "storage",
    "lvm",
    "podman",
    "bash",
    "troubleshooting",
)

TOPIC_DESCRIPTIONS = {
    "filesystem": "File navigation, file operations, search, archives, and editor-oriented workflows.",
    "networking": "Networking, SSH, firewall, remote access, and shared-service connectivity.",
    "users": "User, group, identity, and account lifecycle operations.",
    "permissions": "Ownership, permission bits, access control basics, and safe permission checks.",
    "selinux": "SELinux inspection, contexts, booleans, labeling, and policy-related remediation.",
    "systemd": "systemd, services, boot flow, timers/cron, and package/service lifecycle actions.",
    "storage": "Disks, partitions, filesystems, mount operations, RAID, and persistence checks.",
    "lvm": "Logical Volume Manager concepts and operational commands.",
    "podman": "Podman images, containers, pods, volumes, networks, and rootless usage patterns.",
    "bash": "Shell variables, scripting, text processing, and CLI composition patterns.",
    "troubleshooting": "Diagnostics, logs, process inspection, system information, and recovery-oriented workflows.",
}

TOPIC_KEYWORDS = {
    "filesystem": (
        "nawigacja",
        "operacje na plikach",
        "przegladanie zawartosci plikow",
        "wyszukiwanie plikow",
        "archiwizacja",
        "vim",
    ),
    "networking": (
        "sie",
        "ssh",
        "zapora",
        "firewalld",
        "nfs",
        "samba",
        "autofs",
    ),
    "users": (
        "ytkownik",
        "grupami",
        "grup",
    ),
    "permissions": (
        "uprawnienia",
        "wlasnosc",
        "wlasnosc",
    ),
    "selinux": ("selinux",),
    "systemd": (
        "systemd",
        "uslugami",
        "usluga",
        "boot",
        "grub",
        "cron",
        "harmonogramowanie",
        "pakietami",
        "dnf",
        "rpm",
    ),
    "storage": (
        "systemy plikow",
        "montowanie",
        "dysk",
        "partycje",
        "raid",
        "przechowywanie danych",
    ),
    "lvm": ("lvm", "logical volume"),
    "podman": ("podman", "kontenery"),
    "bash": (
        "powloka",
        "bash",
        "rodowiskowe",
        "filtrowanie tekstu",
        "tekstowe",
        "skrypty bash",
    ),
    "troubleshooting": (
        "diagnostyka",
        "logowanie",
        "monitorowanie",
        "informacje o systemie",
        "procesami",
        "administracyjne",
    ),
}


@dataclass(frozen=True)
class CommandEntry:
    command: str
    category: str
    risk: str
    description: str
    examples: list[str]
    source_section: str


def normalize_text(value: str) -> str:
    ascii_text = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()


def slugify(value: str) -> str:
    slug = normalize_text(value).replace(" ", "-")
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "module"


def load_entries() -> list[CommandEntry]:
    payload = json.loads(CANONICAL_PATH.read_text(encoding="utf-8"))
    entries: list[CommandEntry] = []
    for item in payload:
        command = str(item.get("command", "")).strip()
        if not command:
            continue
        entries.append(
            CommandEntry(
                command=command,
                category=str(item.get("category", "")).strip(),
                risk=str(item.get("risk", "unclassified")).strip() or "unclassified",
                description=str(item.get("description", "")).strip(),
                examples=[str(example).strip() for example in item.get("examples", []) if str(example).strip()],
                source_section=str(item.get("source_section", "")).strip() or str(item.get("category", "")).strip(),
            )
        )
    return entries


def detect_topic(section: str) -> str:
    normalized = normalize_text(section)
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return topic
    return "filesystem"


def summarize_section(entries: list[CommandEntry]) -> str:
    commands = [entry.command for entry in entries]
    families = sorted({head for command in commands if (head := semantic_head(command))})[:8]
    return (
        f"Imported RHCSA material for {len(entries)} commands. "
        f"Primary command families: {', '.join(families) if families else 'none'}."
    )


def base_command(command: str) -> str:
    return command.split()[0]


def semantic_head(command: str) -> str | None:
    head = base_command(command)
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9._:+-]*", head):
        return None
    return head.lower()


def derived_tags(topic: str, section: str, entries: list[CommandEntry]) -> list[str]:
    tags = {"rhcsa", "linux", topic, slugify(section)}
    for entry in entries:
        head = semantic_head(entry.command)
        if head:
            tags.add(head)
    return sorted(tags)


def troubleshooting_notes(topic: str, entries: list[CommandEntry]) -> list[str]:
    commands = " ".join(entry.command for entry in entries).lower()
    notes: list[str] = []
    if "rm -rf" in commands or "rsync --delete" in commands:
        notes.append("Verify the full target path with `pwd` and `ls` before destructive filesystem commands.")
    if "grep" in commands or "awk" in commands or "sed" in commands:
        notes.append("Quote patterns explicitly to avoid shell expansion when matching text.")
    if "systemctl" in commands:
        notes.append("If a service action fails, inspect `systemctl status <unit>` and `journalctl -u <unit>`.")
    if "journalctl" in commands:
        notes.append("Use time or unit filters first to keep logs readable on low-RAM systems.")
    if "chmod" in commands or "chown" in commands:
        notes.append("Confirm current ownership and mode with `ls -l` or `stat` before changing permissions.")
    if "useradd" in commands or "passwd" in commands or "usermod" in commands:
        notes.append("Validate account state with `id`, `/etc/passwd`, and `/etc/group` after changes.")
    if "nmcli" in commands or "ip " in commands or "ssh" in commands or "firewall-cmd" in commands:
        notes.append("Check interface state, service state, and firewall exposure together during network diagnostics.")
    if "mount" in commands or "mkfs" in commands or "lsblk" in commands or "fdisk" in commands:
        notes.append("Cross-check block devices with `lsblk` before formatting, mounting, or editing persistent mounts.")
    if re.search(r"\b(pvs|vgs|lvs|pvcreate|vgcreate|lvcreate|lvextend|lvreduce|lvremove|vgextend|pvdisplay|vgdisplay|lvdisplay)\b", commands):
        notes.append("Validate PV/VG/LV layout with `pvs`, `vgs`, and `lvs` before resizing storage.")
    if "podman" in commands:
        notes.append("When container behavior is unexpected, inspect logs, ports, mounts, and SELinux labeling together.")
    if "selinux" in commands or "semanage" in commands or "restorecon" in commands or "getenforce" in commands:
        notes.append("Correlate AVC denials with labels and booleans before disabling SELinux protections.")
    if not notes:
        notes.append("Validate command intent against current host state before applying changes in production.")
    if topic == "troubleshooting":
        notes.append("Prefer read-only inspection first, then narrow fixes to the subsystem that produced the symptom.")
    return notes[:4]


def render_module(topic: str, section: str, entries: list[CommandEntry]) -> str:
    tags = derived_tags(topic, section, entries)
    lines = [
        "---",
        f"title: {section}",
        f"topic: {topic}",
        f"source_section: {section}",
        "source_pdf: knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from: knowledge/canonical/rhcsa_commands.json",
        f"tags: [{', '.join(tags)}]",
        "---",
        "",
        f"# {section}",
        "",
        summarize_section(entries),
        "",
        "## Tags",
        "",
        ", ".join(tags),
        "",
        "## Examples",
        "",
    ]
    examples = unique_examples(entries)[:10]
    for example in examples:
        lines.append(f"- `{example}`")

    lines.extend(
        [
            "",
            "## Troubleshooting",
            "",
        ]
    )
    for note in troubleshooting_notes(topic, entries):
        lines.append(f"- {note}")

    lines.extend(
        [
            "",
            "## Provenance",
            "",
            "- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`",
            "- Canonical import: `knowledge/canonical/rhcsa_commands.json`",
            f"- Source section: `{section}`",
            "",
            "## Commands",
            "",
        ]
    )

    for entry in entries:
        entry_examples = entry.examples[:3] or [entry.command]
        lines.extend(
            [
                f"### `{entry.command}`",
                "",
                f"- Category: `{entry.category or section}`",
                f"- Risk: `{entry.risk}`",
                f"- Tags: `{topic}`, `{semantic_head(entry.command) or slugify(base_command(entry.command))}`",
            ]
        )
        if entry.description:
            lines.append(f"- Description: {entry.description}")
        lines.append("- Examples:")
        for example in entry_examples:
            lines.append(f"  - `{example}`")
        lines.append("- Troubleshooting hint:")
        lines.append(f"  - {troubleshooting_notes(topic, [entry])[0]}")
        lines.append("- Provenance:")
        lines.append(f"  - RHCSA section: `{entry.source_section}`")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def unique_examples(entries: list[CommandEntry]) -> list[str]:
    seen: set[str] = set()
    examples: list[str] = []
    for entry in entries:
        for example in entry.examples or [entry.command]:
            if example not in seen:
                seen.add(example)
                examples.append(example)
    return examples


def render_topic_readme(topic: str, modules: list[tuple[str, Path, list[CommandEntry]]]) -> str:
    lines = [
        f"# {topic.title()}",
        "",
        TOPIC_DESCRIPTIONS[topic],
        "",
        "## Modules",
        "",
    ]
    for section, path, entries in modules:
        rel_path = path.relative_to(ROOT)
        lines.append(f"- `{rel_path}`: {len(entries)} imported commands from `{section}`")
    lines.extend(
        [
            "",
            "## Provenance",
            "",
            "- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`",
            "- Canonical import: `knowledge/canonical/rhcsa_commands.json`",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_root_readme(topic_map: dict[str, list[tuple[str, Path, list[CommandEntry]]]]) -> str:
    lines = [
        "# RHCSA Local Knowledge Base",
        "",
        "This directory contains the structured local RHCSA knowledge base built from the",
        "existing canonical command import. The original deterministic JSON pipeline remains",
        "in place; these markdown modules add topic-oriented operator-readable knowledge.",
        "",
        "## Topic Layout",
        "",
    ]
    for topic in TOPIC_DIRS:
        count = sum(len(entries) for _, _, entries in topic_map.get(topic, []))
        lines.append(f"- `{topic}/`: {count} commands")
    lines.extend(
        [
            "",
            "## Provenance",
            "",
            "- Source PDF: `knowledge/source/RHCSA_Command_Library (1).pdf`",
            "- Canonical import: `knowledge/canonical/rhcsa_commands.json`",
            "- Parsed sections: `knowledge/parsed/rhcsa_sections.json`",
            "",
            "## Notes",
            "",
            "- Existing deterministic JSON artifacts are preserved.",
            "- Markdown modules are generated from the canonical command import.",
            "- Topic mapping is heuristic but deterministic.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def reset_topic_dirs() -> None:
    for topic in TOPIC_DIRS:
        path = ROOT / topic
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)


def build() -> dict[str, list[tuple[str, Path, list[CommandEntry]]]]:
    entries = load_entries()
    grouped: dict[str, list[CommandEntry]] = defaultdict(list)
    for entry in entries:
        grouped[entry.source_section].append(entry)

    reset_topic_dirs()
    topic_map: dict[str, list[tuple[str, Path, list[CommandEntry]]]] = defaultdict(list)
    for section, section_entries in sorted(grouped.items()):
        topic = detect_topic(section)
        filename = slugify(section) + ".md"
        path = ROOT / topic / filename
        path.write_text(render_module(topic, section, section_entries), encoding="utf-8")
        topic_map[topic].append((section, path, section_entries))

    for topic in TOPIC_DIRS:
        readme_path = ROOT / topic / "README.md"
        readme_path.write_text(render_topic_readme(topic, topic_map.get(topic, [])), encoding="utf-8")

    (ROOT / "README.md").write_text(render_root_readme(topic_map), encoding="utf-8")
    return topic_map


def main() -> int:
    topic_map = build()
    print("Generated RHCSA markdown knowledge base:")
    for topic in TOPIC_DIRS:
        modules = topic_map.get(topic, [])
        command_count = sum(len(entries) for _, _, entries in modules)
        print(f"- {topic}: {len(modules)} modules, {command_count} commands")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
