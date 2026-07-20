"""Developer CLI for provider-independent knowledge context dry-runs."""

from __future__ import annotations

import argparse
from typing import Sequence

from runtime.knowledge_modules.cli import _json, _key_value_map, _repository_root
from runtime.knowledge_modules.contracts import KnowledgeModuleError
from runtime.knowledge_modules.german_law import (
    GERMAN_LAW_MODULE_ID,
    production_german_law_configuration,
    production_knowledge_module_registry,
)
from runtime.knowledge_modules.hub import KnowledgeHub1B
from runtime.knowledge_modules.planning import KNOWLEDGE_QUERY_SCHEMA_VERSION, KnowledgeQuery
from runtime.knowledge_modules.policy import DEFAULT_KNOWLEDGE_HUB_POLICY
from runtime.knowledge_modules.profiles import (
    PROFILE_MODULE_SCHEMA_VERSION,
    PROFILE_SCHEMA_VERSION,
    KnowledgeProfile,
    KnowledgeProfileModuleSelection,
)
from runtime.knowledge_modules.provider_bridge import KnowledgeProviderBridge1A
from runtime.knowledge_modules.provider_target import PROVIDER_TARGET_SCHEMA_VERSION, ProviderTarget


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aoia-knowledge-chat",
        description="Bind explicit request-only knowledge context to the existing provider runtime.",
        allow_abbrev=False,
    )
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--enable-module", action="append", default=[])
    parser.add_argument("--instance", action="append", default=[])
    parser.add_argument("--retrieval-mode", action="append", default=[])
    parser.add_argument("--as-of", action="append", default=[])
    parser.add_argument("--max-results", action="append", default=[])
    parser.add_argument("--max-context-characters", action="append", default=[])
    parser.add_argument("--include-administrative-rules", action="append", default=[])
    parser.add_argument("--module-repository", action="append", default=[])
    parser.add_argument("--module-data-root", action="append", default=[])
    parser.add_argument("--expected-module-head", action="append", default=[])
    parser.add_argument("--max-tokens", type=int, default=1_024)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--format", choices=("json", "text"), default="json")
    return parser


def _integer_map(name: str, values: Sequence[str], *, minimum: int, maximum: int) -> dict[str, int]:
    raw = _key_value_map(name, values)
    result: dict[str, int] = {}
    for module_id, value in raw.items():
        try:
            parsed = int(value, 10)
        except ValueError as exc:
            raise KnowledgeModuleError("PROFILE_INVALID", f"{name} requires module=integer") from exc
        if not minimum <= parsed <= maximum:
            raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", f"{name} is outside reviewed bounds")
        result[module_id] = parsed
    return result


def _profile(args: argparse.Namespace, hub: KnowledgeHub1B) -> KnowledgeProfile:
    modules = tuple(args.enable_module)
    if len(modules) != len(set(modules)):
        raise KnowledgeModuleError("PROFILE_INVALID", "duplicate module selection")
    instances = _key_value_map("instance", args.instance)
    modes = _key_value_map("retrieval-mode", args.retrieval_mode)
    as_of = _key_value_map("as-of", args.as_of)
    max_results = _integer_map("max-results", args.max_results, minimum=1, maximum=20)
    max_context = _integer_map(
        "max-context-characters",
        args.max_context_characters,
        minimum=1_024,
        maximum=32_000,
    )
    administrative = tuple(args.include_administrative_rules)
    if len(administrative) != len(set(administrative)):
        raise KnowledgeModuleError("PROFILE_INVALID", "administrative-rule selection contains duplicates")
    mapped_modules = set(instances) | set(modes) | set(as_of) | set(max_results) | set(max_context) | set(administrative)
    if mapped_modules - set(modules):
        raise KnowledgeModuleError("PROFILE_INVALID", "module option refers to an unselected module")

    selections: list[KnowledgeProfileModuleSelection] = []
    for priority, module_id in enumerate(modules):
        hub.get_module_descriptor(module_id)
        instance_id = instances.get(module_id)
        if instance_id is None:
            candidates = hub.list_module_instances(module_id)
            if len(candidates) != 1:
                raise KnowledgeModuleError("PROFILE_INVALID", f"explicit instance is required: {module_id}")
            instance_id = candidates[0].instance_id
        mode_value = modes.get(module_id, "source-discovery")
        try:
            retrieval_mode = {
                "source-discovery": "SOURCE_DISCOVERY",
                "verified-as-of": "VERIFIED_AS_OF",
            }[mode_value]
        except KeyError as exc:
            raise KnowledgeModuleError("PROFILE_INVALID", f"invalid retrieval mode for {module_id}") from exc
        filters: list[tuple[str, object]] = []
        if module_id in as_of:
            filters.append(("as_of_date", as_of[module_id]))
        if module_id in administrative:
            filters.append(("include_administrative_rules", True))
        selections.append(
            KnowledgeProfileModuleSelection(
                schema_version=PROFILE_MODULE_SCHEMA_VERSION,
                module_id=module_id,
                instance_id=instance_id,
                enabled=True,
                priority=priority,
                per_module_max_results=max_results.get(module_id, 8),
                per_module_max_context_characters=max_context.get(module_id, 16_000),
                retrieval_mode=retrieval_mode,
                module_specific_filters=tuple(filters),
            )
        )
    return KnowledgeProfile(
        schema_version=PROFILE_SCHEMA_VERSION,
        profile_id="knowledge-chat-request-1a",
        display_name="Request-only Knowledge Chat Profile",
        selected_modules=tuple(selections),
        global_max_modules=8,
        global_max_results=max(1, sum(item.per_module_max_results for item in selections)),
        global_max_context_characters=max(
            48_000,
            sum(item.per_module_max_context_characters for item in selections),
        ),
    )


