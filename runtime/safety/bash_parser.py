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
    "/root",
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
    tokens = _normalize_executable_tokens(tokens)
    effective_tokens = _unwrap_env_tokens(tokens)
    lowered = command.lower()
    compact = lowered.replace(" ", "")
    if compact == ":(){:|:&};:":
        return "dangerous", "fork bomb pattern detected"
    if _has_ifs_substitution(command):
        ifs_tokens = _unwrap_env_tokens(_normalize_executable_tokens(_ifs_expanded_tokens(command)))
        if _has_root_recursive_remove(ifs_tokens):
            return "dangerous", "IFS-obfuscated recursive root removal pattern detected"
        if _has_recursive_world_write_root(ifs_tokens):
            return "dangerous", "IFS-obfuscated recursive root permission pattern detected"
        if _has_recursive_owner_change(ifs_tokens):
            return "dangerous", "IFS-obfuscated recursive ownership change detected"
        return "ambiguous", "IFS substitution marker detected"
    if _has_pipe_to_runner(tokens):
        return "dangerous", "pipe-to-runner pattern detected"
    if _has_xargs_recursive_remove(tokens):
        return "dangerous", "xargs recursive removal wrapper detected"
    if _has_heredoc_runner(tokens):
        return "dangerous", "heredoc shell runner pattern detected"
    if _has_process_substitution_runner(command, effective_tokens):
        return "dangerous", "process substitution shell runner pattern detected"
    if _has_runner_command(effective_tokens):
        return "dangerous", "runner command mode detected"
    if _has_mkfs(effective_tokens):
        return "dangerous", "filesystem formatting command detected"
    if _has_dd_disk_write(effective_tokens):
        return "dangerous", "dd device copy option detected"
    if _has_root_recursive_remove(effective_tokens):
        return "dangerous", "recursive root removal pattern detected"
    if _has_recursive_world_write_root(effective_tokens):
        return "dangerous", "recursive world-writable root permission pattern detected"
    if _has_recursive_owner_change(effective_tokens):
        return "dangerous", "recursive ownership change detected"
    if effective_tokens and effective_tokens[0] == "sudo":
        return "dangerous", "privilege escalation prefix detected"
    if _has_alias_or_function_definition(command, tokens):
        return "ambiguous", "alias or function definition requires review"
    if _has_encoded_payload_indicator(effective_tokens):
        return "ambiguous", "encoded payload marker requires review"
    if _has_process_substitution(command):
        return "ambiguous", "process substitution marker detected"
    if _has_non_ascii_marker(command):
        return "ambiguous", "non-ASCII command marker detected"
    if _has_command_substitution(command):
        return "ambiguous", "command substitution marker detected"
    if _has_command_chaining(command):
        return "ambiguous", "command chaining marker detected"
    if _has_pipe(command):
        return "ambiguous", "pipe chain detected"
    if _has_sensitive_redirection(tokens):
        return "ambiguous", "redirection to sensitive path requires review"
    if _has_dev_redirection(command):
        return "ambiguous", "device redirection detected"
    if _has_recursive_remove(effective_tokens):
        return "ambiguous", "recursive removal requires review"
    if _has_recursive_permission_change(effective_tokens):
        return "ambiguous", "recursive permission change requires review"
    if _has_owner_change(effective_tokens):
        return "ambiguous", "ownership change requires review"
    if _has_system_path_move(effective_tokens):
        return "ambiguous", "move involving system path requires review"
    if _has_find_delete(effective_tokens):
        return "ambiguous", "find delete action requires review"
    if _has_echo_command_like_text(effective_tokens):
        return "ambiguous", "echo command-like text requires review"
    if _is_safe_read_only(effective_tokens):
        return "safe", "recognized read-only command shape"
    return "unknown", "command shape is not recognized"


def _has_pipe_to_runner(tokens: tuple[str, ...]) -> bool:
    if "|" not in tokens:
        return False
    return any(segment and segment[0] in {"sh", "bash"} for segment in _pipe_segments(tokens)[1:])


