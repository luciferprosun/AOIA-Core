"""Bounded local developer CLI for explicit Knowledge Hub retrieval."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from runtime.knowledge_modules.contracts import KnowledgeModuleError
from runtime.knowledge_modules.german_law import (
    production_german_law_configuration,
    production_knowledge_module_registry,
)
from runtime.knowledge_modules.hub import KnowledgeHub1A
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


__all__ = ("build_parser", "main")


if __name__ == "__main__":
    raise SystemExit(main())
