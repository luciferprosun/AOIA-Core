from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


PROTECTED_ZONE_NAMES = (
    "provider_critic",
    "artifact_preview",
    "action_proposal",
    "audit",
    "retrieval",
    "knowledge_engine",
    "unix_hat",
    "knowledge_routing",
    "visible_review",
    "freeze_evidence",
    "other_inert",
    "metadata_memory",
)

GATEWAY_EXCEPTION_PATHS = (
    "runtime/providers/gateway.py",
)

FORBIDDEN_IMPORTS_BY_CATEGORY = (
    ("process-import", ("subprocess", "commands", "pty")),
    (
        "network-import",
        (
            "socket",
            "ssl",
            "http.client",
            "requests",
            "httpx",
            "aiohttp",
            "urllib.request",
            "urllib3",
            "ftplib",
            "telnetlib",
            "smtplib",
            "websockets",
        ),
    ),
    ("browser-import", ("webbrowser", "selenium", "playwright", "pyppeteer")),
    ("git-import", ("git", "gitpython", "dulwich", "pygit2")),
    (
        "provider-sdk-import",
        (
            "openai",
            "anthropic",
            "cohere",
            "mistralai",
            "groq",
            "ollama",
            "google.generativeai",
            "google.genai",
            "boto3",
            "botocore",
            "azure.ai",
        ),
    ),
    ("package-manager-import", ("pip", "ensurepip")),
)

FORBIDDEN_IMPORT_ROOTS = tuple(
    root
    for _category, roots in FORBIDDEN_IMPORTS_BY_CATEGORY
    for root in roots
)

FORBIDDEN_AUTHORITY_BOUNDARY_IMPORTS = (
    "runtime.control_write",
    "runtime.human_decision_gate_integration",
    "runtime.human_decision_gated_artifact_write",
    "runtime.safety.sandbox_artifact_runner",
    "runtime.safety.approval_artifact_gate",
    "runtime.patches.controlled_patch_apply",
    "runtime.patches.patch_barrier",
    "runtime.providers.gateway",
    "runtime.provider_clients",
    "runtime.providers.openai_compatible",
    "runtime.providers.gemma_provider",
    "runtime.providers.gemini_provider",
    "runtime.package_ops.controlled_package_install",
    "runtime.browser_ops.controlled_browser_automation",
    "runtime.browser_ops.controlled_browser_read",
    "runtime.git_ops.controlled_git_commit",
    "runtime.git_ops.git_controlled_push",
    "runtime.execution.controlled_test_runner",
    "runtime.tools.executor",
)

FORBIDDEN_CALLS = (
    "subprocess.run",
    "subprocess.call",
    "subprocess.check_call",
    "subprocess.check_output",
    "subprocess.Popen",
    "os.system",
    "os.popen",
    "webbrowser.open",
    "eval",
    "exec",
    "builtins.eval",
    "builtins.exec",
)

ROUTING_FORBIDDEN_DISPATCH_CALLS = (
    "call",
    "candidate",
    "dispatch",
    "execute",
    "invoke",
    "retrieve",
    "route_candidate",
    "run",
)

ROUTING_FORBIDDEN_WRITE_METHODS = (
    "write_bytes",
    "write_text",
)


