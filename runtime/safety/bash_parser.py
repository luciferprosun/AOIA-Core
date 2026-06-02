from __future__ import annotations

import shlex

from runtime.schemas.command_proposal import CommandProposal

SYSTEM_PATH_PREFIXES = (
    "/bin",
    "/boot",
    "/dev",
    "/etc",
    "/lib",
    "/proc",
    "/sbin",
    "/sys",
    "/usr",
    "/var",
)


def parse_bash_command(command: str, *, source: str = "user") -> CommandProposal:
    if not isinstance(command, str):
        raise TypeError("command must be a string")
    normalized = " ".join(command.split())
    if not normalized:
        return _proposal(command, normalized, (), "unknown", "empty command", source)
    try:
        tokens = tuple(shlex.split(normalized, posix=True))
    except ValueError as error:
        return _proposal(
            command,
            normalized,
            (),
            "unknown",
            f"tokenization failed: {error.__class__.__name__}",
            source,
        )
    classification, reason = _classify(normalized, tokens)
    return _proposal(command, normalized, tokens, classification, reason, source)


def _proposal(
    raw_command: str,
    normalized_command: str,
    tokens: tuple[str, ...],
    classification: str,
    reason: str,
    source: str,
) -> CommandProposal:
    approval_state = (
        "not_required" if classification == "safe" else "requires_human_review"
    )
    return CommandProposal(
        raw_command=raw_command,
        normalized_command=normalized_command,
        tokens=tokens,
        classification=classification,
        approval_state=approval_state,
        reason=reason,
        source=source,
        created_by="runtime.safety.bash_parser",
        dry_run=True,
    )


def _classify(command: str, tokens: tuple[str, ...]) -> tuple[str, str]:
    lowered = command.lower()
    compact = lowered.replace(" ", "")
    if compact == ":(){:|:&};:":
        return "dangerous", "fork bomb pattern detected"
    if _has_pipe_to_runner(tokens):
        return "dangerous", "pipe-to-runner pattern detected"
    if _has_runner_command(tokens):
        return "dangerous", "runner command mode detected"
    if _has_mkfs(tokens):
        return "dangerous", "filesystem formatting command detected"
    if _has_dd_disk_write(tokens):
        return "dangerous", "dd device copy option detected"
    if _has_root_recursive_remove(tokens):
        return "dangerous", "recursive root removal pattern detected"
    if _has_recursive_world_write_root(tokens):
        return "dangerous", "recursive world-writable root permission pattern detected"
    if _has_recursive_owner_change(tokens):
        return "dangerous", "recursive ownership change detected"
    if tokens and tokens[0] == "sudo":
        return "dangerous", "privilege escalation prefix detected"
    if _has_command_substitution(command):
        return "ambiguous", "command substitution marker detected"
    if _has_command_chaining(command):
        return "ambiguous", "command chaining marker detected"
    if _has_pipe(command):
        return "ambiguous", "pipe chain detected"
    if _has_dev_redirection(command):
        return "ambiguous", "device redirection detected"
    if _has_recursive_remove(tokens):
        return "ambiguous", "recursive removal requires review"
    if _has_recursive_permission_change(tokens):
        return "ambiguous", "recursive permission change requires review"
    if _has_owner_change(tokens):
        return "ambiguous", "ownership change requires review"
    if _has_system_path_move(tokens):
        return "ambiguous", "move involving system path requires review"
    if _is_safe_read_only(tokens):
        return "safe", "recognized read-only command shape"
    return "unknown", "command shape is not recognized"


def _has_pipe_to_runner(tokens: tuple[str, ...]) -> bool:
    if "|" not in tokens:
        return False
    first = tokens[0] if tokens else ""
    if first not in {"curl", "wget"}:
        return False
    pipe_index = tokens.index("|")
    tail = tokens[pipe_index + 1 :]
    return bool(tail) and tail[0] in {"sh", "bash"}


def _has_runner_command(tokens: tuple[str, ...]) -> bool:
    return len(tokens) >= 2 and tokens[0] in {"bash", "sh"} and tokens[1] == "-c"


def _has_mkfs(tokens: tuple[str, ...]) -> bool:
    return any(token == "mkfs" or token.startswith("mkfs.") for token in tokens)


def _has_dd_disk_write(tokens: tuple[str, ...]) -> bool:
    return bool(tokens) and tokens[0] == "dd" and any(
        token.startswith("if=") or token.startswith("of=") for token in tokens[1:]
    )


def _has_root_recursive_remove(tokens: tuple[str, ...]) -> bool:
    if not _is_rm_recursive_force(tokens):
        return False
    targets = _rm_targets(tokens)
    return any(target == "/" or target.startswith("/*") for target in targets)


def _has_recursive_remove(tokens: tuple[str, ...]) -> bool:
    if not _is_rm_recursive_force(tokens):
        return False
    targets = _rm_targets(tokens)
    if any("*" in target for target in targets):
        return True
    return bool(targets)


def _is_rm_recursive_force(tokens: tuple[str, ...]) -> bool:
    if not tokens or tokens[0] != "rm":
        return False
    flags = [token for token in tokens[1:] if token.startswith("-")]
    has_recursive = any("r" in flag or "R" in flag for flag in flags)
    has_force = any("f" in flag for flag in flags)
    return has_recursive and has_force


def _rm_targets(tokens: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(token for token in tokens[1:] if not token.startswith("-"))


def _has_recursive_world_write_root(tokens: tuple[str, ...]) -> bool:
    if len(tokens) < 4 or tokens[0] != "chmod":
        return False
    return "-R" in tokens[1:] and "777" in tokens[1:] and "/" in tokens[1:]


def _has_recursive_permission_change(tokens: tuple[str, ...]) -> bool:
    return bool(tokens) and tokens[0] == "chmod" and "-R" in tokens[1:]


def _has_recursive_owner_change(tokens: tuple[str, ...]) -> bool:
    return bool(tokens) and tokens[0] == "chown" and "-R" in tokens[1:]


def _has_owner_change(tokens: tuple[str, ...]) -> bool:
    return bool(tokens) and tokens[0] == "chown"


def _has_system_path_move(tokens: tuple[str, ...]) -> bool:
    if not tokens or tokens[0] != "mv":
        return False
    return any(_is_system_path(token) for token in tokens[1:])


def _is_system_path(token: str) -> bool:
    return any(token == prefix or token.startswith(prefix + "/") for prefix in SYSTEM_PATH_PREFIXES)


def _has_command_substitution(command: str) -> bool:
    return "$(" in command or "`" in command


def _has_command_chaining(command: str) -> bool:
    return ";" in command or "&&" in command or "||" in command


def _has_pipe(command: str) -> bool:
    return "|" in command


def _has_dev_redirection(command: str) -> bool:
    for marker in (">/dev/", "> /dev/", ">>/dev/", ">> /dev/", "</dev/", "< /dev/"):
        if marker in command:
            return True
    return False


def _is_safe_read_only(tokens: tuple[str, ...]) -> bool:
    if not tokens:
        return False
    if tokens[0] in {"pwd", "whoami"} and len(tokens) == 1:
        return True
    if tokens[0] == "ls":
        return True
    if tokens[0] == "echo":
        return True
    if tokens[0] == "cat" and len(tokens) >= 2:
        return True
    if tokens[0] == "grep" and len(tokens) >= 3:
        return True
    return False
