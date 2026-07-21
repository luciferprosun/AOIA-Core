from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterator
from unittest.mock import patch

from runtime.safety import dry_run_artifact_integration
from runtime.safety.sandbox_artifact_runner import write_sandbox_artifact
from runtime.safety.write_kill_switch import (
    DEFAULT_WRITE_KILL_SWITCH_FILENAME,
    WRITES_DISABLED,
    WRITES_ENABLED,
    WriteKillSwitchCheckResult,
    resolve_required_write_kill_switch,
)
from runtime.schemas.sandbox_artifact import SandboxArtifactRequest, SandboxArtifactResult


@dataclass(frozen=True)
class ExplicitTestWriteKillSwitch:
    directory: str
    path: str

    def check(self) -> WriteKillSwitchCheckResult:
        return resolve_required_write_kill_switch(
            self.path,
            switch_directory=self.directory,
        )

    def write_sandbox_artifact(
        self,
        request: SandboxArtifactRequest,
        workspace_root: str,
        *args: Any,
        **kwargs: Any,
    ) -> SandboxArtifactResult:
        if "write_kill_switch_path" in kwargs or "write_kill_switch_directory" in kwargs:
            raise AssertionError("the explicit test kill-switch owns its scoped configuration")
        return write_sandbox_artifact(
            request,
            workspace_root,
            *args,
            **kwargs,
            write_kill_switch_path=self.path,
            write_kill_switch_directory=self.directory,
        )


@contextmanager
def enabled_test_write_kill_switch() -> Iterator[ExplicitTestWriteKillSwitch]:
    """Provide one isolated, explicit write precondition for a requesting test only."""

    with TemporaryDirectory(prefix="aoia-test-write-kill-switch-") as directory:
        switch_path = Path(directory) / DEFAULT_WRITE_KILL_SWITCH_FILENAME
        switch_path.write_text(WRITES_ENABLED, encoding="utf-8")
        switch_path.chmod(0o600)
        switch = ExplicitTestWriteKillSwitch(directory=directory, path=str(switch_path))
        if not switch.check().writes_allowed:
            raise AssertionError("explicit test write kill-switch did not enable its scoped precondition")
        try:
            yield switch
        finally:
            if switch_path.exists() and not switch_path.is_symlink():
                switch_path.write_text(WRITES_DISABLED, encoding="utf-8")
                switch_path.chmod(0o600)


@contextmanager
def patch_dry_run_writer_with_test_kill_switch() -> Iterator[ExplicitTestWriteKillSwitch]:
    """Inject the explicit test precondition at the legacy dry-run writer call site."""

    with enabled_test_write_kill_switch() as switch:
        with patch.object(
            dry_run_artifact_integration,
            "write_sandbox_artifact",
            side_effect=switch.write_sandbox_artifact,
        ):
            yield switch
