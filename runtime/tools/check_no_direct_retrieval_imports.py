from __future__ import annotations

import argparse
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODULES = (
    "runtime/main.py",
    "runtime/commands/local_commands.py",
    "runtime/adaptive_routing/epistemic_kernel.py",
    "runtime/orchestrator/knowledge_router.py",
    "runtime/memory/rhcsa_context.py",
)
BANNED_PATTERNS = (
    "from tools.rhcsa_search",
    "import tools.rhcsa_search",
    "from knowledge.rhcsa_engine",
    "import knowledge.rhcsa_engine",
)


def scan(paths: tuple[str, ...] = DEFAULT_MODULES) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for relative_path in paths:
        path = PROJECT_ROOT / relative_path
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            violations.append((relative_path, "missing_file"))
            continue
        for pattern in BANNED_PATTERNS:
            if pattern in source:
                violations.append((relative_path, pattern))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Check coordinator modules for direct deprecated retrieval imports.")
    parser.add_argument("paths", nargs="*", help="Optional repo-relative Python files to scan.")
    args = parser.parse_args()
    targets = tuple(args.paths) if args.paths else DEFAULT_MODULES
    violations = scan(targets)
    if violations:
        for path, pattern in violations:
            print(f"{path}: {pattern}")
        return 1
    print("No direct deprecated retrieval imports found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
