"""Deterministic raw text extraction for the RHCSA command library PDF."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from runtime.safety.subprocess_env import build_subprocess_env
from runtime.safety.bounded_subprocess import (
    SUBPROCESS_HARD_TIMEOUT_REASON_CODE,
    run_bounded_subprocess,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "knowledge" / "source" / "RHCSA_Command_Library.pdf"
DEFAULT_OUTPUT = PROJECT_ROOT / "knowledge" / "raw" / "rhcsa_raw.txt"
PDF_TOOL_HARD_TIMEOUT_SECONDS = 120


class PdfToolHardTimeoutError(RuntimeError):
    """A PDF utility exceeded its hard child-process deadline."""

    reason_code = SUBPROCESS_HARD_TIMEOUT_REASON_CODE

    def __init__(self, tool_name: str, timeout_seconds: int) -> None:
        self.tool_name = tool_name
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"{self.reason_code}: {tool_name} exceeded its hard execution timeout "
            "and was terminated"
        )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 1:
        print("ERROR: usage: python3 knowledge/tools/pdf_extract.py [input_pdf]")
        return 2

    input_path = Path(args[0]).resolve() if args else DEFAULT_INPUT
    output_path = DEFAULT_OUTPUT

    try:
        pages = extract_pdf(input_path, output_path)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    size = output_path.stat().st_size
    print("OK: RHCSA PDF raw extraction complete")
    print(f"extracted_pages={pages}")
    print(f"output_size_bytes={size}")
    print(f"output_path={output_path}")
    return 0


def extract_pdf(input_path: Path, output_path: Path) -> int:
    if not input_path.exists():
        raise RuntimeError(f"input PDF does not exist: {input_path}")
    if not input_path.is_file():
        raise RuntimeError(f"input path is not a file: {input_path}")
    if input_path.suffix.lower() != ".pdf":
        raise RuntimeError(f"input file is not a PDF: {input_path}")

    pdftotext = shutil.which("pdftotext")
    pdfinfo = shutil.which("pdfinfo")
    if not pdftotext:
        raise RuntimeError("required local tool not found: pdftotext")
    if not pdfinfo:
        raise RuntimeError("required local tool not found: pdfinfo")

    pages = read_page_count(pdfinfo, input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"input_path={input_path}")
    print(f"output_path={output_path}")
    print("extractor=pdftotext")

    try:
        result = run_bounded_subprocess(
            [pdftotext, "-layout", "-enc", "UTF-8", str(input_path), str(output_path)],
            check=False,
            env=build_subprocess_env(),
            timeout=PDF_TOOL_HARD_TIMEOUT_SECONDS,
            text=True,
            capture_output=True,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise PdfToolHardTimeoutError("pdftotext", PDF_TOOL_HARD_TIMEOUT_SECONDS) from exc
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "pdftotext failed"
        raise RuntimeError(message)

    if not output_path.exists():
        raise RuntimeError(f"output file was not created: {output_path}")
    if output_path.stat().st_size == 0:
        raise RuntimeError(f"output file is empty: {output_path}")

    return pages


def read_page_count(pdfinfo: str, input_path: Path) -> int:
    try:
        result = run_bounded_subprocess(
            [pdfinfo, str(input_path)],
            check=False,
            env=build_subprocess_env(),
            timeout=PDF_TOOL_HARD_TIMEOUT_SECONDS,
            text=True,
            capture_output=True,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise PdfToolHardTimeoutError("pdfinfo", PDF_TOOL_HARD_TIMEOUT_SECONDS) from exc
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "pdfinfo failed"
        raise RuntimeError(message)

    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            _, value = line.split(":", 1)
            try:
                return int(value.strip())
            except ValueError as exc:
                raise RuntimeError(f"invalid page count from pdfinfo: {value.strip()}") from exc

    raise RuntimeError("pdfinfo output did not include page count")


if __name__ == "__main__":
    raise SystemExit(main())
