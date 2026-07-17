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
    (
        "secret-import",
        (
            "dotenv",
            "keyring",
            "hvac",
            "google.cloud.secretmanager",
            "azure.keyvault",
        ),
    ),
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

_STEP14_STRICT_FORBIDDEN_AUTHORITY_BOUNDARY_IMPORTS = tuple(
    sorted(
        {
            *FORBIDDEN_AUTHORITY_BOUNDARY_IMPORTS,
            "runtime.agent_loops",
            "runtime.approval_policy_bridge",
            "runtime.bridges.proposal_preview_gate_binding",
            "runtime.execution_readiness_gate",
            "runtime.human_approval_gate",
            "runtime.human_decision_approval_bridge",
            "runtime.live_flows",
            "runtime.orchestration",
            "runtime.patches.post_patch_controlled_test_integration",
            "runtime.provider_live_adapter",
            "runtime.safety.approval_gate",
            "runtime.safety.provider_gateway",
            "runtime.safety.sandbox_workspace",
            "runtime.safety.workspace_guard",
            "runtime.safety.write_kill_switch",
            "runtime.tools.browser_tools",
        }
    )
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

STEP14_CORE_PROTECTED_PATHS = (
    "runtime/artifact_preview.py",
    "runtime/audit/durable_audit_ledger.py",
    "runtime/providers/critic.py",
    "runtime/providers/critic_adversarial_corpus.py",
    "runtime/providers/critic_taxonomy.py",
    "runtime/safety/action_proposal_policy.py",
    "runtime/safety/provider_critic_policy.py",
    "runtime/safety/write_kill_switch.py",
    "runtime/schemas/action_proposal.py",
    "runtime/schemas/action_proposal_projection.py",
    "runtime/schemas/provider_critic.py",
)

WRITE_KILL_SWITCH_PROTECTED_PATH = "runtime/safety/write_kill_switch.py"
WRITE_KILL_SWITCH_SECURITY_ROLE = (
    "fail-closed application-write blocker; non-authoritative and read-only"
)

LEDGER_FILESYSTEM_EXCEPTION_PATH = "runtime/audit/durable_audit_ledger.py"

LEDGER_ALLOWED_FILESYSTEM_CALLS = (
    "fcntl.flock",
    "os.close",
    "os.fdopen",
    "os.fsync",
    "os.open",
)

_LEDGER_REQUIRED_APPEND_FLAGS = frozenset(
    {
        "os.O_APPEND",
        "os.O_CREAT",
        "os.O_RDWR",
    }
)
_LEDGER_REQUIRED_READ_FLAGS = frozenset({"os.O_RDONLY"})
_LEDGER_OPTIONAL_OPEN_FLAGS = frozenset(
    {
        "os.O_CLOEXEC",
        "os.O_NOFOLLOW",
    }
)

_STEP14_CORE_ZONE_BY_PATH = {
    "runtime/artifact_preview.py": "artifact_preview",
    "runtime/audit/durable_audit_ledger.py": "audit",
    "runtime/providers/critic.py": "provider_critic",
    "runtime/providers/critic_adversarial_corpus.py": "provider_critic",
    "runtime/providers/critic_taxonomy.py": "provider_critic",
    "runtime/safety/action_proposal_policy.py": "action_proposal",
    "runtime/safety/provider_critic_policy.py": "provider_critic",
    "runtime/safety/write_kill_switch.py": "other_inert",
    "runtime/schemas/action_proposal.py": "action_proposal",
    "runtime/schemas/action_proposal_projection.py": "action_proposal",
    "runtime/schemas/provider_critic.py": "provider_critic",
}

_FILESYSTEM_MUTATION_CALLS = (
    "os.makedirs",
    "os.mkdir",
    "os.remove",
    "os.rename",
    "os.replace",
    "os.rmdir",
    "os.unlink",
    "pathlib.Path.mkdir",
    "pathlib.Path.rename",
    "pathlib.Path.replace",
    "pathlib.Path.rmdir",
    "pathlib.Path.symlink_to",
    "pathlib.Path.hardlink_to",
    "pathlib.Path.touch",
    "pathlib.Path.unlink",
    "pathlib.Path.write_bytes",
    "pathlib.Path.write_text",
    "shutil.copy",
    "shutil.copy2",
    "shutil.copyfile",
    "shutil.copytree",
    "shutil.move",
    "shutil.rmtree",
    "tempfile.NamedTemporaryFile",
    "tempfile.SpooledTemporaryFile",
    "tempfile.TemporaryDirectory",
    "tempfile.mkstemp",
    "tempfile.mkdtemp",
)

_PATH_MUTATION_METHODS = (
    "hardlink_to",
    "mkdir",
    "rename",
    "replace",
    "rmdir",
    "symlink_to",
    "touch",
    "unlink",
    "write_bytes",
    "write_text",
)

_ENVIRONMENT_ACCESS_SYMBOLS = (
    "os.environ",
    "os.getenv",
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
        "runtime/safety/write_kill_switch.py",
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


@dataclass(frozen=True, order=True)
class StaticCapabilityGraphScan:
    root_path: str
    zone: str
    scanned_paths: tuple[str, ...]
    direct_local_imports: tuple[str, ...]
    direct_external_imports: tuple[str, ...]
    unresolved_imports: tuple[str, ...]
    exemptions_applied: tuple[str, ...]
    violations: tuple[StaticCapabilityViolation, ...]


@dataclass(frozen=True)
class _StaticImportReference:
    module_name: str
    imported_names: tuple[str, ...]
    level: int
    line: int
    column: int


def resolve_step14_core_protected_files(
    repo_root: Path,
) -> tuple[ProtectedRuntimeFile, ...]:
    root = _resolve_repository_root(repo_root)
    if len(STEP14_CORE_PROTECTED_PATHS) != len(set(STEP14_CORE_PROTECTED_PATHS)):
        raise StaticCapabilityPolicyError(
            "duplicate Step 14 core protected paths are not allowed"
        )
    if set(STEP14_CORE_PROTECTED_PATHS) != set(_STEP14_CORE_ZONE_BY_PATH):
        raise StaticCapabilityPolicyError(
            "Step 14 core protected paths and zone mapping differ"
        )

    records = tuple(
        ProtectedRuntimeFile(
            path=path,
            zone=_STEP14_CORE_ZONE_BY_PATH[path],
        )
        for path in sorted(STEP14_CORE_PROTECTED_PATHS)
    )
    for record in records:
        _resolve_repo_path(root, record.path, require_file=True)
        if record.zone not in {
            "provider_critic",
            "artifact_preview",
            "action_proposal",
            "audit",
            "other_inert",
        }:
            raise StaticCapabilityPolicyError(
                f"invalid Step 14 core zone: {record.zone!r}"
            )
    validate_gateway_exceptions(root, records)
    return records


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
    enforce_inert_side_effects: bool = False,
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
    ledger_allowed_os_open_lines = _ledger_allowed_os_open_lines(
        tree,
        path,
        aliases,
    )
    violations: set[StaticCapabilityViolation] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                violation = _import_violation(path, node, alias.name)
                if violation is not None:
                    violations.add(violation)
                if enforce_inert_side_effects:
                    strict_violation = _strict_authority_import_violation(
                        path,
                        node,
                        alias.name,
                    )
                    if strict_violation is not None:
                        violations.add(strict_violation)
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                imported_symbol = f"{node.module}.{alias.name}"
                violation = _import_violation(path, node, imported_symbol)
                if violation is not None:
                    violations.add(violation)
                if enforce_inert_side_effects:
                    strict_violation = _strict_authority_import_violation(
                        path,
                        node,
                        imported_symbol,
                    )
                    if strict_violation is not None:
                        violations.add(strict_violation)
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
                if (
                    enforce_inert_side_effects
                    and imported_symbol in _ENVIRONMENT_ACCESS_SYMBOLS
                ):
                    violations.add(
                        _violation(
                            path,
                            node,
                            "environment-access",
                            imported_symbol,
                            "protected inert source reads process environment state",
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

            if enforce_inert_side_effects:
                strict_violation = _strict_inert_call_violation(
                    path,
                    node,
                    call_symbol,
                    aliases,
                    ledger_allowed_os_open_lines=ledger_allowed_os_open_lines,
                )
                if strict_violation is not None:
                    violations.add(strict_violation)

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

        if enforce_inert_side_effects and isinstance(
            node,
            (ast.Attribute, ast.Name),
        ):
            accessed_symbol = _resolve_call_symbol(node, aliases)
            if accessed_symbol == "os.environ" or accessed_symbol.startswith(
                "os.environ."
            ):
                violations.add(
                    _violation(
                        path,
                        node,
                        "environment-access",
                        accessed_symbol,
                        "protected inert source reads process environment state",
                    )
                )

    return tuple(sorted(violations))


def _strict_inert_call_violation(
    path: str,
    node: ast.Call,
    call_symbol: str,
    aliases: dict[str, str],
    *,
    ledger_allowed_os_open_lines: frozenset[int],
) -> StaticCapabilityViolation | None:
    if call_symbol == "os.getenv" or call_symbol.startswith("os.environ."):
        return _violation(
            path,
            node,
            "environment-access",
            call_symbol,
            "protected inert source reads process environment state",
        )

    normalized_symbol = _path_constructor_call_symbol(node, call_symbol, aliases)
    if normalized_symbol in _FILESYSTEM_MUTATION_CALLS:
        return _violation(
            path,
            node,
            "filesystem-mutation",
            normalized_symbol,
            "protected inert source performs filesystem mutation",
        )

    if normalized_symbol == "os.open":
        if node.lineno in ledger_allowed_os_open_lines:
            return None
        if _os_open_call_is_proven_read_only(node, aliases):
            return None
        return _violation(
            path,
            node,
            "filesystem-mutation",
            normalized_symbol,
            "protected inert source uses mutating os.open flags",
        )
    terminal_symbol = normalized_symbol.rsplit(".", 1)[-1]
    if terminal_symbol in set(_PATH_MUTATION_METHODS) - {"replace"}:
        return _violation(
            path,
            node,
            "filesystem-mutation",
            normalized_symbol or terminal_symbol,
            "protected inert source performs filesystem mutation",
        )
    if terminal_symbol == "open" and _open_call_can_write(node):
        return _violation(
            path,
            node,
            "filesystem-mutation",
            normalized_symbol or "open",
            "protected inert source opens a file in a mutating mode",
        )
    return None


def _os_open_call_is_proven_read_only(
    node: ast.Call,
    aliases: dict[str, str],
) -> bool:
    flags_node: ast.AST | None = node.args[1] if len(node.args) > 1 else None
    for keyword in node.keywords:
        if keyword.arg == "flags":
            flags_node = keyword.value
    flags = _static_open_flags(flags_node, aliases, {})
    if flags is None:
        return False
    return (
        _LEDGER_REQUIRED_READ_FLAGS.issubset(flags)
        and flags <= _LEDGER_REQUIRED_READ_FLAGS | _LEDGER_OPTIONAL_OPEN_FLAGS
        and _os_open_has_no_mode(node)
    )


def _ledger_allowed_os_open_lines(
    tree: ast.AST,
    path: str,
    aliases: dict[str, str],
) -> frozenset[int]:
    if _normalized_policy_path(path) != LEDGER_FILESYSTEM_EXCEPTION_PATH:
        return frozenset()

    flag_values: dict[str, frozenset[str] | None] = {}
    allowed_lines: set[int] = set()
    ordered_nodes = sorted(
        ast.walk(tree),
        key=lambda node: (
            getattr(node, "lineno", 0),
            getattr(node, "col_offset", 0),
            type(node).__name__,
        ),
    )
    for node in ordered_nodes:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            flag_values[node.targets[0].id] = _static_open_flags(
                node.value,
                aliases,
                flag_values,
            )
        elif (
            isinstance(node, ast.AugAssign)
            and isinstance(node.op, ast.BitOr)
            and isinstance(node.target, ast.Name)
        ):
            existing = flag_values.get(node.target.id)
            added = _static_open_flags(node.value, aliases, flag_values)
            flag_values[node.target.id] = (
                None if existing is None or added is None else existing | added
            )
        elif (
            isinstance(node, ast.Call)
            and _resolve_call_symbol(node.func, aliases) == "os.open"
        ):
            flags_node = node.args[1] if len(node.args) > 1 else None
            for keyword in node.keywords:
                if keyword.arg == "flags":
                    flags_node = keyword.value
            flags = _static_open_flags(flags_node, aliases, flag_values)
            if flags is None:
                continue
            permitted_append = (
                _LEDGER_REQUIRED_APPEND_FLAGS.issubset(flags)
                and flags
                <= _LEDGER_REQUIRED_APPEND_FLAGS | _LEDGER_OPTIONAL_OPEN_FLAGS
                and _os_open_mode_is_exact(node, 0o600)
            )
            permitted_read = (
                _LEDGER_REQUIRED_READ_FLAGS.issubset(flags)
                and flags
                <= _LEDGER_REQUIRED_READ_FLAGS | _LEDGER_OPTIONAL_OPEN_FLAGS
                and _os_open_has_no_mode(node)
            )
            if permitted_append or permitted_read:
                allowed_lines.add(node.lineno)
    return frozenset(allowed_lines)


def _static_open_flags(
    node: ast.AST | None,
    aliases: dict[str, str],
    flag_values: dict[str, frozenset[str] | None],
) -> frozenset[str] | None:
    if node is None:
        return None
    if isinstance(node, ast.Name) and node.id in flag_values:
        return flag_values[node.id]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left = _static_open_flags(node.left, aliases, flag_values)
        right = _static_open_flags(node.right, aliases, flag_values)
        return None if left is None or right is None else left | right
    symbol = _resolve_call_symbol(node, aliases)
    if symbol.startswith("os.O_"):
        return frozenset({symbol})
    if (
        isinstance(node, ast.Call)
        and _resolve_call_symbol(node.func, aliases) == "getattr"
    ):
        if (
            len(node.args) >= 2
            and _resolve_call_symbol(node.args[0], aliases) == "os"
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
            and node.args[1].value in {"O_CLOEXEC", "O_NOFOLLOW"}
        ):
            return frozenset({f"os.{node.args[1].value}"})
    if isinstance(node, ast.Constant) and node.value == 0:
        return frozenset()
    return None


def _os_open_mode_is_exact(node: ast.Call, expected_mode: int) -> bool:
    mode_node: ast.AST | None = node.args[2] if len(node.args) > 2 else None
    for keyword in node.keywords:
        if keyword.arg == "mode":
            mode_node = keyword.value
    return isinstance(mode_node, ast.Constant) and mode_node.value == expected_mode


def _os_open_has_no_mode(node: ast.Call) -> bool:
    if len(node.args) > 2:
        return False
    return all(keyword.arg != "mode" for keyword in node.keywords)


def _normalized_policy_path(path: str) -> str | None:
    if type(path) is not str or not path or path.startswith("/") or "\\" in path:
        return None
    parts = path.split("/")
    if any(not part or part in {".", ".."} for part in parts):
        return None
    return "/".join(parts)


def _path_constructor_call_symbol(
    node: ast.Call,
    call_symbol: str,
    aliases: dict[str, str],
) -> str:
    if not isinstance(node.func, ast.Attribute):
        return call_symbol
    receiver = node.func.value
    if not isinstance(receiver, ast.Call):
        return call_symbol
    constructor = _resolve_call_symbol(receiver.func, aliases)
    if constructor == "pathlib.Path" and node.func.attr in _PATH_MUTATION_METHODS:
        return f"pathlib.Path.{node.func.attr}"
    return call_symbol


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


def _os_open_call_can_write(
    node: ast.Call,
    aliases: dict[str, str] | None = None,
) -> bool:
    flags_node: ast.AST | None = node.args[1] if len(node.args) > 1 else None
    for keyword in node.keywords:
        if keyword.arg == "flags":
            flags_node = keyword.value
    if flags_node is None:
        return True
    names = {
        part
        for candidate in ast.walk(flags_node)
        if (part := _resolve_call_symbol(candidate, aliases or {}))
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


def scan_step14_import_graph(
    repo_root: Path,
    protected_files: Iterable[ProtectedRuntimeFile],
    *,
    gateway_exceptions: Sequence[str] = (),
) -> tuple[StaticCapabilityGraphScan, ...]:
    root = _resolve_repository_root(repo_root)
    records = tuple(sorted(protected_files, key=lambda item: (item.path, item.zone)))
    if not records:
        raise StaticCapabilityPolicyError("Step 14 protected root set cannot be empty")
    if len({record.path for record in records}) != len(records):
        raise StaticCapabilityPolicyError("duplicate Step 14 graph roots are forbidden")
    for record in records:
        if record.zone not in PROTECTED_ZONE_NAMES:
            raise StaticCapabilityPolicyError(
                f"unknown protected zone: {record.zone!r}"
            )
        _resolve_repo_path(root, record.path, require_file=True)

    if gateway_exceptions:
        validate_gateway_exceptions(root, records, gateway_exceptions)
    module_index = _build_local_module_index(root)
    return tuple(
        _scan_step14_graph_root(
            root,
            record,
            module_index,
        )
        for record in records
    )


def _scan_step14_graph_root(
    repo_root: Path,
    root_record: ProtectedRuntimeFile,
    module_index: dict[str, str],
) -> StaticCapabilityGraphScan:
    pending: list[tuple[str, tuple[str, ...]]] = [
        (root_record.path, (root_record.path,))
    ]
    visited: set[str] = set()
    queued: set[str] = {root_record.path}
    violations: set[StaticCapabilityViolation] = set()
    unresolved: set[str] = set()
    root_local_imports: set[str] = set()
    root_external_imports: set[str] = set()

    while pending:
        relative_path, dependency_path = pending.pop(0)
        visited.add(relative_path)
        source_path = _resolve_repo_path(repo_root, relative_path, require_file=True)
        try:
            source = source_path.read_text(encoding="utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            violation = StaticCapabilityViolation(
                path=relative_path,
                line=1,
                column=exc.start,
                category="invalid-utf8",
                symbol="utf-8",
                message="protected dependency source is not valid UTF-8",
            )
            violations.add(_with_dependency_path(violation, dependency_path))
            continue

        source_findings = scan_source_for_capabilities(
            source,
            path=relative_path,
            zone_name=_step14_graph_zone(relative_path, root_record),
            enforce_inert_side_effects=True,
        )
        violations.update(
            _with_dependency_path(finding, dependency_path)
            for finding in source_findings
        )
        if any(finding.category == "syntax-error" for finding in source_findings):
            continue

        references = _static_import_references(source, relative_path)
        for reference in references:
            local_paths, external_name, unresolved_name = _resolve_import_reference(
                reference,
                relative_path,
                module_index,
            )
            if relative_path == root_record.path:
                root_local_imports.update(local_paths)
                if external_name is not None:
                    root_external_imports.add(external_name)

            if unresolved_name is not None:
                unresolved_record = f"{relative_path}:{unresolved_name}"
                unresolved.add(unresolved_record)
                violations.add(
                    StaticCapabilityViolation(
                        path=relative_path,
                        line=reference.line,
                        column=reference.column,
                        category="unresolved-local-import",
                        symbol=unresolved_name,
                        message=(
                            "protected dependency import cannot be resolved statically; "
                            f"dependency path: {' -> '.join(dependency_path)}"
                        ),
                    )
                )

            for local_path in local_paths:
                canonical_name = _canonical_module_name(local_path)
                next_dependency_path = (*dependency_path, local_path)
                if _matches_any_module_prefix(
                    canonical_name,
                    _STEP14_STRICT_FORBIDDEN_AUTHORITY_BOUNDARY_IMPORTS,
                ):
                    violations.add(
                        StaticCapabilityViolation(
                            path=relative_path,
                            line=reference.line,
                            column=reference.column,
                            category="authority-boundary-import",
                            symbol=canonical_name,
                            message=(
                                "protected dependency reaches an authority or execution "
                                "boundary; dependency path: "
                                f"{' -> '.join(next_dependency_path)}"
                            ),
                        )
                    )
                    continue
                if local_path not in queued:
                    queued.add(local_path)
                    pending.append((local_path, next_dependency_path))
            pending.sort(key=lambda item: (item[0], item[1]))

    return StaticCapabilityGraphScan(
        root_path=root_record.path,
        zone=root_record.zone,
        scanned_paths=tuple(sorted(visited)),
        direct_local_imports=tuple(sorted(root_local_imports)),
        direct_external_imports=tuple(sorted(root_external_imports)),
        unresolved_imports=tuple(sorted(unresolved)),
        exemptions_applied=(),
        violations=tuple(sorted(violations)),
    )


def _step14_graph_zone(
    relative_path: str,
    root_record: ProtectedRuntimeFile,
) -> str:
    if relative_path == root_record.path:
        return root_record.zone
    return _STEP14_CORE_ZONE_BY_PATH.get(relative_path, "other_inert")


def _build_local_module_index(repo_root: Path) -> dict[str, str]:
    runtime_directory = _resolve_repo_path(
        repo_root,
        "runtime",
        require_file=False,
    )
    if not runtime_directory.is_dir():
        raise StaticCapabilityPolicyError("runtime source directory is missing")

    index: dict[str, str] = {}
    for candidate in sorted(runtime_directory.rglob("*.py")):
        relative = candidate.relative_to(repo_root).as_posix()
        _resolve_repo_path(repo_root, relative, require_file=True)
        canonical_name = _canonical_module_name(relative)
        aliases = (canonical_name, canonical_name.removeprefix("runtime."))
        for module_name in aliases:
            if not module_name:
                continue
            existing = index.get(module_name)
            if existing is not None and existing != relative:
                raise StaticCapabilityPolicyError(
                    f"ambiguous local module {module_name!r}: {existing!r}, {relative!r}"
                )
            index[module_name] = relative
    return index


def _static_import_references(
    source: str,
    path: str,
) -> tuple[_StaticImportReference, ...]:
    tree = ast.parse(source, filename=path)
    aliases = _collect_import_aliases(tree)
    references: list[_StaticImportReference] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                references.append(
                    _StaticImportReference(
                        module_name=alias.name,
                        imported_names=(),
                        level=0,
                        line=node.lineno,
                        column=node.col_offset,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            references.append(
                _StaticImportReference(
                    module_name=node.module or "",
                    imported_names=tuple(alias.name for alias in node.names),
                    level=node.level,
                    line=node.lineno,
                    column=node.col_offset,
                )
            )
        elif isinstance(node, ast.Call) and _resolve_call_symbol(
            node.func,
            aliases,
        ) in {
            "importlib.import_module",
            "builtins.__import__",
            "__import__",
        }:
            if (
                node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                dynamic_target = node.args[0].value
                level = len(dynamic_target) - len(dynamic_target.lstrip("."))
                references.append(
                    _StaticImportReference(
                        module_name=dynamic_target.lstrip("."),
                        imported_names=(),
                        level=level,
                        line=node.lineno,
                        column=node.col_offset,
                    )
                )
    return tuple(
        sorted(
            references,
            key=lambda item: (
                item.line,
                item.column,
                item.level,
                item.module_name,
                item.imported_names,
            ),
        )
    )


def _resolve_import_reference(
    reference: _StaticImportReference,
    importer_path: str,
    module_index: dict[str, str],
) -> tuple[tuple[str, ...], str | None, str | None]:
    base_name = reference.module_name
    if reference.level:
        importer_module = _canonical_module_name(importer_path)
        package_name = (
            importer_module
            if importer_path.endswith("/__init__.py")
            else importer_module.rsplit(".", 1)[0]
        )
        package_parts = package_name.split(".")
        levels_up = reference.level - 1
        if levels_up >= len(package_parts):
            target = "." * reference.level + reference.module_name
            return (), None, target
        prefix = ".".join(package_parts[: len(package_parts) - levels_up])
        base_name = (
            f"{prefix}.{reference.module_name}"
            if reference.module_name
            else prefix
        )

    candidates: list[str] = []
    if base_name:
        candidates.append(base_name)
    for imported_name in reference.imported_names:
        if imported_name != "*" and base_name:
            candidates.append(f"{base_name}.{imported_name}")

    local_paths = tuple(
        sorted(
            {
                module_index[candidate]
                for candidate in candidates
                if candidate in module_index
            }
        )
    )
    if local_paths:
        if (
            reference.level
            and not reference.module_name
            and reference.imported_names
            and not any(
                f"{base_name}.{name}" in module_index
                for name in reference.imported_names
                if name != "*"
            )
        ):
            missing = next(
                (
                    f"{base_name}.{name}"
                    for name in reference.imported_names
                    if name != "*" and f"{base_name}.{name}" not in module_index
                ),
                None,
            )
            if missing is not None:
                return local_paths, None, missing
        return local_paths, None, None

    local_top_levels = {name.split(".", 1)[0] for name in module_index}
    is_local_reference = bool(reference.level) or base_name.startswith("runtime")
    if base_name.split(".", 1)[0] in local_top_levels:
        is_local_reference = True
    if is_local_reference:
        return (), None, base_name or "." * reference.level
    return (), base_name, None


def _canonical_module_name(relative_path: str) -> str:
    if not relative_path.startswith("runtime/") or not relative_path.endswith(".py"):
        raise StaticCapabilityPolicyError(
            f"local dependency is outside runtime source: {relative_path!r}"
        )
    module_path = relative_path[:-3]
    if module_path.endswith("/__init__"):
        module_path = module_path[: -len("/__init__")]
    return module_path.replace("/", ".")


def _with_dependency_path(
    violation: StaticCapabilityViolation,
    dependency_path: Sequence[str],
) -> StaticCapabilityViolation:
    return StaticCapabilityViolation(
        path=violation.path,
        line=violation.line,
        column=violation.column,
        category=violation.category,
        symbol=violation.symbol,
        message=(
            f"{violation.message}; dependency path: "
            f"{' -> '.join(dependency_path)}"
        ),
    )


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


def _strict_authority_import_violation(
    path: str,
    node: ast.AST,
    module_name: str,
) -> StaticCapabilityViolation | None:
    if not _matches_any_module_prefix(
        module_name,
        _STEP14_STRICT_FORBIDDEN_AUTHORITY_BOUNDARY_IMPORTS,
    ):
        return None
    return _violation(
        path,
        node,
        "authority-boundary-import",
        module_name,
        "protected inert source imports an authority or execution boundary",
    )


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