_EXPLICIT_ZONE_PATHS = {
    "provider_critic": (
        "runtime/provider_critic_review.py",
        "runtime/provider_review_projection.py",
        "runtime/providers/critic.py",
        "runtime/providers/critic_adversarial_corpus.py",
        "runtime/providers/critic_taxonomy.py",
        "runtime/providers/provider_response_schema.py",
        "runtime/safety/provider_critic_policy.py",
        "runtime/schemas/provider_critic.py",
    ),
    "artifact_preview": (
        "runtime/artifact_preview.py",
        "runtime/bridges/proposal_to_preview.py",
        "runtime/patches/patch_preview.py",
        "runtime/browser_ops/browser_automation_preview.py",
        "runtime/git_ops/git_write_preview.py",
        "runtime/git_ops/git_commit_preview.py",
        "runtime/git_ops/git_push_preview.py",
        "runtime/schemas/tool_call_preview.py",
    ),
    "action_proposal": (
        "runtime/schemas/action_proposal.py",
        "runtime/schemas/action_proposal_projection.py",
        "runtime/safety/action_proposal_policy.py",
        "runtime/proposal_intake.py",
        "runtime/proposal_review_packet.py",
        "runtime/proposer_source_boundary.py",
        "runtime/package_ops/package_install_proposal.py",
        "runtime/provider_proposer_adapter.py",
    ),
    "metadata_memory": (
        "runtime/knowledge_hub_attachment.py",
    ),
    "audit": (),
    "retrieval": (
        "runtime/retrieval/facade.py",
        "runtime/retrieval/feature_flags.py",
        "runtime/retrieval/unix_runtime_adapter.py",
    ),
    "knowledge_engine": (
        "runtime/knowledge/rhcsa_engine.py",
    ),
    "unix_hat": (
        "runtime/memory_hat_registry.py",
    ),
    "knowledge_routing": (
        "runtime/orchestrator/knowledge_router.py",
    ),
    "visible_review": (
        "runtime/visible_unix_prototype.py",
    ),
    "freeze_evidence": (
        "runtime/final_repository_freeze.py",
        "runtime/unix_full_validation_freeze.py",
    ),
    "other_inert": (
        "runtime/browser_ops/browser_automation_governance.py",
        "runtime/decision_implication_review.py",
        "runtime/decision_review_handoff.py",
        "runtime/human_review_decision.py",
        "runtime/human_review_decision_projection.py",
        "runtime/human_review_decision_validator.py",
        "runtime/patches/patch_policy.py",
        "runtime/prompt_packet_review.py",
        "runtime/provider_config_review.py",
        "runtime/provider_live_readiness_review.py",
        "runtime/provider_request_review.py",
        "runtime/review_packet_projection.py",
        "runtime/review_session_bundle.py",
        "runtime/review_session_snapshot.py",
        "runtime/secret_boundary_review.py",
    ),
}

_ZONE_DIRECTORY_PATHS = {
    "provider_critic": ("runtime/provider_critic",),
    "metadata_memory": (
        "runtime/schemas",
        "runtime/memory",
    ),
    "audit": ("runtime/audit",),
    "retrieval": ("runtime/retrieval/linux",),
    "knowledge_engine": ("runtime/knowledge",),
    "unix_hat": ("runtime/memory_hats",),
}

_ZONE_RESOLUTION_ORDER = (
    "provider_critic",
    "artifact_preview",
    "action_proposal",
    "audit",
    "retrieval",
    "knowledge_engine",
    "unix_hat",
    "knowledge_routing",
    "visible_review",
    "freeze_evidence",
    "other_inert",
    "metadata_memory",
)

_REQUIRED_ZONE_PATHS = {
    "provider_critic": "runtime/providers/critic.py",
    "artifact_preview": "runtime/artifact_preview.py",
    "action_proposal": "runtime/schemas/action_proposal.py",
    "metadata_memory": "runtime/memory/runtime_schemas.py",
    "audit": "runtime/audit/durable_audit_ledger.py",
    "retrieval": "runtime/retrieval/facade.py",
    "knowledge_engine": "runtime/knowledge/rhcsa_engine.py",
    "unix_hat": "runtime/memory_hat_registry.py",
    "knowledge_routing": "runtime/orchestrator/knowledge_router.py",
    "visible_review": "runtime/visible_unix_prototype.py",
    "freeze_evidence": "runtime/unix_full_validation_freeze.py",
    "other_inert": "runtime/human_review_decision.py",
}


class StaticCapabilityPolicyError(ValueError):
    """A deterministic, fail-closed static-policy configuration error."""


@dataclass(frozen=True, order=True)
class StaticCapabilityViolation:
    path: str
    line: int
    column: int
    category: str
    symbol: str
    message: str


