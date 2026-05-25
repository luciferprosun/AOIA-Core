from __future__ import annotations

from dataclasses import dataclass

from textual.widgets import Static


FORBIDDEN_TRANSCRIPT_MARKERS = (
    "[DEBUG] RAW MODEL OUTPUT",
    "SYSTEM PROMPT:",
    "RUNTIME STATE JSON:",
    "REQUEST JSON:",
    "PLANNER REQUEST JSON:",
    "raw_output",
    "prompt_preview",
    "reasoning_trace",
)


@dataclass(frozen=True)
class TranscriptEntry:
    role: str
    text: str


class TranscriptPanel(Static):
    """Operator-visible transcript panel.

    The transcript is intentionally bounded and sanitized. It displays CLI-visible
    runtime output only, not prompts, raw provider internals, or reasoning traces.
    """

    max_entries = 12
    max_chars_per_entry = 1800

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.entries: list[TranscriptEntry] = []

    def append_entry(self, role: str, text: str) -> None:
        clean = sanitize_transcript(text, self.max_chars_per_entry)
        if not clean:
            return
        self.entries.append(TranscriptEntry(role=role, text=clean))
        self.entries = self.entries[-self.max_entries :]
        self.update(self.render_entries())

    def clear_entries(self) -> None:
        self.entries.clear()
        self.update("Transcript cleared.")

    def render_entries(self) -> str:
        if not self.entries:
            return "No transcript yet."
        rows: list[str] = ["AOIA Operator Transcript"]
        for entry in self.entries:
            rows.append("")
            rows.append(f"[{entry.role}]")
            rows.append(entry.text)
        return "\n".join(rows)


def sanitize_transcript(text: str, max_chars: int = 1800) -> str:
    """Return a bounded operator-safe transcript string."""
    if not text:
        return ""

    safe_lines: list[str] = []
    skipping_debug_block = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if any(marker in line for marker in FORBIDDEN_TRANSCRIPT_MARKERS):
            skipping_debug_block = True
            safe_lines.append("[redacted runtime-internal output]")
            continue
        if skipping_debug_block:
            if not line.strip():
                skipping_debug_block = False
            continue
        safe_lines.append(line)

    clean = "\n".join(safe_lines).strip()
    if len(clean) > max_chars:
        return clean[: max_chars - 18].rstrip() + "\n[output truncated]"
    return clean
