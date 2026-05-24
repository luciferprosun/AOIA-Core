from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


COMMAND_STOPWORDS = {
    "a",
    "about",
    "command",
    "commands",
    "for",
    "how",
    "jak",
    "komenda",
    "komendy",
    "linux",
    "mi",
    "of",
    "o",
    "poka",
    "pokaz",
    "pokaż",
    "rhcsa",
    "rhce",
    "show",
    "the",
    "to",
    "w",
}

ALIASES = {
    "apache": "httpd",
    "apachectl": "httpd",
    "cron": "crontab",
    "firewall": "firewall-cmd",
    "firewalld": "firewall-cmd",
    "grep extended": "grep -E",
    "list": "ls",
    "services": "systemctl",
    "ssh daemon": "sshd",
    "ssh service": "sshd",
}


@dataclass(frozen=True)
class NormalizedQuery:
    original: str
    normalized: str
    tokens: tuple[str, ...]
    candidate_command: str
    alias_target: str | None
    category_hint: str | None


def normalize_text(value: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    return re.sub(r"[^a-z0-9_+./$-]+", " ", normalized).strip()


def normalize_command(value: str) -> str:
    return " ".join(value.strip().split())


def command_key(value: str) -> str:
    command = normalize_command(value)
    if " " not in command:
        return command.lower()
    binary, rest = command.split(" ", 1)
    return f"{binary.lower()} {rest}"


def tokenize(value: str) -> tuple[str, ...]:
    return tuple(token for token in normalize_text(value).split() if token)


def detect_category(tokens: tuple[str, ...]) -> str | None:
    joined = " ".join(tokens)
    categories = {
        "bash": {"bash", "shell", "script", "skrypt", "zmienna"},
        "filesystem": {"file", "files", "folder", "katalog", "plik", "directory", "copy", "delete"},
        "lvm": {"lvm", "lv", "vg", "pv", "volume"},
        "networking": {"network", "ip", "dns", "firewall", "port", "ssh", "routing", "sieci"},
        "permissions": {"chmod", "chown", "permission", "acl", "uprawnienia"},
        "podman": {"podman", "container", "kontener"},
        "selinux": {"selinux", "semanage", "restorecon", "context"},
        "storage": {"disk", "mount", "xfs", "ext4", "swap", "storage", "dysk"},
        "systemd": {"systemd", "systemctl", "journalctl", "service", "timer", "usluga", "usługa"},
        "troubleshooting": {"debug", "diagnose", "problem", "troubleshoot", "log", "logs"},
        "users": {"user", "group", "passwd", "uzytkownik", "użytkownik", "grupa"},
    }
    for category, words in categories.items():
        if words.intersection(tokens) or category in joined:
            return category
    return None


def extract_candidate_command(query: str) -> str:
    quoted = re.findall(r"`([^`]+)`", query)
    if quoted:
        return normalize_command(quoted[0])

    tokens = list(tokenize(query))
    meaningful = [token for token in tokens if token not in COMMAND_STOPWORDS]
    if not meaningful:
        return ""

    if len(meaningful) >= 2:
        two = " ".join(meaningful[:2])
        if two in ALIASES:
            return two
        if meaningful[1].startswith("-") or meaningful[0] in {"dnf", "git", "ip", "ls", "systemctl", "journalctl"}:
            return normalize_command(" ".join(meaningful[:3]))
    return meaningful[0]


def normalize_query(query: str) -> NormalizedQuery:
    normalized = normalize_text(query)
    tokens = tokenize(query)
    candidate = extract_candidate_command(query)
    alias_target = ALIASES.get(candidate.lower()) if candidate else None
    if not alias_target:
        alias_target = ALIASES.get(normalized)
    return NormalizedQuery(
        original=query,
        normalized=normalized,
        tokens=tokens,
        candidate_command=candidate,
        alias_target=alias_target,
        category_hint=detect_category(tokens),
    )
