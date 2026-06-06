#!/usr/bin/env python3
"""Terminal provider/model switcher for local AOIA-Core developer testing.

This utility never executes model output. It can optionally send one prompt to
one explicitly selected/current provider and prints the response as plain text.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = REPO_ROOT / "runtime"

for import_path in (str(REPO_ROOT), str(RUNTIME_ROOT)):
    if import_path not in sys.path:
        sys.path.insert(0, import_path)

from providers.config import DEFAULT_MODEL_PRESETS, ProviderManager, load_api_environment


KEY_NAMES = (
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "ANTHROPIC_API_KEY",
    "DEEPSEEK_API_KEY",
    "GROQ_API_KEY",
    "MISTRAL_API_KEY",
    "TOGETHER_API_KEY",
    "HUGGINGFACE_API_KEY",
    "XAI_API_KEY",
)

PROVIDER_KEYS = {
    "deepseek": ("DEEPSEEK_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "openrouter": ("OPENROUTER_API_KEY",),
    "xai": ("XAI_API_KEY",),
}


def present(value: str | None) -> str:
    return "present" if value else "missing"


def key_status_lines(keys: Iterable[str] = KEY_NAMES) -> list[str]:
    return [f"{key}: {present(os.environ.get(key))}" for key in keys]


def provider_key_status(provider_name: str) -> str:
    keys = PROVIDER_KEYS.get(provider_name, ())
    if not keys:
        return "unknown"
    return "present" if any(os.environ.get(key) for key in keys) else "missing"


def redact_known_secrets(text: str) -> str:
    redacted = text
    for key in KEY_NAMES:
        value = os.environ.get(key)
        if value and len(value) >= 6:
            redacted = redacted.replace(value, "<redacted>")
    return redacted


def print_key_status() -> None:
    print("API key presence:")
    for line in key_status_lines():
        print(f"  {line}")


def print_provider_status(manager: ProviderManager) -> None:
    print(f"Current model: {manager.current_model}")
    print("Provider chain:")
    for row in manager.provider_status():
        enabled = "yes" if row["enabled"] else "no"
        available = "yes" if row["available"] else "no"
        key_state = provider_key_status(str(row["name"]))
        print(
            f"  {row['name']:<12} model={row['model']:<32} "
            f"enabled={enabled:<3} key={key_state:<7} available={available}"
        )


def print_available_models(manager: ProviderManager) -> None:
    print("Model presets:")
    for alias, full_name in sorted(DEFAULT_MODEL_PRESETS.items()):
        normalized = manager.normalize_model_name(full_name)
        provider_name = normalized.split("/", 1)[0]
        marker = "available" if provider_key_status(provider_name) == "present" else "unavailable"
        notice = manager.model_notice(normalized)
        suffix = f" ({notice})" if notice else ""
        print(f"  {alias:<18} -> {normalized:<36} {marker}{suffix}")


def print_status(manager: ProviderManager) -> None:
    print_provider_status(manager)
    print()
    print_key_status()


def switch_model(manager: ProviderManager, model_name: str, *, dry_run: bool) -> None:
    normalized = manager.normalize_model_name(model_name)
    notice = manager.model_notice(normalized)
    if dry_run:
        print(f"Would switch model to: {normalized}")
    else:
        manager.switch_model(normalized)
        print(f"Switched model to: {normalized}")
    if notice:
        print(f"Notice: {notice}")


def print_api_warning() -> None:
    print("Warning: --prompt makes one live provider API call and may consume quota.", file=sys.stderr)
    print("Model output is printed as text only and is never executed.", file=sys.stderr)


def extract_gemini_text(payload: dict) -> str:
    parts: list[str] = []
    for candidate in payload.get("candidates", []):
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            text = part.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts).strip()


def generate_gemini_once(model: str, prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        raise FileNotFoundError("GEMINI_API_KEY or GOOGLE_API_KEY not found")

    model_path = urllib_parse.quote(model, safe="")
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    request = urllib_request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model_path}:generateContent",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(request, timeout=90) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"gemini HTTP {error.code}: {detail}") from error

    text = extract_gemini_text(payload)
    if not text:
        raise RuntimeError("Gemini response did not include text output.")
    return text


def generate_current_model_once(manager: ProviderManager, prompt: str) -> str:
    provider_name, model = manager.current_model.split("/", 1)
    if provider_name == "gemini":
        return generate_gemini_once(model, prompt)

    # Intentionally avoid ProviderManager.generate(), which uses fallback
    # routing. This CLI should not fan out across providers or spend quota
    # beyond the single current/selected provider.
    provider = manager._build_provider(manager.current_model)  # noqa: SLF001
    return provider.generate(prompt)


def run_prompt(manager: ProviderManager, prompt: str) -> int:
    print_api_warning()
    print(f"Calling current model once: {manager.current_model}")
    try:
        response = generate_current_model_once(manager, prompt)
    except Exception as error:  # noqa: BLE001 - developer CLI should show provider errors.
        print(f"Provider call failed: {redact_known_secrets(str(error))}", file=sys.stderr)
        return 1
    print(response)
    return 0


def choose_model(manager: ProviderManager) -> str | None:
    entries = sorted(DEFAULT_MODEL_PRESETS.items())
    print_available_models(manager)
    print()
    print("Choose a preset number, type a custom provider/model, or press Enter to cancel.")
    for index, (alias, full_name) in enumerate(entries, start=1):
        print(f"  {index}. {alias} -> {manager.normalize_model_name(full_name)}")
    choice = input("> ").strip()
    if not choice:
        return None
    if choice.isdigit():
        index = int(choice)
        if 1 <= index <= len(entries):
            return entries[index - 1][1]
        print("Invalid preset number.")
        return None
    return choice


def interactive_menu(manager: ProviderManager) -> int:
    while True:
        print()
        print("AOIA-Core Terminal Provider Switcher")
        print("1. Show status")
        print("2. List model presets")
        print("3. Switch model")
        print("q. Quit")
        choice = input("> ").strip().lower()

        if choice == "1":
            print_status(manager)
        elif choice == "2":
            print_available_models(manager)
        elif choice == "3":
            model_name = choose_model(manager)
            if model_name:
                switch_model(manager, model_name, dry_run=False)
        elif choice in {"q", "quit", "exit"}:
            return 0
        else:
            print("Unknown choice.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Terminal provider/model switcher for AOIA-Core local developer testing."
    )
    parser.add_argument("--status", action="store_true", help="Print current provider and key status.")
    parser.add_argument("--list", action="store_true", dest="list_models", help="List model presets.")
    parser.add_argument("--select", metavar="MODEL", help="Switch to a model alias or provider/model.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve --select without writing the model config.",
    )
    parser.add_argument(
        "--prompt",
        help=(
            "Send one prompt to the current or selected provider. "
            "This makes one API call and may consume quota."
        ),
    )
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.dry_run and not args.select:
        raise SystemExit("--dry-run requires --select.")
    if args.dry_run and args.prompt:
        raise SystemExit("--dry-run cannot be combined with --prompt.")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate_args(args)
    load_api_environment()
    manager = ProviderManager(REPO_ROOT)

    if args.status:
        print_status(manager)
    if args.list_models:
        print_available_models(manager)
    if args.select:
        switch_model(manager, args.select, dry_run=args.dry_run)
    if args.prompt:
        return run_prompt(manager, args.prompt)

    if not any((args.status, args.list_models, args.select, args.prompt)):
        if sys.stdin.isatty():
            return interactive_menu(manager)
        print_status(manager)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
