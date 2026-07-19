"""One fixed subprocess boundary for the pinned German Law Hat CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from runtime.knowledge_modules.contracts import (
    KnowledgeModuleConfiguration,
    KnowledgeModuleError,
)
from runtime.knowledge_modules.selection import KnowledgeModuleQuery


_OPERATIONS = {
    "descriptor": "hat-info",
    "verify": "hat-verify",
    "query": "hat-query",
}


@dataclass(frozen=True, slots=True)
class ExternalCommandResult:
    operation: str
    command: tuple[str, ...]
    returncode: int
    payload: dict[str, Any]
    stderr: str


class GermanLawExternalGateway:
    """Invoke only descriptor, verification, or query on one reviewed module."""

    __slots__ = ()

    @property
    def executable(self) -> str:
        try:
            executable = Path(sys.executable).resolve(strict=True)
        except OSError as exc:
            raise KnowledgeModuleError("MODULE_NOT_AVAILABLE", "Python executable is unavailable") from exc
        if not executable.is_file() or not executable.is_absolute():
            raise KnowledgeModuleError("MODULE_NOT_AVAILABLE", "Python executable is invalid")
        return str(executable)

    def descriptor(self, configuration: KnowledgeModuleConfiguration) -> dict[str, Any]:
        return self._invoke(configuration, "descriptor", None).payload

    def verify(self, configuration: KnowledgeModuleConfiguration) -> ExternalCommandResult:
        return self._invoke(configuration, "verify", None)

    def query(
        self,
        configuration: KnowledgeModuleConfiguration,
        query: KnowledgeModuleQuery,
    ) -> dict[str, Any]:
        return self._invoke(configuration, "query", query).payload

    def _invoke(
        self,
        configuration: KnowledgeModuleConfiguration,
        operation: str,
        query: KnowledgeModuleQuery | None,
    ) -> ExternalCommandResult:
        if operation not in _OPERATIONS:
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "unsupported module operation")
        if operation == "query" and query is None:
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "query operation lacks a query")
        if operation != "query" and query is not None:
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "non-query operation has query data")

        repository = self._repository_root(configuration.module_repository_path)
        command = self._command(configuration, repository, operation, query)
        environment = self._minimal_environment(repository)
        timeout = (
            configuration.verification_timeout_seconds
            if operation == "verify"
            else configuration.query_timeout_seconds
        )
        try:
            completed = subprocess.run(
                command,
                cwd=str(repository),
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
                shell=False,
                close_fds=True,
            )
        except subprocess.TimeoutExpired as exc:
            raise KnowledgeModuleError(
                "MODULE_TIMEOUT", f"German Law {operation} exceeded {timeout} seconds"
            ) from exc
        except OSError as exc:
            raise KnowledgeModuleError("MODULE_NOT_AVAILABLE", "German Law process could not start") from exc

        stdout = self._bounded_bytes(
            completed.stdout,
            configuration.maximum_stdout_bytes,
            "stdout",
        )
        stderr_bytes = self._bounded_bytes(
            completed.stderr,
            configuration.maximum_stderr_bytes,
            "stderr",
        )
        try:
            stderr = stderr_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "module stderr is not UTF-8") from exc
        payload = self._decode_json(stdout)
        allowed_returncodes = {0, 1} if operation == "verify" else {0}
        if completed.returncode not in allowed_returncodes:
            raise KnowledgeModuleError(
                "CORPUS_VERIFICATION_FAILED" if operation == "verify" else "MODULE_OUTPUT_MALFORMED",
                f"German Law {operation} exited with {completed.returncode}: {stderr[:512]}",
            )
        return ExternalCommandResult(
            operation=operation,
            command=command,
            returncode=completed.returncode,
            payload=payload,
            stderr=stderr,
        )

    def _command(
        self,
        configuration: KnowledgeModuleConfiguration,
        repository: Path,
        operation: str,
        query: KnowledgeModuleQuery | None,
    ) -> tuple[str, ...]:
        del repository
        command = [
            self.executable,
            "-m",
            "german_law_corpus.cli",
            _OPERATIONS[operation],
        ]
        if operation == "query":
            assert query is not None
            mode = {
                "SOURCE_DISCOVERY": "source-discovery",
                "VERIFIED_AS_OF": "verified-as-of",
            }[query.retrieval_mode]
            command.extend((f"--mode={mode}", f"--query={query.question}"))
            if query.as_of_date is not None:
                command.append(f"--as-of={query.as_of_date}")
            for jurisdiction in query.jurisdictions:
                command.append(f"--jurisdiction={jurisdiction}")
            for document_type in query.document_types:
                command.append(f"--document-type={document_type}")
            for source_class in query.source_classes:
                command.append(f"--source-class={source_class}")
            for language in query.languages:
                command.append(f"--language={language}")
            if query.include_administrative_rules:
                command.append("--include-administrative-rules")
            command.extend(
                (
                    f"--max-results={query.max_results}",
                    f"--max-excerpt-characters={query.max_excerpt_characters}",
                    f"--max-total-context-characters={query.max_total_context_characters}",
                )
            )
        command.extend((f"--data-root={configuration.corpus_data_root}", "--format=json"))
        return tuple(command)

    @staticmethod
    def _repository_root(value: str) -> Path:
        supplied = Path(value)
        if not supplied.is_absolute() or ".." in supplied.parts:
            raise KnowledgeModuleError("MODULE_NOT_AVAILABLE", "module repository path is invalid")
        absolute = supplied.absolute()
        for component in (absolute, *absolute.parents):
            if component.exists() and component.is_symlink():
                raise KnowledgeModuleError(
                    "MODULE_NOT_AVAILABLE", "module repository symlink is forbidden"
                )
        try:
            root = supplied.resolve(strict=True)
        except OSError as exc:
            raise KnowledgeModuleError("MODULE_NOT_AVAILABLE", "module repository is unavailable") from exc
        if not root.is_dir() or not (root / "src/german_law_corpus/cli.py").is_file():
            raise KnowledgeModuleError("MODULE_NOT_AVAILABLE", "module repository layout is invalid")
        return root

    @staticmethod
    def _minimal_environment(repository: Path) -> dict[str, str]:
        return {
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONNOUSERSITE": "1",
            "PYTHONPATH": str(repository / "src"),
            "PYTHONUTF8": "1",
            "TZ": "UTC",
        }

    @staticmethod
    def _bounded_bytes(value: Any, limit: int, stream: str) -> bytes:
        if not isinstance(value, bytes):
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", f"module {stream} is not bytes")
        if len(value) > limit:
            raise KnowledgeModuleError(
                "MODULE_OUTPUT_LIMIT_EXCEEDED", f"module {stream} exceeds {limit} bytes"
            )
        return value

    @staticmethod
    def _decode_json(value: bytes) -> dict[str, Any]:
        try:
            text = value.decode("utf-8", errors="strict")
            decoded = json.loads(
                text,
                parse_constant=lambda item: (_ for _ in ()).throw(
                    ValueError(f"invalid JSON constant {item}")
                ),
                object_pairs_hook=GermanLawExternalGateway._unique_object,
            )
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "module output is not strict JSON") from exc
        if not isinstance(decoded, dict):
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "module output is not an object")
        return decoded

    @staticmethod
    def _unique_object(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result


__all__ = (
    "ExternalCommandResult",
    "GermanLawExternalGateway",
)