def _pipe_segments(tokens: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token == "|":
            segments.append([])
        else:
            segments[-1].append(token)
    return tuple(tuple(segment) for segment in segments)


def _has_xargs_recursive_remove(tokens: tuple[str, ...]) -> bool:
    if "xargs" not in tokens:
        return False
    index = tokens.index("xargs")
    tail = _normalize_executable_tokens(tokens[index + 1 :])
    return _is_rm_recursive_force(tail)


def _has_heredoc_runner(tokens: tuple[str, ...]) -> bool:
    return bool(tokens) and tokens[0] in {"sh", "bash"} and any(
        token.startswith("<<") for token in tokens[1:]
    )


def _has_process_substitution_runner(command: str, tokens: tuple[str, ...]) -> bool:
    return bool(tokens) and tokens[0] in {"sh", "bash"} and _has_process_substitution(command)


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


def _has_find_delete(tokens: tuple[str, ...]) -> bool:
    return bool(tokens) and tokens[0] == "find" and "-delete" in tokens[1:]


def _has_alias_or_function_definition(command: str, tokens: tuple[str, ...]) -> bool:
    if tokens and tokens[0] == "alias":
        return True
    compact = command.replace(" ", "")
    return "(){" in compact or "function" in tokens[:1]


def _has_encoded_payload_indicator(tokens: tuple[str, ...]) -> bool:
    if not tokens:
        return False
    if tokens[0] not in {"base64", "openssl", "xxd"}:
        return False
    decode_markers = {"-d", "--decode", "-D", "base64", "-r", "-p"}
    return any(token in decode_markers for token in tokens[1:])


def _has_echo_command_like_text(tokens: tuple[str, ...]) -> bool:
    if not tokens or tokens[0] != "echo":
        return False
    text = " ".join(tokens[1:]).strip().lower()
    if not text:
        return False
    suspicious_fragments = (
        "rm -rf",
        "sudo ",
        "curl ",
        "wget ",
        "mkfs",
        "dd if=",
        "dd of=",
    )
    if any(fragment in text for fragment in suspicious_fragments):
        return True
    return text in {"whoami", "bash", "sh"}


def _is_system_path(token: str) -> bool:
    return any(token == prefix or token.startswith(prefix + "/") for prefix in SYSTEM_PATH_PREFIXES)


def _has_sensitive_redirection(tokens: tuple[str, ...]) -> bool:
    for index, token in enumerate(tokens):
        if token in {">", ">>"} and index + 1 < len(tokens):
            return _is_system_path(tokens[index + 1])
        target = _redirection_target(token)
        if target and _is_system_path(target):
            return True
    return False


def _redirection_target(token: str) -> str:
    if token.startswith("&>"):
        return token[2:]
    if token.startswith((">", ">>")):
        return token.lstrip(">")
    for marker in (">>", ">"):
        if marker in token:
            prefix, target = token.split(marker, 1)
            if prefix.isdigit() or prefix in {"&"}:
                return target
    return ""


def _has_ifs_substitution(command: str) -> bool:
    return "${ifs}" in command.lower()


def _ifs_expanded_tokens(command: str) -> tuple[str, ...]:
    if not _has_ifs_substitution(command):
        return ()
    expanded = command.replace("${IFS}", " ").replace("${ifs}", " ")
    try:
        return tuple(shlex.split(" ".join(expanded.split()), posix=True))
    except ValueError:
        return ()


def _normalize_executable_tokens(tokens: tuple[str, ...]) -> tuple[str, ...]:
    if not tokens:
        return tokens
    normalized = list(tokens)
    executable_indexes = {0}
    for index, token in enumerate(tokens[:-1]):
        if token in {"|", "xargs", "env"}:
            executable_indexes.add(index + 1)
    for index in executable_indexes:
        normalized[index] = _command_basename(normalized[index])
    return tuple(normalized)


def _unwrap_env_tokens(tokens: tuple[str, ...]) -> tuple[str, ...]:
    if not tokens or tokens[0] != "env":
        return tokens
    tail = list(tokens[1:])
    while tail and (tail[0].startswith("-") or ("=" in tail[0] and not tail[0].startswith("="))):
        tail.pop(0)
    return _normalize_executable_tokens(tuple(tail))


def _command_basename(token: str) -> str:
    normalized = token.lstrip("\\")
    if normalized.startswith("/") and normalized != "/":
        return normalized.rsplit("/", 1)[-1]
    return normalized


def _has_command_substitution(command: str) -> bool:
    return "$(" in command or "`" in command


def _has_process_substitution(command: str) -> bool:
    return "<(" in command or ">(" in command


def _has_non_ascii_marker(command: str) -> bool:
    return any(ord(character) > 127 for character in command)


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
    if tokens[0] == "systemctl" and len(tokens) >= 3 and tokens[1] == "status":
        return True
    return False
