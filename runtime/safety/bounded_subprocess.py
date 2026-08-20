from __future__ import annotations

import math
import subprocess
from collections.abc import Mapping, Sequence
from numbers import Real
from os import PathLike
from typing import Any


SUBPROCESS_HARD_TIMEOUT_REASON_CODE = "SUBPROCESS_HARD_TIMEOUT"
MIN_HARD_TIMEOUT_SECONDS = 0.01
MAX_HARD_TIMEOUT_SECONDS = 600.0


class SubprocessTimeoutPolicyError(ValueError):
    """Raised before process creation when a hard timeout is missing or unsafe."""


def validate_hard_timeout_seconds(value: object) -> float:
    """Return a finite hard timeout within the runtime-owned global bounds."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise SubprocessTimeoutPolicyError(
            "subprocess hard timeout must be a finite number of seconds"
        )
    seconds = float(value)
    if not math.isfinite(seconds):
        raise SubprocessTimeoutPolicyError(
            "subprocess hard timeout must be a finite number of seconds"
        )
    if seconds < MIN_HARD_TIMEOUT_SECONDS or seconds > MAX_HARD_TIMEOUT_SECONDS:
        raise SubprocessTimeoutPolicyError(
            "subprocess hard timeout is outside runtime policy bounds"
        )
    return seconds


def run_bounded_subprocess(
    args: Sequence[str | bytes | PathLike[str] | PathLike[bytes]],
    *,
    env: Mapping[str, str],
    timeout: object,
    **kwargs: Any,
) -> subprocess.CompletedProcess[Any]:
    """Run one child with an explicit environment and finite hard timeout.

    ``subprocess.run`` enforces its timeout at the ``Popen.communicate`` child
    boundary. On expiry it kills the child, waits for termination, and only then
    raises ``TimeoutExpired``. Keeping the primitive in this one function lets
    structural tests reject future raw or unbounded process sites.
    """
    seconds = validate_hard_timeout_seconds(timeout)
    if kwargs.get("shell") is True:
        raise SubprocessTimeoutPolicyError(
            "bounded subprocess execution does not permit shell=True"
        )
    child_env = {str(name): str(value) for name, value in env.items()}
    return subprocess.run(
        args,
        env=child_env,
        timeout=seconds,
        **kwargs,
    )