@dataclass(frozen=True, order=True)
class ProtectedRuntimeFile:
    path: str
    zone: str


def resolve_protected_runtime_files(
    repo_root: Path,
    zone_names: Sequence[str] | None = None,
) -> tuple[ProtectedRuntimeFile, ...]:
    root = _resolve_repository_root(repo_root)
    requested_zones = _validate_zone_names(zone_names)
    records: dict[str, ProtectedRuntimeFile] = {}

    for zone in _ZONE_RESOLUTION_ORDER:
        if zone not in requested_zones:
            continue

        explicit_paths = _EXPLICIT_ZONE_PATHS[zone]
        if len(explicit_paths) != len(set(explicit_paths)):
            raise StaticCapabilityPolicyError(
                f"duplicate explicit protected path in zone {zone!r}"
            )

        candidates = list(explicit_paths)
        for directory in _ZONE_DIRECTORY_PATHS.get(zone, ()):
            directory_path = _resolve_repo_path(root, directory, require_file=False)
            if not directory_path.is_dir():
                raise StaticCapabilityPolicyError(
                    f"protected directory is missing: {directory}"
                )
            candidates.extend(
                path.relative_to(root).as_posix()
                for path in directory_path.glob("*.py")
                if path.is_file()
            )

        for relative in sorted(set(candidates)):
            _resolve_repo_path(root, relative, require_file=True)
            existing = records.get(relative)
            if existing is not None:
                continue
            records[relative] = ProtectedRuntimeFile(path=relative, zone=zone)

    resolved = tuple(sorted(records.values(), key=lambda item: (item.path, item.zone)))
    validate_protected_policy(root, resolved, required_zones=requested_zones)
    return resolved


def validate_protected_policy(
    repo_root: Path,
    protected_files: Iterable[ProtectedRuntimeFile],
    *,
    required_zones: Sequence[str] | None = None,
) -> None:
    root = _resolve_repository_root(repo_root)
    zones = _validate_zone_names(required_zones)
    records = tuple(protected_files)

    if not FORBIDDEN_IMPORT_ROOTS:
        raise StaticCapabilityPolicyError("forbidden import policy is empty")
    if not FORBIDDEN_CALLS:
        raise StaticCapabilityPolicyError("forbidden call policy is empty")
    if not FORBIDDEN_AUTHORITY_BOUNDARY_IMPORTS:
        raise StaticCapabilityPolicyError("authority-boundary import policy is empty")

    paths = [record.path for record in records]
    if len(paths) != len(set(paths)):
        raise StaticCapabilityPolicyError("duplicate protected paths are not allowed")

    for record in records:
        if record.zone not in PROTECTED_ZONE_NAMES:
            raise StaticCapabilityPolicyError(
                f"unknown protected zone: {record.zone!r}"
            )
        _resolve_repo_path(root, record.path, require_file=True)

    for zone in zones:
        zone_records = tuple(record for record in records if record.zone == zone)
        if not zone_records:
            raise StaticCapabilityPolicyError(
                f"protected zone resolved to no files: {zone}"
            )
        required_path = _REQUIRED_ZONE_PATHS[zone]
        if required_path not in {record.path for record in zone_records}:
            raise StaticCapabilityPolicyError(
                f"protected zone {zone!r} is missing required path {required_path!r}"
            )

    validate_gateway_exceptions(root, records)


def validate_gateway_exceptions(
    repo_root: Path,
    protected_files: Iterable[ProtectedRuntimeFile],
    exceptions: Sequence[str] = GATEWAY_EXCEPTION_PATHS,
) -> tuple[str, ...]:
    root = _resolve_repository_root(repo_root)
    protected_paths = {record.path for record in protected_files}

    if len(exceptions) != len(set(exceptions)):
        raise StaticCapabilityPolicyError("duplicate gateway exceptions are forbidden")

    for relative in exceptions:
        if any(character in relative for character in "*?[]"):
            raise StaticCapabilityPolicyError(
                f"wildcard gateway exception is forbidden: {relative!r}"
            )
        _resolve_repo_path(root, relative, require_file=True)
        if relative in protected_paths:
            raise StaticCapabilityPolicyError(
                f"protected file cannot be a gateway exception: {relative!r}"
            )

    return tuple(sorted(exceptions))


