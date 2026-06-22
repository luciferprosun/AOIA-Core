from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from runtime.providers.contracts import ProviderActivationStatus
from runtime.providers.selector import list_available_providers, run_selected_provider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AOIA controlled provider selector (dry-run by default; output is UNTRUSTED)."
    )
    parser.add_argument("--list", action="store_true", help="list runtime provider metadata")
    parser.add_argument("--provider", help="known provider identifier")
    parser.add_argument("--model", help="explicit model identifier")
    parser.add_argument("--prompt", help="explicit prompt text")
    parser.add_argument("--max-tokens", type=int, help="explicit output token cap")
    parser.add_argument("--live", action="store_true", help="request controlled live policy")
    parser.add_argument(
        "--acknowledge-live-provider-test",
        action="store_true",
        help="acknowledge a manual live provider test",
    )
    parser.add_argument(
        "--activate-manual-live-test",
        action="store_true",
        help="explicitly activate one manually requested live test",
    )
    parser.add_argument(
        "--created-at",
        default="cli-manual-run",
        help="caller-supplied audit timestamp or label",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list:
        print(json.dumps([item.to_dict() for item in list_available_providers()], sort_keys=True))
        return 0
    provider_id = args.provider or ""
    model_id = args.model or ""
    prompt = args.prompt or ""
    activation = (
        ProviderActivationStatus.LIVE_ALLOWED_FOR_MANUAL_TEST
        if args.activate_manual_live_test
        else ProviderActivationStatus.DRY_RUN_ONLY
    )
    try:
        result = run_selected_provider(
            provider_id=provider_id,
            model_id=model_id,
            prompt=prompt,
            max_tokens=args.max_tokens,
            live=args.live,
            acknowledge_live_provider_test=args.acknowledge_live_provider_test,
            activation_status=activation,
            selected_by="manual",
            created_at=args.created_at,
        )
    except ValueError as error:
        print(json.dumps({"status": "invalid", "error_message": str(error)}, sort_keys=True))
        return 2
    print(json.dumps(result.to_dict(), sort_keys=True))
    return 0 if result.status in {"dry_run_preview", "live_success"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
