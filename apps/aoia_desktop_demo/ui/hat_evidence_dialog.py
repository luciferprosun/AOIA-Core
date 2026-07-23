"""Generic read-only preview of the immutable attachment used in a turn."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..knowledge.hats.canonical import verify_attachment
from ..knowledge.hats.contracts import HatAttachment
from . import theme

EVIDENCE_ONLY_MARKER = "EVIDENCE ONLY - NO AUTHORITY"
HUMAN_REVIEW_MARKER = "Final suggested answers still require human review."


def format_hat_evidence(attachment: HatAttachment) -> str:
    verify_attachment(attachment)
    bundle = attachment.bundle
    lines = [
        EVIDENCE_ONLY_MARKER,
        HUMAN_REVIEW_MARKER,
        "",
        f"Knowledge HAT: {attachment.descriptor.display_name}",
        f"Logical id: {attachment.descriptor.hat_id}",
        f"Library: {bundle.library_id} {bundle.library_version}",
        f"Manifest: {bundle.manifest_id}",
        f"Manifest digest: {bundle.manifest_digest}",
        f"Index: {bundle.index_id}",
        f"Index digest: {bundle.index_digest}",
        f"Bundle hash: {bundle.bundle_hash}",
        f"Attachment hash: {attachment.attachment_hash}",
        "",
    ]
    for passage in bundle.passages:
        lines.extend(
            (
                f"[{passage.rank}] {passage.source_title}",
                f"Source id: {passage.source_id}",
                f"Source locator: {passage.source_locator}",
                (
                    "Statutory references: "
                    + (", ".join(passage.statutory_references) or "not supplied")
                ),
                (
                    "Effective-date metadata: "
                    + (", ".join(passage.effective_dates) or "not supplied; currentness uncertain")
                ),
                f"Content digest: {passage.content_digest}",
                "Bounded excerpt:",
                passage.excerpt,
                "",
            )
        )
    return "\n".join(lines).rstrip() + "\n"


class HatEvidenceDialog(tk.Toplevel):
    """Opening this window performs formatting only; it never retrieves."""

    def __init__(
        self,
        parent: tk.Widget,
        attachment: HatAttachment,
        opener: tk.Widget,
    ) -> None:
        super().__init__(parent)
        self._opener = opener
        self.title("View HAT Evidence")
        self.configure(bg=theme.BG)
        self.geometry("840x660")
        self.minsize(680, 480)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Escape>", lambda _event: self._close())

        header = tk.Frame(self, bg=theme.PANEL)
        header.pack(fill="x")
        tk.Label(
            header,
            text=EVIDENCE_ONLY_MARKER,
            bg=theme.PANEL,
            fg=theme.WARN,
            font=theme.base_font(12, "bold"),
        ).pack(side="left", padx=14, pady=11)
        ttk.Button(header, text="Close", command=self._close).pack(
            side="right", padx=14, pady=8
        )

        text = tk.Text(
            self,
            bg=theme.BG,
            fg=theme.TEXT,
            wrap="word",
            relief="flat",
            padx=14,
            pady=12,
        )
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        text.pack(fill="both", expand=True)
        text.insert("1.0", format_hat_evidence(attachment))
        text.configure(state="disabled")
        self.after_idle(self.focus_set)

    def _close(self) -> None:
        self.destroy()
        try:
            self._opener.focus_set()
        except tk.TclError:
            pass