def scan_source_for_capabilities(
    source: str,
    *,
    path: str,
    zone_name: str,
) -> tuple[StaticCapabilityViolation, ...]:
    _validate_zone_names((zone_name,))

    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        return (
            StaticCapabilityViolation(
                path=path,
                line=exc.lineno or 1,
                column=max((exc.offset or 1) - 1, 0),
                category="syntax-error",
                symbol="ast.parse",
                message=f"protected source did not parse: {exc.msg}",
            ),
        )

    aliases = _collect_import_aliases(tree)
    violations: set[StaticCapabilityViolation] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                violation = _import_violation(path, node, alias.name)
                if violation is not None:
                    violations.add(violation)
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                imported_symbol = f"{node.module}.{alias.name}"
                violation = _import_violation(path, node, imported_symbol)
                if violation is not None:
                    violations.add(violation)
                dangerous_symbol = _dangerous_imported_symbol(node.module, alias.name)
                if dangerous_symbol is not None:
                    violations.add(
                        _violation(
                            path,
                            node,
                            "dangerous-symbol-import",
                            dangerous_symbol,
                            "protected source imports a dangerous callable",
                        )
                    )
        elif isinstance(node, ast.Call):
            call_symbol = _resolve_call_symbol(node.func, aliases)
            if call_symbol in FORBIDDEN_CALLS:
                violations.add(
                    _violation(
                        path,
                        node,
                        "dangerous-call",
                        call_symbol,
                        "protected source calls a dangerous capability",
                    )
                )

            if zone_name == "knowledge_routing":
                routing_violation = _routing_call_violation(
                    path,
                    node,
                    call_symbol,
                )
                if routing_violation is not None:
                    violations.add(routing_violation)

            if call_symbol in {
                "importlib.import_module",
                "builtins.__import__",
                "__import__",
            }:
                dynamic_violation = _dynamic_import_violation(
                    path,
                    node,
                    call_symbol,
                )
                if dynamic_violation is not None:
                    violations.add(dynamic_violation)

            for keyword in node.keywords:
                if (
                    keyword.arg == "shell"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                ):
                    violations.add(
                        _violation(
                            path,
                            keyword,
                            "shell-true",
                            call_symbol or "<unresolved-call>",
                            "protected source passes shell=True",
                        )
                    )

    return tuple(sorted(violations))


def _routing_call_violation(
    path: str,
    node: ast.Call,
    call_symbol: str,
) -> StaticCapabilityViolation | None:
    terminal_symbol = call_symbol.rsplit(".", 1)[-1]
    if terminal_symbol in ROUTING_FORBIDDEN_WRITE_METHODS:
        return _violation(
            path,
            node,
            "routing-filesystem-write",
            call_symbol or terminal_symbol,
            "knowledge routing must return report data without writing files",
        )

    if terminal_symbol in ROUTING_FORBIDDEN_DISPATCH_CALLS:
        return _violation(
            path,
            node,
            "routing-dispatch",
            call_symbol or terminal_symbol,
            "knowledge routing must not invoke retrieval or caller-supplied callables",
        )

    if call_symbol in {"open", "builtins.open"} and _open_call_can_write(node):
        return _violation(
            path,
            node,
            "routing-filesystem-write",
            call_symbol,
            "knowledge routing must not open files in a mutating mode",
        )

    if call_symbol == "os.open" and _os_open_call_can_write(node):
        return _violation(
            path,
            node,
            "routing-filesystem-write",
            call_symbol,
            "knowledge routing must not use write/create/truncate os.open flags",
        )
    return None