def _configurations(args: argparse.Namespace, profile: KnowledgeProfile) -> dict[str, object]:
    repositories = _key_value_map("module-repository", args.module_repository)
    data_roots = _key_value_map("module-data-root", args.module_data_root)
    expected_heads = _key_value_map("expected-module-head", args.expected_module_head)
    selected_ids = {item.module_id for item in profile.enabled_selections}
    if (set(repositories) | set(data_roots) | set(expected_heads)) - selected_ids:
        raise KnowledgeModuleError("PROFILE_INVALID", "instance configuration refers to an unselected module")
    configurations: dict[str, object] = {}
    for selection in profile.enabled_selections:
        if selection.module_id != GERMAN_LAW_MODULE_ID:
            raise KnowledgeModuleError("MODULE_UNAVAILABLE", "production instance configuration is unavailable")
        if any(selection.module_id not in values for values in (repositories, data_roots, expected_heads)):
            raise KnowledgeModuleError(
                "MODULE_UNAVAILABLE",
                f"explicit instance configuration is incomplete: {selection.module_id}",
            )
        configurations[selection.instance_id] = production_german_law_configuration(
            module_repository_path=repositories[selection.module_id],
            corpus_data_root=data_roots[selection.module_id],
            expected_repository_head=expected_heads[selection.module_id],
        )
    return configurations


def _text(payload: dict[str, object]) -> str:
    lines = [
        f"provider_status: {payload['provider_status']}",
        f"knowledge_grounding_status: {payload['knowledge_grounding_status']}",
        f"selected_modules: {', '.join(payload['selected_module_ids'])}",
        f"context_package_hash: {payload['context_package_hash']}",
        f"authority_status: {payload['authority_status']}",
    ]
    for failure in payload["module_failures"]:
        lines.append(f"! {failure['module_id']} {failure['code']}: {failure['message']}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        _repository_root(args.repository_root)
        hub = KnowledgeHub1B(production_knowledge_module_registry(), DEFAULT_KNOWLEDGE_HUB_POLICY)
        profile = _profile(args, hub)
        query = KnowledgeQuery(
            schema_version=KNOWLEDGE_QUERY_SCHEMA_VERSION,
            question=args.question,
        )
        target = ProviderTarget(
            schema_version=PROVIDER_TARGET_SCHEMA_VERSION,
            provider_id=args.provider,
            model_id=args.model,
            dry_run=True,
            live_call_requested=False,
            live_call_acknowledged=False,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )
        result = KnowledgeProviderBridge1A(hub).execute(
            profile=profile,
            query=query,
            instance_configurations=_configurations(args, profile),
            provider_target=target,
        )
        payload = result.to_dict()
        print(_json(payload) if args.format == "json" else _text(payload))
        return 2 if result.provider_status == "RETRIEVAL_FAILED_CLOSED" else 0
    except (KnowledgeModuleError, ValueError) as exc:
        status = exc.status if isinstance(exc, KnowledgeModuleError) else "PROVIDER_TARGET_INVALID"
        reason = exc.reason if isinstance(exc, KnowledgeModuleError) else str(exc)
        print(_json({
            "authority_status": "NON_AUTHORITATIVE",
            "can_approve": False,
            "can_call_provider": False,
            "can_execute": False,
            "can_write": False,
            "reason": reason,
            "status": status,
        }))
        return 2


__all__ = ("build_parser", "main")


if __name__ == "__main__":
    raise SystemExit(main())
