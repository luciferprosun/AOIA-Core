"""Premium, controlled desktop cockpit for the AOIA competition demo."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from . import theme
from .cockpit_state import CockpitState, configured_model_ids
from .settings_dialog import SettingsDialog
from ..app import (
    STATUS_ACTIONS_DISABLED,
    STATUS_EVIDENCE_ONLY,
    STATUS_HUMAN_REQUIRED,
    STATUS_UNTRUSTED,
    SOURCES_LABEL,
    SUGGESTION_LABEL,
    AppController,
    CriticalReviewCompletion,
    SendResult,
)
from ..critical_review import (
    ExecutionStatus,
    ObserverConfig,
    ObserverReviewResult,
    ReviewValidationError,
)
from ..knowledge.registry import NONE_PROFILE_ID
from ..providers.base import ModelInfo, ProviderError

APP_TITLE = "AOIA Control Chat — Competition Demo"
DEFAULT_SIZE = (1440, 900)
MIN_SIZE = (1280, 720)
TELEMETRY_STATUS = "SMART ROUTER TELEMETRY — NOT CONNECTED IN THIS DEMO"


class AlertWindow(tk.Toplevel):
    """A small, accessible blocking alert which never receives secrets."""

    def __init__(self, parent: tk.Widget, title: str, message: str, opener: tk.Widget) -> None:
        super().__init__(parent)
        self._opener = opener
        self.title(title)
        self.configure(bg=theme.PANEL)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        tk.Label(self, text=title, bg=theme.PANEL, fg=theme.WARN, font=theme.base_font(13, "bold")).pack(
            anchor="w", padx=20, pady=(18, 6)
        )
        tk.Label(self, text=message, bg=theme.PANEL, fg=theme.TEXT, justify="left", wraplength=430).pack(
            anchor="w", padx=20, pady=(0, 16)
        )
        button = ttk.Button(self, text="Dismiss", command=self._close)
        button.pack(anchor="e", padx=20, pady=(0, 18))
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Escape>", lambda _event: self._close())
        button.focus_set()

    def _close(self) -> None:
        self.destroy()
        if self._opener.winfo_exists():
            self._opener.focus_set()


class ObserverResultDialog(tk.Toplevel):
    """Plain-text, per-slot rendering of one immutable observer result."""

    def __init__(self, parent: tk.Widget, result: ObserverReviewResult, opener: tk.Widget) -> None:
        super().__init__(parent)
        self._opener = opener
        self.title(f"Critical Review — {result.slot_id}")
        self.configure(bg=theme.BG)
        self.geometry("760x620")
        self.minsize(620, 480)
        self.transient(parent)
        text = tk.Text(
            self,
            bg=theme.BG,
            fg=theme.TEXT,
            wrap="word",
            relief="flat",
            padx=16,
            pady=14,
            state="normal",
        )
        text.pack(fill="both", expand=True, padx=10, pady=(10, 4))
        text.insert("1.0", format_observer_result(result))
        text.configure(state="disabled")
        close_button = ttk.Button(self, text="Close", command=self._close)
        close_button.pack(anchor="e", padx=12, pady=(4, 12))
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Escape>", lambda _event: self._close())
        close_button.focus_set()

    def _close(self) -> None:
        self.destroy()
        if self._opener.winfo_exists():
            self._opener.focus_set()


def format_observer_result(result: ObserverReviewResult) -> str:
    lines = [
        f"Observer slot: {result.slot_id}",
        f"Role: {result.role}",
        f"Provider: {result.provider_id or '(none)'}",
        f"Model: {result.model_id or '(none)'}",
        f"Execution status: {result.execution_status.value}",
        f"Summary: {result.concise_summary}",
        "",
        "Findings:",
    ]
    if result.findings:
        for finding in result.findings:
            lines.append(f"- [{finding.severity}] {finding.category} — {finding.title}: {finding.detail}")
    else:
        lines.append("- None")
    lines.extend(("", "Uncertainty:"))
    lines.extend((f"- {item}" for item in result.uncertainty) if result.uncertainty else ("- None",))
    lines.extend(("", "Evidence conflicts:"))
    lines.extend(
        (f"- {item}" for item in result.evidence_conflicts) if result.evidence_conflicts else ("- None",)
    )
    if result.raw_untrusted_output is not None:
        lines.extend(("", "Bounded raw untrusted output:", result.raw_untrusted_output))
    lines.extend(
        (
            "",
            f"Snapshot hash: {result.snapshot_hash}",
            f"Observer configuration hash: {result.observer_configuration_hash}",
            f"Error category: {result.error_category or '(none)'}",
            "",
            "METADATA ONLY — NO AUTHORITY",
        )
    )
    return "\n".join(lines)


class MainWindow(tk.Tk):
    def __init__(self, repo_root: Path) -> None:
        super().__init__()
        self.controller = AppController(repo_root)
        self._model_infos: list[ModelInfo] = []
        self.cockpit = CockpitState(primary_model_id=self.controller.effective_model_id())

        self.title(APP_TITLE)
        self.configure(bg=theme.BG)
        width = max(MIN_SIZE[0], self.controller.settings.window_width or DEFAULT_SIZE[0])
        height = max(MIN_SIZE[1], self.controller.settings.window_height or DEFAULT_SIZE[1])
        self.geometry(f"{width}x{height}")
        self.minsize(*MIN_SIZE)
        self._configure_style()
        self._build_layout()
        self._refresh_knowledge_dropdown()
        self._render_connection_state()
        self._render_observers()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TButton", background=theme.PANEL_ALT, foreground=theme.TEXT, bordercolor=theme.BORDER, padding=(10, 6))
        style.map("TButton", background=[("active", "#263244"), ("disabled", theme.PANEL)])
        style.configure("TCombobox", fieldbackground=theme.PANEL_ALT, background=theme.PANEL_ALT, foreground=theme.TEXT)

    # --- layout -------------------------------------------------------------

    def _build_layout(self) -> None:
        self._build_header()
        self._build_notice_bar()
        self._build_observer_rail()
        self._build_conversation()
        self._build_composer()

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=theme.PANEL, height=58)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="AOIA", bg=theme.PANEL, fg=theme.ACCENT, font=theme.base_font(18, "bold")).pack(
            side="left", padx=(18, 8), pady=12
        )
        tk.Label(header, text="CONTROLLED DESKTOP DEMO", bg=theme.PANEL, fg=theme.ACCENT_SECONDARY,
                 font=theme.base_font(9, "bold")).pack(side="left", padx=(0, 22))
        self.provider_label = tk.Label(header, bg=theme.PANEL, fg=theme.TEXT_MUTED)
        self.provider_label.pack(side="left", padx=8)
        self.model_label = tk.Label(header, bg=theme.PANEL, fg=theme.TEXT_MUTED)
        self.model_label.pack(side="left", padx=8)
        self.connection_label = tk.Label(header, bg=theme.PANEL, fg=theme.TEXT_MUTED)
        self.connection_label.pack(side="left", padx=8)
        self.critical_loop_label = tk.Label(
            header, text="Critical loop: manual only", bg=theme.PANEL, fg=theme.TEXT_MUTED
        )
        self.critical_loop_label.pack(side="left", padx=8)
        ttk.Button(header, text="Settings", command=self._open_settings).pack(side="right", padx=18, pady=10)

    def _build_notice_bar(self) -> None:
        notices = tk.Frame(self, bg=theme.PANEL_ALT)
        notices.pack(fill="x", padx=14, pady=(10, 6))
        self.status_strip_label = tk.Label(
            notices,
            text=f"{STATUS_UNTRUSTED}  •  {STATUS_EVIDENCE_ONLY}  •  {STATUS_ACTIONS_DISABLED}  •  {STATUS_HUMAN_REQUIRED}",
            bg=theme.PANEL_ALT, fg=theme.ACCENT_SECONDARY, anchor="w", font=theme.base_font(9),
        )
        self.status_strip_label.pack(side="left", padx=12, pady=7)
        tk.Label(notices, text=TELEMETRY_STATUS, bg=theme.PANEL_ALT, fg=theme.TEXT_MUTED,
                 font=theme.base_font(9, "bold")).pack(side="right", padx=12, pady=7)

    def _build_observer_rail(self) -> None:
        section = tk.Frame(self, bg=theme.BG)
        section.pack(fill="x", padx=14, pady=(4, 8))
        title = tk.Frame(section, bg=theme.BG)
        title.pack(fill="x")
        tk.Label(title, text="CRITICAL PROMPT LOOP", bg=theme.BG, fg=theme.TEXT, font=theme.base_font(12, "bold")).pack(
            side="left"
        )
        self.review_button = ttk.Button(title, text="Run Critical Review", command=self._run_critical_review)
        self.review_button.pack(side="right")
        self.observer_rail = tk.Frame(section, bg=theme.BG)
        self.observer_rail.pack(fill="x", pady=(6, 0))
        for column in range(3):
            self.observer_rail.columnconfigure(column, weight=1, uniform="observer")
        self.observer_cards: list[dict[str, tk.Widget]] = []
        for index in range(3):
            card = tk.Frame(self.observer_rail, bg=theme.PANEL, highlightbackground=theme.BORDER, highlightthickness=1)
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 5, 0 if index == 2 else 5))
            role = tk.Label(card, bg=theme.PANEL, fg=theme.ACCENT, font=theme.base_font(11, "bold"), anchor="w")
            role.pack(fill="x", padx=12, pady=(10, 2))
            state = tk.Label(card, bg=theme.PANEL, fg=theme.TEXT_MUTED, anchor="w")
            state.pack(fill="x", padx=12)
            route = tk.Label(card, bg=theme.PANEL, fg=theme.TEXT, anchor="w", wraplength=350, justify="left")
            route.pack(fill="x", padx=12, pady=(5, 3))
            result = tk.Label(card, bg=theme.PANEL, fg=theme.TEXT_MUTED, anchor="w", justify="left", wraplength=350)
            result.pack(fill="x", padx=12, pady=(0, 5))
            details = ttk.Button(
                card,
                text="View full result",
                state="disabled",
                command=lambda slot_index=index: self._show_observer_result(slot_index),
            )
            details.pack(anchor="w", padx=12, pady=(0, 10))
            self.observer_cards.append(
                {"role": role, "state": state, "route": route, "result": result, "details": details}
            )

    def _build_conversation(self) -> None:
        conversation = tk.Frame(self, bg=theme.PANEL, highlightbackground=theme.BORDER, highlightthickness=1)
        conversation.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        top = tk.Frame(conversation, bg=theme.PANEL)
        top.pack(fill="x")
        tk.Label(top, text="CONVERSATION", bg=theme.PANEL, fg=theme.TEXT, font=theme.base_font(11, "bold")).pack(
            side="left", padx=12, pady=8
        )
        self.knowledge_var = tk.StringVar()
        self.knowledge_combo = ttk.Combobox(top, textvariable=self.knowledge_var, state="readonly", width=34)
        self.knowledge_combo.pack(side="right", padx=12, pady=7)
        self.knowledge_combo.bind("<<ComboboxSelected>>", lambda _event: self._on_knowledge_selected())
        self.transcript = tk.Text(
            conversation, bg=theme.BG, fg=theme.TEXT, wrap="word", state="disabled", relief="flat", padx=14, pady=10,
            insertbackground=theme.TEXT,
        )
        self.transcript.pack(fill="both", expand=True, padx=1, pady=(0, 1))
        self.transcript.tag_configure("user", foreground=theme.ACCENT)
        self.transcript.tag_configure("assistant", foreground=theme.TEXT)
        self.transcript.tag_configure("error", foreground=theme.ERROR)
        self.transcript.tag_configure("label", foreground=theme.TEXT_MUTED, font=theme.base_font(9))

    def _build_composer(self) -> None:
        composer = tk.Frame(self, bg=theme.PANEL, highlightbackground=theme.BORDER, highlightthickness=1)
        composer.pack(fill="x", padx=14, pady=(0, 14))
        composer.columnconfigure(0, weight=1)
        self.input_text = tk.Text(composer, height=3, bg=theme.PANEL_ALT, fg=theme.TEXT, insertbackground=theme.TEXT, wrap="word",
                                  relief="flat", padx=10, pady=8)
        self.input_text.grid(row=0, column=0, rowspan=2, sticky="ew", padx=(10, 6), pady=10)
        self.input_text.bind("<Return>", self._on_enter_pressed)
        tk.Label(composer, text="Enter to send • Shift+Enter for a line break", bg=theme.PANEL, fg=theme.TEXT_MUTED).grid(
            row=2, column=0, sticky="w", padx=10, pady=(0, 8)
        )
        self.send_button = ttk.Button(composer, text="Send", command=self._on_send)
        self.send_button.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(10, 3))
        self.cancel_button = ttk.Button(composer, text="Cancel", command=self._on_cancel, state="disabled")
        self.cancel_button.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(3, 10))
        self.status_message_label = tk.Label(composer, text="Ready for operator input.", bg=theme.PANEL, fg=theme.TEXT_MUTED)
        self.status_message_label.grid(row=2, column=1, sticky="e", padx=10, pady=(0, 8))

    # --- state and settings -------------------------------------------------

    def _available_models_by_provider(self) -> dict[str, tuple[str, ...]]:
        if not self.controller.settings.has_configured_provider_connection():
            return {}
        return configured_model_ids(
            provider_id=self.controller.settings.provider,
            saved_model_id=self.controller.effective_model_id(),
            fetched_model_ids=(model.id for model in self._model_infos),
        )

    def _open_settings(self) -> None:
        SettingsDialog(
            self,
            self.controller,
            self.cockpit,
            self._available_models_by_provider,
            on_saved=self._on_settings_saved,
            on_refresh_models=self._refresh_models,
        )

    def _on_settings_saved(self) -> None:
        self.cockpit.set_primary_model(self.controller.effective_model_id())
        self._render_connection_state()
        self._render_observers()

    def _render_connection_state(self) -> None:
        provider = self.controller.settings.provider or "(not configured)"
        model_id = self.controller.effective_model_id() or "(no primary model)"
        self.provider_label.configure(text=f"Provider: {provider}")
        self.model_label.configure(text=f"Primary model: {model_id}")
        if self.controller.provider_route_is_eligible():
            self.connection_label.configure(text="Connection: eligible for manual use", fg=theme.ACCENT)
        elif self.controller.settings.has_configured_provider_connection():
            self.connection_label.configure(text="Connection: API key required", fg=theme.WARN)
        else:
            self.connection_label.configure(text="Connection: not configured", fg=theme.WARN)

    def _refresh_models(self) -> None:
        self.status_message_label.configure(text="Refreshing explicit provider model catalog…", fg=theme.TEXT_MUTED)
        self.update_idletasks()
        try:
            self._model_infos = self.controller.refresh_models()
        except ProviderError as error:
            self.status_message_label.configure(text="Model catalog refresh failed.", fg=theme.ERROR)
            self._show_alert("Provider request failed", f"The model catalog could not be refreshed. {error}", self.review_button)
            return
        self.status_message_label.configure(text=f"Loaded {len(self._model_infos)} configured-provider models.", fg=theme.TEXT_MUTED)
        self._render_observers()

    # --- knowledge ----------------------------------------------------------

    def _refresh_knowledge_dropdown(self) -> None:
        profiles = self.controller.knowledge_profiles
        self.knowledge_combo.configure(values=[profile.display_name for profile in profiles])
        self.knowledge_var.set(self.controller.current_knowledge_profile().display_name)

    def _on_knowledge_selected(self) -> None:
        profile = next(
            (item for item in self.controller.knowledge_profiles if item.display_name == self.knowledge_var.get()),
            self.controller.knowledge_profiles[0],
        )
        self.controller.set_knowledge_profile(profile.id)
        suffix = "no local evidence selected" if profile.id == NONE_PROFILE_ID else f"{profile.document_count or 0} local records; evidence only"
        self.status_message_label.configure(text=f"Knowledge profile: {profile.display_name} — {suffix}", fg=theme.TEXT_MUTED)

    # --- critical prompt loop ------------------------------------------------

    def _render_observers(self) -> None:
        for index, (slot, widgets) in enumerate(
            zip(self.cockpit.observer_slots, self.observer_cards, strict=True), start=1
        ):
            review_result = slot.review_result
            if review_result is None:
                enabled = "ENABLED" if slot.enabled else "DISABLED"
                widgets["role"].configure(text=f"OBSERVER {index} — {slot.role}")
                widgets["state"].configure(
                    text=f"{enabled} • {slot.state}",
                    fg=theme.ACCENT if slot.enabled else theme.TEXT_MUTED,
                )
                route = f"Provider: {slot.provider_id or 'not selected'}\nModel: {slot.model_id or 'not selected'}"
                widgets["route"].configure(text=route)
                widgets["result"].configure(text=f"{slot.result}\nMETADATA ONLY • NO AUTHORITY")
                widgets["details"].configure(state="disabled")
                continue

            status_color = theme.ACCENT if review_result.execution_status is ExecutionStatus.COMPLETED else theme.WARN
            if review_result.execution_status is ExecutionStatus.DISABLED:
                status_color = theme.TEXT_MUTED
            widgets["role"].configure(text=f"OBSERVER {index} — {review_result.role}")
            widgets["state"].configure(text=review_result.execution_status.value, fg=status_color)
            widgets["route"].configure(
                text=(
                    f"Provider: {review_result.provider_id or 'not selected'}\n"
                    f"Model: {review_result.model_id or 'not selected'}"
                )
            )
            stale_note = ""
            current_hash = self._current_primary_snapshot_hash()
            if current_hash != review_result.snapshot_hash:
                stale_note = "\nEarlier captured primary snapshot"
            widgets["result"].configure(
                text=(
                    f"{review_result.concise_summary}\n"
                    f"Trace: {review_result.snapshot_hash[:12]}{stale_note}\n"
                    "METADATA ONLY • NO AUTHORITY"
                )
            )
            widgets["details"].configure(state="normal")

    def _run_critical_review(self) -> None:
        if self.controller.critical_review_active:
            self.status_message_label.configure(text="Critical review is already running.", fg=theme.WARN)
            return
        try:
            snapshot = self.controller.capture_review_snapshot()
        except ReviewValidationError:
            self._show_alert(
                "Critical review unavailable",
                "UNAVAILABLE — PRIMARY SNAPSHOT FAILED CLOSED VALIDATION",
                self.review_button,
            )
            self.status_message_label.configure(text="Critical review snapshot validation failed closed.", fg=theme.WARN)
            return
        if snapshot is None:
            message = "UNAVAILABLE — NO COMPLETED PRIMARY RESPONSE"
            self._show_alert("Critical review unavailable", message, self.review_button)
            self.status_message_label.configure(text=message, fg=theme.WARN)
            return

        try:
            configs = tuple(
                ObserverConfig(
                    slot_id=f"observer-{index}",
                    enabled=slot.enabled,
                    role_id=slot.role,
                    provider_connection_id=slot.provider_id,
                    model_id=slot.model_id,
                )
                for index, slot in enumerate(self.cockpit.observer_slots, start=1)
            )
        except ReviewValidationError:
            self._show_alert(
                "Critical review unavailable",
                "Observer configuration failed closed validation.",
                self.review_button,
            )
            self.status_message_label.configure(text="Observer configuration failed closed validation.", fg=theme.WARN)
            return
        for slot in self.cockpit.observer_slots:
            slot.review_result = None
            if slot.enabled:
                slot.state = "PENDING"
                slot.result = "Waiting for one bounded observer response."
            else:
                slot.state = "Disabled"
                slot.result = "Observer disabled; no provider call will be made."
        self._render_observers()
        self.review_button.configure(state="disabled")
        self.critical_loop_label.configure(text="Critical loop: running", fg=theme.ACCENT)
        self.status_message_label.configure(text="Running bounded independent observer review…", fg=theme.TEXT_MUTED)
        started = self.controller.submit_critical_review(
            snapshot,
            configs,
            on_done=self._on_critical_review_done,
            on_scheduled_callback=lambda func: self.after(0, func),
        )
        if not started:
            self.review_button.configure(state="normal")
            self.critical_loop_label.configure(text="Critical loop: blocked", fg=theme.WARN)
            self.status_message_label.configure(text="Critical review did not start.", fg=theme.WARN)

    def _on_critical_review_done(self, completion: CriticalReviewCompletion) -> None:
        self.review_button.configure(state="normal")
        if completion.error_category is not None:
            self.critical_loop_label.configure(text="Critical loop: failed closed", fg=theme.WARN)
            self.status_message_label.configure(text="Critical review failed closed before observer calls.", fg=theme.WARN)
            self._show_alert(
                "Critical review failed",
                f"Local error category: {completion.error_category}",
                self.review_button,
            )
            return
        self.cockpit.apply_review_results(completion.results)
        self._render_observers()
        self.critical_loop_label.configure(text="Critical loop: complete", fg=theme.ACCENT)
        self.status_message_label.configure(
            text="Bounded review finished. Results are metadata only and have no authority.",
            fg=theme.TEXT_MUTED,
        )

    def _current_primary_snapshot_hash(self) -> str | None:
        try:
            snapshot = self.controller.capture_review_snapshot()
        except ReviewValidationError:
            return None
        return snapshot.snapshot_hash if snapshot is not None else None

    def _show_observer_result(self, slot_index: int) -> None:
        slot = self.cockpit.observer_slots[slot_index]
        if slot.review_result is None:
            return
        opener = self.observer_cards[slot_index]["details"]
        ObserverResultDialog(self, slot.review_result, opener)

    # --- chat ---------------------------------------------------------------

    def _on_enter_pressed(self, event) -> str | None:
        if event.state & 0x0001:  # Shift+Enter retains the Text widget's newline behavior.
            return None
        self._on_send()
        return "break"

    def _route_block_reason(self) -> str | None:
        settings = self.controller.settings
        if not settings.provider:
            return "No provider configured. Open Settings → Provider Connections and save OpenRouter."
        if settings.api_base_url.rstrip("/") != "https://openrouter.ai/api/v1":
            return "Invalid Base URL. Enter https://openrouter.ai/api/v1 in Settings → Provider Connections."
        if not self.controller.effective_model_id():
            return "No primary model selected. Choose a valid configured-provider model in Settings → Primary Model."
        if not self.controller.secrets.api_key:
            return "Missing API key. Enter it manually in Settings for this session; it remains masked and is not saved."
        return None

    def _on_send(self) -> None:
        text = self.input_text.get("1.0", "end").strip()
        if not text or self.controller.session.has_active_request:
            return
        reason = self._route_block_reason()
        if reason:
            self.status_message_label.configure(text="Provider request blocked.", fg=theme.WARN)
            self._show_alert("Provider request blocked", reason, self.send_button)
            return
        self.input_text.delete("1.0", "end")
        self._append_transcript_line("user", "You", text)
        self._set_busy(True)
        request_id = self.controller.submit_message(text, on_done=self._on_send_result, on_scheduled_callback=lambda func: self.after(0, func))
        if request_id is None:
            self._set_busy(False)

    def _on_send_result(self, result: SendResult) -> None:
        if not self.controller.session.is_current(result.request_id):
            return
        self.controller.session.end_request(result.request_id)
        self._set_busy(False)
        if result.error_message:
            self.controller.session.add_error_message(result.error_message)
            self._append_transcript_line("error", "Provider request failed", result.error_message)
            self._show_alert("Provider request failed", result.error_message, self.send_button)
            return
        chat_result = result.chat_result
        assert chat_result is not None
        self.controller.accept_completed_primary_turn(result)
        self.controller.session.add_assistant_message(chat_result.content)
        footer = SUGGESTION_LABEL + (f"\n{SOURCES_LABEL}" if result.evidence_count else "")
        self._append_transcript_line("assistant", "Assistant", chat_result.content, footer=footer)

    def _on_cancel(self) -> None:
        self.controller.cancel_active_request()
        self._set_busy(False)
        self.status_message_label.configure(text="Request canceled by operator.", fg=theme.WARN)

    def _set_busy(self, busy: bool) -> None:
        self.send_button.configure(state="disabled" if busy else "normal")
        self.cancel_button.configure(state="normal" if busy else "disabled")
        if busy:
            self.status_message_label.configure(text="Sending one controlled provider request…", fg=theme.TEXT_MUTED)
        else:
            self.status_message_label.configure(text="Ready for operator input.", fg=theme.TEXT_MUTED)

    def _append_transcript_line(self, tag: str, speaker: str, text: str, footer: str | None = None) -> None:
        self.transcript.configure(state="normal")
        self.transcript.insert("end", f"{speaker}\n", "label")
        self.transcript.insert("end", f"{text}\n", tag)
        if footer:
            self.transcript.insert("end", f"{footer}\n", "label")
        self.transcript.insert("end", "\n")
        self.transcript.configure(state="disabled")
        self.transcript.see("end")

    def _render_transcript(self) -> None:
        self.transcript.configure(state="normal")
        self.transcript.delete("1.0", "end")
        self.transcript.configure(state="disabled")

    def _show_alert(self, title: str, message: str, opener: tk.Widget) -> None:
        AlertWindow(self, title, message, opener)

    def _on_close(self) -> None:
        self.controller.settings.window_width = self.winfo_width()
        self.controller.settings.window_height = self.winfo_height()
        self.controller.save_current_settings()
        self.controller.shutdown()
        self.destroy()


def run_app(repo_root: Path | None = None) -> None:
    resolved_root = repo_root or Path(__file__).resolve().parents[2]
    window = MainWindow(resolved_root)
    window.mainloop()