def _open_call_can_write(node: ast.Call) -> bool:
    mode_node: ast.AST | None = node.args[1] if len(node.args) > 1 else None
    for keyword in node.keywords:
        if keyword.arg == "mode":
            mode_node = keyword.value
    if mode_node is None:
        return False
    if not isinstance(mode_node, ast.Constant) or not isinstance(mode_node.value, str):
        return True
    return any(flag in mode_node.value for flag in "wax+")


def _os_open_call_can_write(node: ast.Call) -> bool:
    flags_node: ast.AST | None = node.args[1] if len(node.args) > 1 else None
    for keyword in node.keywords:
        if keyword.arg == "flags":
            flags_node = keyword.value
    if flags_node is None:
        return True
    names = {
        part
        for candidate in ast.walk(flags_node)
        if (part := _resolve_call_symbol(candidate, {}))
    }
    forbidden_flags = {
        "os.O_APPEND",
        "os.O_CREAT",
        "os.O_RDWR",
        "os.O_TRUNC",
        "os.O_WRONLY",
    }
    return bool(names.intersection(forbidden_flags)) or not names


def scan_file_for_capabilities(
    repo_root: Path,
    protected_file: ProtectedRuntimeFile,
) -> tuple[StaticCapabilityViolation, ...]:
    root = _resolve_repository_root(repo_root)
    if protected_file.zone not in PROTECTED_ZONE_NAMES:
        raise StaticCapabilityPolicyError(
            f"unknown protected zone: {protected_file.zone!r}"
        )
    source_path = _resolve_repo_path(root, protected_file.path, require_file=True)
    try:
        source = source_path.read_text(encoding="utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        return (
            StaticCapabilityViolation(
                path=protected_file.path,
                line=1,
                column=exc.start,
                category="invalid-utf8",
                symbol="utf-8",
                message="protected source is not valid UTF-8",
            ),
        )
    return scan_source_for_capabilities(
        source,
        path=protected_file.path,
        zone_name=protected_file.zone,
    )


def scan_protected_repository(
    repo_root: Path,
    zone_names: Sequence[str] | None = None,
) -> tuple[StaticCapabilityViolation, ...]:
    protected_files = resolve_protected_runtime_files(repo_root, zone_names)
    violations = (
        violation
        for protected_file in protected_files
        for violation in scan_file_for_capabilities(repo_root, protected_file)
    )
    return tuple(sorted(violations))


def format_violations(violations: Iterable[StaticCapabilityViolation]) -> str:
    return "\n".join(
        (
            f"{violation.path}:{violation.line}:{violation.column}: "
            f"{violation.category}: {violation.symbol}: {violation.message}"
        )
        for violation in sorted(violations)
    )


