"""Bounded local developer CLI for explicit Knowledge Hub retrieval."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from runtime.knowledge_modules.contracts import KnowledgeModuleError
from runtime.knowledge_modules.german_law import (
    GERMAN_LAW_MODULE_ID,
    production_german_law_configuration,
    production_knowledge_module_registry,
)
from runtime.knowledge_modules.hub import KnowledgeHub1A, KnowledgeHub1B
from runtime.knowledge_modules.planning import KNOWLEDGE_QUERY_SCHEMA_VERSION, KnowledgeQuery
from runtime.knowledge_modules.policy import DEFAULT_KNOWLEDGE_HUB_POLICY
from runtime.knowledge_modules.profiles import (
    PROFILE_MODULE_SCHEMA_VERSION,
    PROFILE_SCHEMA_VERSION,
    KnowledgeProfile,
    KnowledgeProfileModuleSelection,
)
from runtime.knowledge_modules.selection import (
    KnowledgeModuleQuery,
    KnowledgeModuleSelection,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aoia-knowledge-query",
        description="Explicit, provider-free, read-only Knowledge Module retrieval.",
        allow_abbrev=False,
    )
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--list-modules", action="store_true")
    parser.add_argument("--module", action="append", dest="modules")
    parser.add_argument("--question")
    parser.add_argument(
        "--retrieval-mode",
        choices=("source-discovery", "verified-as-of"),
    )
    parser.add_argument("--as-of")
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--max-excerpt-characters", type=int, default=2_000)
    parser.add_argument("--max-total-context-characters", type=int, default=16_000)
    parser.add_argument("--include-administrative-rules", action="store_true")
    parser.add_argument("--module-repository")
    parser.add_argument("--module-data-root")
    parser.add_argument("--expected-module-head")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    return parser


def _repository_root(value: str) -> Path:
    supplied = Path(value)
    if not supplied.is_absolute():
        supplied = Path.cwd() / supplied
    if ".." in supplied.parts:
        raise KnowledgeModuleError("INVALID_MODULE_CONFIGURATION", "repository root traverses")
    try:
        root = supplied.resolve(strict=True)
    except OSError as exc:
        raise KnowledgeModuleError("INVALID_MODULE_CONFIGURATION", "repository root is unavailable") from exc
    if not root.is_dir() or not (root / "pyproject.toml").is_file():
        raise KnowledgeModuleError("INVALID_MODULE_CONFIGURATION", "repository root is invalid")
    return root


def _json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _text_result(value: dict[str, object]) -> str:
    lines = [
        f"status: {value['status']}",
        f"selected_modules: {', '.join(value['selected_module_ids'])}",
        f"authority_status: {value['authority_status']}",
    ]
    for bundle in value["evidence_bundles"]:
        lines.extend(
            (
                f"module: {bundle['module_id']} {bundle['module_version']}",
                f"mode: {bundle['retrieval_mode']}",
                f"bundle_hash: {bundle['bundle_hash']}",
            )
        )
        for item in bundle["evidence_items"]:
            lines.append(
                f"- {item['document_id']} {item.get('provision_number') or ''}: "
                f"{item['official_title']}"
            )
            lines.append(f"  {item['bounded_excerpt']}")
        for failure in bundle["retrieval_failures"]:
            lines.append(f"! {failure['code']}: {failure['message']}")
    for failure in value["module_failures"]:
        lines.append(f"! {failure['module_id']} {failure['code']}: {failure['message']}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        _repository_root(args.repository_root)
        hub = KnowledgeHub1A(production_knowledge_module_registry())
        if args.list_modules:
            payload = {
                "authority_status": "NON_AUTHORITATIVE",
                "can_approve": False,
                "can_call_provider": False,
                "can_execute": False,
                "can_write": False,
                "modules": [descriptor.to_dict() for descriptor in hub.list_modules()],
                "status": "MODULES_LISTED",
            }
            print(_json(payload) if args.format == "json" else "\n".join(
                f"{item['module_id']} {item['module_version']} enabled_by_default=false"
                for item in payload["modules"]
            ))
            return 0

        required = {
            "module": args.modules,
            "question": args.question,
            "retrieval-mode": args.retrieval_mode,
            "module-repository": args.module_repository,
            "module-data-root": args.module_data_root,
            "expected-module-head": args.expected_module_head,
        }
        missing = sorted(name for name, value in required.items() if not value)
        if missing:
            raise KnowledgeModuleError(
                "INVALID_MODULE_CONFIGURATION", f"missing required options: {missing}"
            )
        selection = KnowledgeModuleSelection(module_ids=tuple(args.modules))
        query = KnowledgeModuleQuery(
            question=args.question,
            retrieval_mode={
                "source-discovery": "SOURCE_DISCOVERY",
                "verified-as-of": "VERIFIED_AS_OF",
            }[args.retrieval_mode],
            as_of_date=args.as_of,
            include_administrative_rules=args.include_administrative_rules,
            max_results=args.max_results,
            max_excerpt_characters=args.max_excerpt_characters,
            max_total_context_characters=args.max_total_context_characters,
        )
        configuration = production_german_law_configuration(
            module_repository_path=args.module_repository,
            corpus_data_root=args.module_data_root,
            expected_repository_head=args.expected_module_head,
        )
        configurations = {module_id: configuration for module_id in selection.module_ids}
        result = hub.query(selection, query, configurations)
        payload = result.to_dict()
        print(_json(payload) if args.format == "json" else _text_result(payload))
        return 0 if result.status != "KNOWLEDGE_MODULE_FAILURE" else 2
    except KnowledgeModuleError as exc:
        payload = {
            "authority_status": "NON_AUTHORITATIVE",
            "can_approve": False,
            "can_call_provider": False,
            "can_execute": False,
            "can_write": False,
            "reason": exc.reason,
            "status": exc.status,
        }
        print(_json(payload))
        return 2


def build_hub_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aoia-knowledge-hub",
        description="Generic provider-independent Knowledge Module control plane.",
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)

    def common(command: argparse.ArgumentParser) -> None:
        command.add_argument("--repository-root", required=True)
        command.add_argument("--format", choices=("json", "text"), default="json")

    list_modules = subparsers.add_parser("list-modules", allow_abbrev=False)
    common(list_modules)

    list_instances = subparsers.add_parser("list-instances", allow_abbrev=False)
    common(list_instances)
    list_instances.add_argument("--module")

    validate = subparsers.add_parser("validate-profile", allow_abbrev=False)
    common(validate)
    _profile_arguments(validate)

    query = subparsers.add_parser("query", allow_abbrev=False)
    common(query)
    _profile_arguments(query)
    query.add_argument("--question", required=True)
    query.add_argument("--module-repository", action="append", default=[])
    query.add_argument("--module-data-root", action="append", default=[])
    query.add_argument("--expected-module-head", action="append", default=[])
    return parser


def _profile_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--enable-module", action="append", default=[])
    parser.add_argument("--instance", action="append", default=[])
    parser.add_argument("--retrieval-mode", action="append", default=[])
    parser.add_argument("--as-of", action="append", default=[])
    parser.add_argument("--per-module-max-results", type=int, default=10)
    parser.add_argument("--per-module-max-context-characters", type=int, default=16_000)
    parser.add_argument("--global-max-modules", type=int, default=8)
    parser.add_argument("--global-max-results", type=int)
    parser.add_argument("--global-max-context-characters", type=int)


def _key_value_map(name: str, values: Sequence[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in values:
        if not isinstance(raw, str) or "=" not in raw:
            raise KnowledgeModuleError("PROFILE_INVALID", f"{name} requires module=value")
        key, value = raw.split("=", 1)
        if not key or not value or key in result:
            raise KnowledgeModuleError("PROFILE_INVALID", f"{name} contains an invalid or duplicate module")
        result[key] = value
    return result


def _request_profile(args: argparse.Namespace, hub: KnowledgeHub1B) -> KnowledgeProfile:
    modules = tuple(args.enable_module)
    if len(modules) != len(set(modules)):
        raise KnowledgeModuleError("PROFILE_INVALID", "duplicate module selection")
    instances = _key_value_map("instance", args.instance)
    modes = _key_value_map("retrieval-mode", args.retrieval_mode)
    as_of = _key_value_map("as-of", args.as_of)
    if set(instances) - set(modules) or set(modes) - set(modules) or set(as_of) - set(modules):
        raise KnowledgeModuleError("PROFILE_INVALID", "profile mapping refers to an unselected module")
    selections: list[KnowledgeProfileModuleSelection] = []
    for priority, module_id in enumerate(modules):
        hub.get_module_descriptor(module_id)
        instance_id = instances.get(module_id)
        if instance_id is None:
            candidates = hub.list_module_instances(module_id)
            if len(candidates) != 1:
                raise KnowledgeModuleError("PROFILE_INVALID", f"explicit instance is required: {module_id}")
            instance_id = candidates[0].instance_id
        mode = modes.get(module_id, "source-discovery")
        try:
            retrieval_mode = {
                "source-discovery": "SOURCE_DISCOVERY",
                "verified-as-of": "VERIFIED_AS_OF",
            }[mode]
        except KeyError as exc:
            raise KnowledgeModuleError("PROFILE_INVALID", f"invalid retrieval mode for {module_id}") from exc
        filters: list[tuple[str, object]] = []
        if module_id in as_of:
            filters.append(("as_of_date", as_of[module_id]))
        selections.append(
            KnowledgeProfileModuleSelection(
                schema_version=PROFILE_MODULE_SCHEMA_VERSION,
                module_id=module_id,
                instance_id=instance_id,
                enabled=True,
                priority=priority,
                per_module_max_results=args.per_module_max_results,
                per_module_max_context_characters=args.per_module_max_context_characters,
                retrieval_mode=retrieval_mode,
                module_specific_filters=tuple(filters),
            )
        )
    enabled_count = len(selections)
    global_results = args.global_max_results
    if global_results is None:
        global_results = max(10, enabled_count * args.per_module_max_results)
    global_context = args.global_max_context_characters
    if global_context is None:
        global_context = max(16_000, enabled_count * args.per_module_max_context_characters)
    return KnowledgeProfile(
        schema_version=PROFILE_SCHEMA_VERSION,
        profile_id="request-profile-1b",
        display_name="Request-only Knowledge Profile",
        selected_modules=tuple(selections),
        global_max_modules=args.global_max_modules,
        global_max_results=global_results,
        global_max_context_characters=global_context,
    )


def _hub_text(payload: dict[str, object]) -> str:
    lines = [f"status: {payload['status']}"]
    if "profile" in payload:
        lines.append(f"profile: {payload['profile']['profile_id']}")
    if "composite_bundle" in payload:
        bundle = payload["composite_bundle"]
        lines.append(f"modules: {', '.join(bundle['selected_module_ids'])}")
        lines.append(f"evidence_items: {bundle['total_evidence_items']}")
        lines.append(f"composite_bundle_hash: {bundle['composite_bundle_hash']}")
    return "\n".join(lines)


def hub_main(argv: Sequence[str] | None = None) -> int:
    parser = build_hub_parser()
    try:
        args = parser.parse_args(argv)
        _repository_root(args.repository_root)
        hub = KnowledgeHub1B(
            production_knowledge_module_registry(),
            DEFAULT_KNOWLEDGE_HUB_POLICY,
        )
        if args.operation == "list-modules":
            payload = {
                "authority_status": "NON_AUTHORITATIVE",
                "can_call_provider": False,
                "controls": [item.to_dict() for item in hub.control_model()],
                "status": "MODULES_LISTED",
            }
        elif args.operation == "list-instances":
            payload = {
                "authority_status": "NON_AUTHORITATIVE",
                "can_call_provider": False,
                "instances": [item.to_dict() for item in hub.list_module_instances(args.module)],
                "status": "INSTANCES_LISTED",
            }
        elif args.operation == "validate-profile":
            profile = _request_profile(args, hub)
            hub.validate_profile(profile)
            payload = {
                "authority_status": "NON_AUTHORITATIVE",
                "can_call_provider": False,
                "control_model": [item.to_dict() for item in hub.control_model(profile)],
                "profile": profile.to_dict(),
                "status": "PROFILE_VALID",
            }
        else:
            profile = _request_profile(args, hub)
            query = KnowledgeQuery(
                schema_version=KNOWLEDGE_QUERY_SCHEMA_VERSION,
                question=args.question,
            )
            repository_paths = _key_value_map("module-repository", args.module_repository)
            data_roots = _key_value_map("module-data-root", args.module_data_root)
            expected_heads = _key_value_map("expected-module-head", args.expected_module_head)
            configurations = {}
            for selection in profile.enabled_selections:
                if selection.module_id != GERMAN_LAW_MODULE_ID:
                    raise KnowledgeModuleError("MODULE_UNAVAILABLE", "production instance configuration is unavailable")
                required = (repository_paths, data_roots, expected_heads)
                if any(selection.module_id not in mapping for mapping in required):
                    raise KnowledgeModuleError(
                        "MODULE_UNAVAILABLE",
                        f"explicit instance configuration is incomplete: {selection.module_id}",
                    )
                configurations[selection.instance_id] = production_german_law_configuration(
                    module_repository_path=repository_paths[selection.module_id],
                    corpus_data_root=data_roots[selection.module_id],
                    expected_repository_head=expected_heads[selection.module_id],
                )
            result = hub.execute(profile, query, configurations)
            payload = result.to_dict()
        print(_json(payload) if args.format == "json" else _hub_text(payload))
        return 0 if payload["status"] not in ("KNOWLEDGE_MODULE_FAILURE",) else 2
    except KnowledgeModuleError as exc:
        payload = {
            "authority_status": "NON_AUTHORITATIVE",
            "can_approve": False,
            "can_call_provider": False,
            "can_execute": False,
            "can_write": False,
            "reason": exc.reason,
            "status": exc.status,
        }
        print(_json(payload))
        return 2


__all__ = ("build_hub_parser", "build_parser", "hub_main", "main")


if __name__ == "__main__":
    raise SystemExit(main())
