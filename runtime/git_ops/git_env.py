from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from runtime.safety.subprocess_env import build_subprocess_env


@dataclass(frozen=True)
class GitEnvPolicy:
    safe_path: str = "/usr/bin:/bin"
    home: str = "/nonexistent"
    xdg_config_home: str = "/nonexistent"
    terminal_prompt: str = "0"
    locale: str = "C"


def build_hardened_git_env(
    ambient_env: Mapping[str, str] | None = None,
    policy: GitEnvPolicy | None = None,
) -> dict[str, str]:
    del ambient_env
    active_policy = policy or GitEnvPolicy()
    return build_subprocess_env(
        inherit_names=(),
        fixed={
            "PATH": active_policy.safe_path,
            "HOME": active_policy.home,
            "XDG_CONFIG_HOME": active_policy.xdg_config_home,
            "LANG": active_policy.locale,
            "LC_ALL": active_policy.locale,
            "GIT_TERMINAL_PROMPT": active_policy.terminal_prompt,
            "GIT_CONFIG_NOGLOBAL": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
            "GIT_CONFIG": "/dev/null",
            "GIT_CONFIG_COUNT": "0",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "",
            "PAGER": "cat",
            "GIT_EDITOR": ":",
            "VISUAL": ":",
            "EDITOR": ":",
            "GIT_ASKPASS": "",
            "SSH_ASKPASS": "",
            "GIT_SSH_COMMAND": "",
            "GIT_EXTERNAL_DIFF": "",
            "GIT_DIFF_OPTS": "",
            "GIT_TRACE": "0",
            "GIT_TRACE_PACKET": "0",
            "GIT_TRACE_CURL": "0",
        },
    )
