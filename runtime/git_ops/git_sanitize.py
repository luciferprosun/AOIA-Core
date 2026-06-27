from __future__ import annotations

import re


_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_GITHUB_CLASSIC_RE = re.compile(r"ghp_[A-Za-z0-9_]{8,}")
_GITHUB_FINE_GRAINED_RE = re.compile(r"github_pat_[A-Za-z0-9_]{8,}")
_CREDENTIAL_URL_RE = re.compile(r"https://[^@\s/]+@github\.com", re.IGNORECASE)
_TOKEN_PARAM_RE = re.compile(r"(?i)\b(access_token|token)=([^&\s]+)")


def redact_git_secrets(text: str | None) -> str:
    if text is None:
        return ""
    value = str(text)
    value = _GITHUB_CLASSIC_RE.sub("ghp_[REDACTED]", value)
    value = _GITHUB_FINE_GRAINED_RE.sub("github_pat_[REDACTED]", value)
    value = _CREDENTIAL_URL_RE.sub("https://[REDACTED]@github.com", value)
    value = _TOKEN_PARAM_RE.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)
    return value


def sanitize_git_output(text: str | None) -> str:
    redacted = redact_git_secrets(text)
    without_ansi = _ANSI_RE.sub("", redacted)
    return "".join(
        char if char == "\n" or char == "\t" or ord(char) >= 32 else "?"
        for char in without_ansi
    )