def _collect_import_aliases(tree: ast.AST) -> dict[str, str]:
    aliases: dict[str, str] = {
        "__import__": "builtins.__import__",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local_name = alias.asname or alias.name.split(".", 1)[0]
                aliases[local_name] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                local_name = alias.asname or alias.name
                aliases[local_name] = f"{node.module}.{alias.name}"
    return aliases


def _resolve_call_symbol(node: ast.AST, aliases: dict[str, str]) -> str:
    parts = _attribute_parts(node)
    if not parts:
        return ""
    root = aliases.get(parts[0], parts[0])
    return ".".join((root, *parts[1:]))


def _attribute_parts(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Attribute):
        return (*_attribute_parts(node.value), node.attr)
    return ()


def _import_violation(
    path: str,
    node: ast.AST,
    module_name: str,
) -> StaticCapabilityViolation | None:
    category = _forbidden_import_category(module_name)
    if category is not None:
        return _violation(
            path,
            node,
            category,
            module_name,
            "protected source imports a forbidden capability",
        )
    if _matches_any_module_prefix(module_name, FORBIDDEN_AUTHORITY_BOUNDARY_IMPORTS):
        return _violation(
            path,
            node,
            "authority-boundary-import",
            module_name,
            "protected source imports an authority or execution boundary",
        )
    return None


def _forbidden_import_category(module_name: str) -> str | None:
    normalized = module_name.casefold()
    for category, roots in FORBIDDEN_IMPORTS_BY_CATEGORY:
        if _matches_any_module_prefix(normalized, roots):
            return category
    return None


def _dangerous_imported_symbol(module_name: str, imported_name: str) -> str | None:
    candidate = f"{module_name}.{imported_name}"
    if candidate in FORBIDDEN_CALLS:
        return candidate
    if module_name == "importlib" and imported_name == "import_module":
        return candidate
    if module_name == "builtins" and imported_name == "__import__":
        return candidate
    return None


def _dynamic_import_violation(
    path: str,
    node: ast.Call,
    call_symbol: str,
) -> StaticCapabilityViolation | None:
    if not node.args:
        target = "<missing-target>"
        message = "dynamic import target is missing and cannot be proven safe"
    else:
        first_argument = node.args[0]
        if isinstance(first_argument, ast.Constant) and isinstance(first_argument.value, str):
            target = first_argument.value
            category = _forbidden_import_category(target)
            if category is None and not _matches_any_module_prefix(
                target,
                FORBIDDEN_AUTHORITY_BOUNDARY_IMPORTS,
            ):
                return None
            message = f"dynamic import targets forbidden module {target!r}"
        else:
            target = "<unresolved-target>"
            message = "dynamic import target cannot be proven safe"

    return _violation(
        path,
        node,
        "dynamic-import",
        f"{call_symbol}({target})",
        message,
    )


def _violation(
    path: str,
    node: ast.AST,
    category: str,
    symbol: str,
    message: str,
) -> StaticCapabilityViolation:
    return StaticCapabilityViolation(
        path=path,
        line=getattr(node, "lineno", 1),
        column=getattr(node, "col_offset", 0),
        category=category,
        symbol=symbol,
        message=message,
    )


def _matches_any_module_prefix(module_name: str, prefixes: Sequence[str]) -> bool:
    normalized = module_name.casefold()
    return any(
        normalized == prefix.casefold()
        or normalized.startswith(prefix.casefold() + ".")
        for prefix in prefixes
    )


def _validate_zone_names(zone_names: Sequence[str] | None) -> tuple[str, ...]:
    requested = PROTECTED_ZONE_NAMES if zone_names is None else tuple(zone_names)
    if not requested:
        raise StaticCapabilityPolicyError("protected zone selection cannot be empty")
    if len(requested) != len(set(requested)):
        raise StaticCapabilityPolicyError("duplicate protected zone names are forbidden")
    unknown = sorted(set(requested) - set(PROTECTED_ZONE_NAMES))
    if unknown:
        raise StaticCapabilityPolicyError(
            f"unknown protected zones: {', '.join(unknown)}"
        )
    return tuple(requested)


def _resolve_repository_root(repo_root: Path) -> Path:
    root = Path(repo_root)
    try:
        resolved = root.resolve(strict=True)
    except OSError as exc:
        raise StaticCapabilityPolicyError(
            f"repository root cannot be resolved: {root}"
        ) from exc
    if not resolved.is_dir():
        raise StaticCapabilityPolicyError(
            f"repository root is not a directory: {resolved}"
        )
    return resolved


def _resolve_repo_path(
    repo_root: Path,
    relative_path: str,
    *,
    require_file: bool,
) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute():
        raise StaticCapabilityPolicyError(
            f"protected path must be repository-relative: {relative_path!r}"
        )

    lexical_path = repo_root / relative
    try:
        resolved = lexical_path.resolve(strict=True)
    except OSError as exc:
        raise StaticCapabilityPolicyError(
            f"protected path cannot be resolved: {relative_path!r}"
        ) from exc

    if resolved != repo_root and repo_root not in resolved.parents:
        raise StaticCapabilityPolicyError(
            f"protected path escapes repository root: {relative_path!r}"
        )
    if lexical_path.is_symlink():
        raise StaticCapabilityPolicyError(
            f"protected file cannot be a symlink: {relative_path!r}"
        )
    if require_file and not resolved.is_file():
        raise StaticCapabilityPolicyError(
            f"protected path is not a file: {relative_path!r}"
        )
    return resolved
