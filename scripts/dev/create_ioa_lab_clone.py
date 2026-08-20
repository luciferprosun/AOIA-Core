#!/usr/bin/env python3
"""Create and inspect a local IOA lab hologram clone of AOIA-Core.

The lab clone is a disposable workspace for future model-assisted experiments.
This utility creates clone scaffolding only. It does not run model output,
start agents, store credentials, or modify AOIA-Core runtime behavior.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from runtime.safety.bounded_subprocess import run_bounded_subprocess
    from runtime.safety.subprocess_env import build_subprocess_env
except ModuleNotFoundError:
    repository_root = Path(__file__).resolve().parents[2]
    if str(repository_root) not in sys.path:
        sys.path.insert(0, str(repository_root))
    from runtime.safety.bounded_subprocess import run_bounded_subprocess
    from runtime.safety.subprocess_env import build_subprocess_env


PRODUCTION_REPO = Path("/home/l/Desktop/AOIA-Core")
LAB_ROOT = Path("/home/l/Desktop/IOA-LAB")
CLONE_TARGET = LAB_ROOT / "IOA-Lab-Klon-Main-Version"
PUSH_BLOCK_URL = "DISABLED_IOA_LAB_HOLOGRAM_NO_PRODUCTION_PUSH"
DEVELOPMENT_GIT_HARD_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class RepoState:
    exists: bool
    is_git_repo: bool
    branch: str
    head: str
    origin_url: str
    origin_push_url: str
    dirty: bool


def run_git(args: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run_bounded_subprocess(
        ["git", *args],
        cwd=cwd,
        check=check,
        env=build_subprocess_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=DEVELOPMENT_GIT_HARD_TIMEOUT_SECONDS,
        shell=False,
    )


def git_output(args: list[str], cwd: Path) -> str:
    result = run_git(args, cwd)
    return result.stdout.strip()


def optional_git_output(args: list[str], cwd: Path) -> str:
    result = run_git(args, cwd, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def inspect_repo(path: Path) -> RepoState:
    exists = path.exists()
    is_git_repo = exists and (path / ".git").exists()
    if not is_git_repo:
        return RepoState(
            exists=exists,
            is_git_repo=False,
            branch="",
            head="",
            origin_url="",
            origin_push_url="",
            dirty=False,
        )

    status = git_output(["status", "--short"], path)
    return RepoState(
        exists=True,
        is_git_repo=True,
        branch=optional_git_output(["branch", "--show-current"], path),
        head=optional_git_output(["rev-parse", "--short", "HEAD"], path),
        origin_url=optional_git_output(["remote", "get-url", "origin"], path),
        origin_push_url=optional_git_output(["remote", "get-url", "--push", "origin"], path),
        dirty=bool(status),
    )


def print_header() -> None:
    print("IOA Lab Clone / AOIA Hologram Workspace")
    print(f"Production repo: {PRODUCTION_REPO}")
    print(f"Lab root:        {LAB_ROOT}")
    print(f"Hologram clone:  {CLONE_TARGET}")
    print()
    print("Boundary: no model-output execution, no autonomous runner, no credentials, no production push.")
    print()


def print_repo_state(label: str, path: Path, state: RepoState) -> None:
    print(f"{label}: {path}")
    print(f"  exists: {yes_no(state.exists)}")
    print(f"  git repo: {yes_no(state.is_git_repo)}")
    if state.is_git_repo:
        print(f"  branch: {state.branch or '(detached or unknown)'}")
        print(f"  head: {state.head or '(unknown)'}")
        print(f"  dirty: {yes_no(state.dirty)}")
        print(f"  origin fetch URL: {state.origin_url or '(none)'}")
        print(f"  origin push URL: {state.origin_push_url or '(none)'}")


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def print_status() -> None:
    print_header()
    print_repo_state("Production", PRODUCTION_REPO, inspect_repo(PRODUCTION_REPO))
    print()
    print_repo_state("Hologram", CLONE_TARGET, inspect_repo(CLONE_TARGET))


def planned_actions(copy_current_repo: bool, disable_remote: bool) -> list[str]:
    actions = [f"Create lab root if missing: {LAB_ROOT}"]
    if copy_current_repo:
        actions.extend(
            [
                f"Create local no-hardlink Git clone from {PRODUCTION_REPO}",
                f"Clone target: {CLONE_TARGET}",
                "Set lab clone origin push URL to a disabled sentinel value",
            ]
        )
        if disable_remote:
            actions.append("Remove origin remote from the lab clone after cloning")
    else:
        actions.append("Do not copy AOIA-Core; create lab root only")
    return actions


def print_dry_run(copy_current_repo: bool, disable_remote: bool) -> None:
    print_header()
    print("Dry run only. No filesystem changes will be made.")
    print()
    for action in planned_actions(copy_current_repo, disable_remote):
        print(f"- {action}")


def ensure_production_repo() -> None:
    state = inspect_repo(PRODUCTION_REPO)
    if not state.is_git_repo:
        raise SystemExit(f"Production repo is not a Git repository: {PRODUCTION_REPO}")


def target_has_origin() -> bool:
    return bool(optional_git_output(["remote", "get-url", "origin"], CLONE_TARGET))


def ensure_target_available() -> bool:
    if not CLONE_TARGET.exists():
        return True
    if CLONE_TARGET.is_dir() and not any(CLONE_TARGET.iterdir()):
        return True
    if inspect_repo(CLONE_TARGET).is_git_repo:
        return False
    raise SystemExit(
        "Hologram target already exists and is not empty. "
        "Refusing to overwrite without destructive cleanup."
    )


def write_lab_readme() -> None:
    readme_path = LAB_ROOT / "README_IOA_LAB.md"
    if readme_path.exists():
        return
    readme_path.write_text(
        "\n".join(
            [
                "# IOA Lab",
                "",
                "Local disposable hologram workspace for AOIA-Core experiments.",
                "",
                f"- Production repo: `{PRODUCTION_REPO}`",
                f"- Hologram clone: `{CLONE_TARGET}`",
                "- Production AOIA-Core remains the source of truth.",
                "- Experiments should happen in the hologram clone only.",
                "- Do not store API credentials in this lab directory.",
                "- Do not execute model output automatically.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def init_lab(copy_current_repo: bool, disable_remote: bool) -> None:
    ensure_production_repo()
    LAB_ROOT.mkdir(parents=True, exist_ok=True)
    write_lab_readme()
    print(f"Lab root ready: {LAB_ROOT}")

    if not copy_current_repo:
        print("No clone requested. Use --copy-current-repo to create the hologram clone.")
        return

    should_clone = ensure_target_available()
    if should_clone:
        run_git(["clone", "--local", "--no-hardlinks", str(PRODUCTION_REPO), str(CLONE_TARGET)], PRODUCTION_REPO)
        run_git(["remote", "set-url", "--push", "origin", PUSH_BLOCK_URL], CLONE_TARGET)
        print(f"Hologram clone created: {CLONE_TARGET}")
        print(f"Origin push URL blocked: {PUSH_BLOCK_URL}")
    else:
        print(f"Hologram clone already exists: {CLONE_TARGET}")
        if target_has_origin():
            run_git(["remote", "set-url", "--push", "origin", PUSH_BLOCK_URL], CLONE_TARGET)
            print(f"Origin push URL blocked: {PUSH_BLOCK_URL}")

    if disable_remote and target_has_origin():
        run_git(["remote", "remove", "origin"], CLONE_TARGET)
        print("Origin remote removed from hologram clone.")

    print()
    print_repo_state("Hologram", CLONE_TARGET, inspect_repo(CLONE_TARGET))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or inspect the IOA lab hologram clone for AOIA-Core."
    )
    parser.add_argument("--status", action="store_true", help="Show production and hologram state.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without changes.")
    parser.add_argument("--init", action="store_true", help="Create the IOA lab root.")
    parser.add_argument(
        "--copy-current-repo",
        action="store_true",
        help="With --init, create the hologram clone from the current production repo.",
    )
    parser.add_argument(
        "--disable-remote",
        action="store_true",
        help="With --copy-current-repo, remove origin from the lab clone after cloning.",
    )
    return parser


def validate_args(args: argparse.Namespace) -> None:
    selected = [args.status, args.dry_run, args.init]
    if sum(1 for value in selected if value) != 1:
        raise SystemExit("Choose exactly one of --status, --dry-run, or --init.")
    if args.copy_current_repo and not (args.init or args.dry_run):
        raise SystemExit("--copy-current-repo requires --init or --dry-run.")
    if args.disable_remote and not args.copy_current_repo:
        raise SystemExit("--disable-remote requires --copy-current-repo.")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate_args(args)

    if args.status:
        print_status()
    elif args.dry_run:
        print_dry_run(args.copy_current_repo, args.disable_remote)
    elif args.init:
        init_lab(args.copy_current_repo, args.disable_remote)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
