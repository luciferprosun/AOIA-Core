from __future__ import annotations

import os
from collections.abc import Iterable, Mapping


class SubprocessEnvironmentPolicyError(ValueError):
    """Raised when runtime code requests an environment outside the child policy."""


# These are the only ambient values copied from the AOIA parent process. Values
# such as PYTHONPATH, loader settings, provider configuration, and credentials
# are deliberately absent.
SAFE_INHERITED_ENVIRONMENT_VARIABLES = frozenset(
    {
        "HOME",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "PATH",
        "TEMP",
        "TERM",
        "TMP",
        "TMPDIR",
    }
)

# Specialized controlled subprocesses need fixed process-control values. These
# names may be supplied by runtime code, but are never copied from the ambient
# environment unless they are also present in the inherited allowlist above.
SAFE_FIXED_ENVIRONMENT_VARIABLES = frozenset(
    {
        *SAFE_INHERITED_ENVIRONMENT_VARIABLES,
        "EDITOR",
        "GIT_ASKPASS",
        "GIT_CONFIG",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_NOGLOBAL",
        "GIT_CONFIG_NOSYSTEM",
        "GIT_CONFIG_SYSTEM",
        "GIT_DIFF_OPTS",
        "GIT_EDITOR",
        "GIT_EXTERNAL_DIFF",
        "GIT_OPTIONAL_LOCKS",
        "GIT_PAGER",
        "GIT_SSH_COMMAND",
        "GIT_TERMINAL_PROMPT",
        "GIT_TRACE",
        "GIT_TRACE_CURL",
        "GIT_TRACE_PACKET",
        "NPM_CONFIG_AUDIT",
        "NPM_CONFIG_FUND",
        "NPM_CONFIG_IGNORE_SCRIPTS",
        "NPM_CONFIG_OFFLINE",
        "PAGER",
        "PIP_DISABLE_PIP_VERSION_CHECK",
        "PIP_NO_INDEX",
        "PIP_NO_INPUT",
        "PYTHONDONTWRITEBYTECODE",
        "PYTHONNOUSERSITE",
        "PYTHONPATH",
        "PYTHONPYCACHEPREFIX",
        "SSH_ASKPASS",
        "VIRTUAL_ENV",
        "VISUAL",
        "XDG_CONFIG_HOME",
    }
)

_SENSITIVE_EXACT_NAMES = frozenset(
    {
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "DATABASE_URL",
        "GITHUB_TOKEN",
        "PRIVATE_KEY",
    }
)
_SENSITIVE_SUFFIXES = (
    "_API_KEY",
    "_PASSWORD",
    "_PRIVATE_KEY",
    "_SECRET",
    "_TOKEN",
)


def is_sensitive_environment_name(name: str) -> bool:
    """Return whether an environment variable name is credential-shaped."""
    normalized = name.upper()
    return (
        normalized in _SENSITIVE_EXACT_NAMES
        or normalized.endswith(_SENSITIVE_SUFFIXES)
        or "_CREDENTIAL" in normalized
    )


def build_subprocess_env(
    ambient_env: Mapping[str, str] | None = None,
    *,
    inherit_names: Iterable[str] | None = None,
    fixed: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build a new minimal environment for an AOIA child process.

    Ambient values are copied only through the small OS/runtime allowlist.
    Specialized callers may add fixed, policy-approved process-control values;
    credential-shaped names are rejected even if a future allowlist edit were
    to include one accidentally. The parent mapping is never modified.
    """
    source = os.environ if ambient_env is None else ambient_env
    requested_names = (
        SAFE_INHERITED_ENVIRONMENT_VARIABLES
        if inherit_names is None
        else frozenset(inherit_names)
    )
    unsupported_inherited = requested_names - SAFE_INHERITED_ENVIRONMENT_VARIABLES
    if unsupported_inherited:
        names = ", ".join(sorted(unsupported_inherited))
        raise SubprocessEnvironmentPolicyError(
            f"subprocess environment inheritance is not allowlisted: {names}"
        )

    child_env: dict[str, str] = {}
    for name in sorted(requested_names):
        if is_sensitive_environment_name(name):
            continue
        value = source.get(name)
        if value is not None:
            child_env[name] = str(value)

    if "PATH" in requested_names and "PATH" not in child_env:
        child_env["PATH"] = os.defpath

    for name, value in (fixed or {}).items():
        if is_sensitive_environment_name(name):
            raise SubprocessEnvironmentPolicyError(
                f"credential-shaped subprocess environment variable is blocked: {name}"
            )
        if name not in SAFE_FIXED_ENVIRONMENT_VARIABLES:
            raise SubprocessEnvironmentPolicyError(
                f"fixed subprocess environment variable is not allowlisted: {name}"
            )
        if not isinstance(value, str):
            raise SubprocessEnvironmentPolicyError(
                f"fixed subprocess environment value must be text: {name}"
            )
        child_env[name] = value

    return child_env
