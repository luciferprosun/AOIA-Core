from __future__ import annotations

from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Label, Static

from tui.widgets.approval_panel import ApprovalPanel
from tui.widgets.log_panel import LogPanel
from tui.widgets.status_panel import StatusPanel
from tui.widgets.status_bar import RuntimeStatusBar
from tui.widgets.transcript_panel import TranscriptPanel


class DashboardView(Vertical):
    """Minimal AOIA operator dashboard layout."""

    DEFAULT_CSS = """
    DashboardView {
        height: 100%;
    }

    #panels {
        height: 2fr;
    }

    #console {
        height: 2fr;
    }

    StatusPanel, LogPanel, TranscriptPanel, ApprovalPanel {
        width: 1fr;
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    RuntimeStatusBar {
        height: auto;
        border: solid $accent;
        padding: 0 1;
    }

    #commands {
        height: auto;
        border: solid $secondary;
        padding: 1;
    }
    """

    def compose(self):
        yield Header(show_clock=True)
        yield Horizontal(
            StatusPanel(id="status"),
            LogPanel(id="logs"),
            id="panels",
        )
        yield Horizontal(
            TranscriptPanel(id="transcript"),
            ApprovalPanel(id="approval"),
            id="console",
        )
        yield RuntimeStatusBar(id="runtime-status-bar")
        yield Static(
            "Commands: enter request or /model NAME, /clear, /status, /quit. Ctrl+A approve, Ctrl+X reject, Ctrl+P/N history, Ctrl+R refresh.",
            id="commands",
        )
        yield Input(placeholder="AOIA operator command or slash command", id="operator-input")
        yield Label("", id="notice")
        yield Footer()
