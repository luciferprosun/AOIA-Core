"""Main desktop window for AOIA Control Chat — Competition Demo."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from . import theme
from .settings_dialog import SettingsDialog
from ..app import (
    STATUS_ACTIONS_DISABLED,
    STATUS_EVIDENCE_ONLY,
    STATUS_HUMAN_REQUIRED,
    STATUS_UNTRUSTED,
    SOURCES_LABEL,
    SUGGESTION_LABEL,
    AppController,
    SendResult,
)
from ..knowledge.registry import NONE_PROFILE_ID
from ..providers.base import ModelInfo, ProviderError

APP_TITLE = "AOIA Control Chat — Competition Demo"
DEFAULT_SIZE = (1100, 720)
MIN_SIZE = (850, 560)

OFFLINE_DEMO_RESPONSE = (
    "This is a deterministic, canned line shown only in Offline UI Demo mode. "
    "No model was contacted, and this text is not a real AI response."
)


class MainWindow(tk.Tk):
    def __init__(self, repo_root: Path) -> None:
        super().__init__()
        self.controller = AppController(repo_root)
        self._model_infos: list[ModelInfo] = []
        self._offline_demo = False

        self.title(APP_TITLE)
        self.configure(bg=theme.BG)
        width = self.controller.settings.window_width or DEFAULT_SIZE[0]
        height = self.controller.settings.window_height or DEFAULT_SIZE[1]
        self.geometry(f"{width}x{height}")
        self.minsize(*MIN_SIZE)

        self._build_layout()
        self._refresh_knowledge_dropdown()
        self._update_status_strip()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # --- layout construction ------------------------------------------------

    def _build_layout(self) -> None:
        self._build_top_bar()

        body = tk.Frame(self, bg=theme.BG)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_left_panel(body)
        self._build_main_area(body)

    def _build_top_bar(self) -> None:
        bar = tk.Frame(self, bg=theme.PANEL, height=44)
        bar.pack(fill="x", side="top")

        tk.Label(
            bar, text="AOIA Control Chat", bg=theme.PANEL, fg=theme.ACCENT,
            font=theme.base_font(theme.FONT_SIZE_HEADING, "bold"),
        ).pack(side="left", padx=12, pady=8)

        self.provider_label = tk.Label(bar, text="Provider: OpenRouter", bg=theme.PANEL, fg=theme.TEXT_MUTED)
        self.provider_label.pack(side="left", padx=8)

        self.model_label = tk.Label(bar, text="Model: (none selected)", bg=theme.PANEL, fg=theme.TEXT_MUTED)
        self.model_label.pack(side="left", padx=8)

        self.connection_label = tk.Label(bar, text="Connection: unknown", bg=theme.PANEL, fg=theme.TEXT_MUTED)
        self.connection_label.pack(side="left", padx=8)

        ttk.Button(bar, text="Settings", command=self._open_settings).pack(side="right", padx=12)

    def _build_left_panel(self, parent: tk.Widget) -> None:
        panel = tk.Frame(parent, bg=theme.PANEL, width=260)
        panel.grid(row=0, column=0, sticky="ns")
        panel.grid_propagate(False)

        pad = {"padx": 10, "pady": (10, 2)}

        tk.Label(panel, text="Model", bg=theme.PANEL, fg=theme.TEXT_MUTED).pack(anchor="w", **pad)
        self.model_var = tk.StringVar(value=self.controller.settings.selected_model_id)
        self.model_combo = ttk.Combobox(panel, textvariable=self.model_var, values=[], width=32)
        self.model_combo.pack(fill="x", padx=10)
        self.model_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_model_selected())

        ttk.Button(panel, text="Refresh Models", command=self._on_refresh_models).pack(fill="x", padx=10, pady=6)

        tk.Label(panel, text="Knowledge Profile", bg=theme.PANEL, fg=theme.TEXT_MUTED).pack(anchor="w", **pad)
        self.knowledge_var = tk.StringVar()
        self.knowledge_combo = ttk.Combobox(panel, textvariable=self.knowledge_var, values=[], state="readonly", width=32)
        self.knowledge_combo.pack(fill="x", padx=10)
        self.knowledge_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_knowledge_selected())

        self.knowledge_status_label = tk.Label(
            panel, text="Knowledge: None", bg=theme.PANEL, fg=theme.TEXT_MUTED, wraplength=230, justify="left"
        )
        self.knowledge_status_label.pack(anchor="w", padx=10, pady=(4, 10))

        ttk.Separator(panel, orient="horizontal").pack(fill="x", padx=10, pady=8)

        ttk.Button(panel, text="New Chat", command=self._on_new_chat).pack(fill="x", padx=10, pady=4)
        ttk.Button(panel, text="Clear Chat", command=self._on_clear_chat).pack(fill="x", padx=10, pady=4)

        self.offline_demo_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            panel, text="Offline UI Demo", variable=self.offline_demo_var, command=self._on_toggle_offline_demo,
            bg=theme.PANEL, fg=theme.TEXT, selectcolor=theme.PANEL_ALT, activebackground=theme.PANEL,
        ).pack(anchor="w", padx=10, pady=(12, 4))

    def _build_main_area(self, parent: tk.Widget) -> None:
        main = tk.Frame(parent, bg=theme.BG)
        main.grid(row=0, column=1, sticky="nsew")
        main.rowconfigure(1, weight=1)
        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=1)

        status_strip = tk.Frame(main, bg=theme.PANEL_ALT)
        status_strip.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.status_strip_label = tk.Label(
            status_strip,
            text="",
            bg=theme.PANEL_ALT,
            fg=theme.ACCENT_SECONDARY,
            font=theme.base_font(theme.FONT_SIZE_SMALL),
            justify="left",
            anchor="w",
        )
        self.status_strip_label.pack(fill="x", padx=10, pady=4)

        self.transcript = tk.Text(
            main, bg=theme.BG, fg=theme.TEXT, wrap="word", state="disabled",
            insertbackground=theme.TEXT, relief="flat", padx=10, pady=8,
        )
        self.transcript.grid(row=1, column=0, sticky="nsew")
        self.transcript.tag_configure("user", foreground=theme.ACCENT)
        self.transcript.tag_configure("assistant", foreground=theme.TEXT)
        self.transcript.tag_configure("error", foreground=theme.ERROR)
        self.transcript.tag_configure("label", foreground=theme.TEXT_MUTED, font=theme.base_font(theme.FONT_SIZE_SMALL))

        evidence_frame = tk.Frame(main, bg=theme.PANEL)
        evidence_frame.grid(row=1, column=1, sticky="nsew")
        tk.Label(evidence_frame, text="Evidence", bg=theme.PANEL, fg=theme.TEXT_MUTED).pack(anchor="w", padx=8, pady=6)
        self.evidence_text = tk.Text(
            evidence_frame, bg=theme.PANEL, fg=theme.TEXT_MUTED, wrap="word", state="disabled", relief="flat", padx=8,
        )
        self.evidence_text.pack(fill="both", expand=True, padx=4, pady=(0, 8))

        input_frame = tk.Frame(main, bg=theme.BG)
        input_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        input_frame.columnconfigure(0, weight=1)

        self.input_text = tk.Text(input_frame, height=3, bg=theme.PANEL, fg=theme.TEXT, insertbackground=theme.TEXT, wrap="word")
        self.input_text.grid(row=0, column=0, sticky="ew", padx=(10, 4), pady=8)
        self.input_text.bind("<Return>", self._on_enter_pressed)
        self.input_text.bind("<Shift-Return>", lambda _e: None)

        button_col = tk.Frame(input_frame, bg=theme.BG)
        button_col.grid(row=0, column=1, sticky="ns", padx=(0, 10))
        self.send_button = ttk.Button(button_col, text="Send", command=self._on_send)
        self.send_button.pack(fill="x", pady=(0, 4))
        self.cancel_button = ttk.Button(button_col, text="Cancel Request", command=self._on_cancel, state="disabled")
        self.cancel_button.pack(fill="x")

        status_row = tk.Frame(main, bg=theme.BG)
        status_row.grid(row=3, column=0, columnspan=2, sticky="ew")
        self.status_message_label = tk.Label(status_row, text="Ready.", bg=theme.BG, fg=theme.TEXT_MUTED)
        self.status_message_label.pack(side="left", padx=10, pady=(0, 8))
        self.context_size_label = tk.Label(status_row, text="", bg=theme.BG, fg=theme.TEXT_MUTED)
        self.context_size_label.pack(side="right", padx=10, pady=(0, 8))

    # --- status strip / labels ------------------------------------------------

    def _update_status_strip(self) -> None:
        self.status_strip_label.configure(
            text=f"{STATUS_UNTRUSTED}   |   {STATUS_EVIDENCE_ONLY}   |   {STATUS_ACTIONS_DISABLED}   |   {STATUS_HUMAN_REQUIRED}"
        )

    def _refresh_knowledge_dropdown(self) -> None:
        profiles = self.controller.knowledge_profiles
        display_values = [profile.display_name for profile in profiles]
        self.knowledge_combo.configure(values=display_values)
        current = self.controller.current_knowledge_profile()
        self.knowledge_var.set(current.display_name)
        self._update_knowledge_status_label(current.id)

    def _update_knowledge_status_label(self, profile_id: str) -> None:
        profile = self.controller.current_knowledge_profile() if profile_id is None else None
        profile = profile or next(
            (p for p in self.controller.knowledge_profiles if p.id == profile_id),
            self.controller.knowledge_profiles[0],
        )
        if profile.id == NONE_PROFILE_ID:
            self.knowledge_status_label.configure(text="Knowledge: None")
        else:
            count = profile.document_count if profile.document_count is not None else "unknown"
            self.knowledge_status_label.configure(
                text=f"Knowledge: {profile.display_name} ({count} records, evidence only)"
            )

    # --- event handlers ------------------------------------------------------

    def _open_settings(self) -> None:
        SettingsDialog(self, self.controller, on_saved=self._on_settings_saved)

    def _on_settings_saved(self) -> None:
        self.connection_label.configure(text="Connection: settings saved")

    def _on_refresh_models(self) -> None:
        self.status_message_label.configure(text="Refreshing model list...")
        self.update_idletasks()
        try:
            self._model_infos = self.controller.refresh_models()
        except ProviderError as error:
            self.status_message_label.configure(text=f"Model refresh failed: {error}", fg=theme.ERROR)
            return
        values = [f"{model.name} ({model.id})" for model in self._model_infos]
        self.model_combo.configure(values=values)
        self.status_message_label.configure(text=f"Loaded {len(self._model_infos)} models.", fg=theme.TEXT_MUTED)

    def _on_model_selected(self) -> None:
        raw = self.model_var.get()
        model_id = raw.split("(")[-1].rstrip(")") if "(" in raw else raw
        self.controller.settings.selected_model_id = model_id
        self.model_label.configure(text=f"Model: {model_id}")

    def _on_knowledge_selected(self) -> None:
        selected_name = self.knowledge_var.get()
        profile = next(
            (p for p in self.controller.knowledge_profiles if p.display_name == selected_name),
            self.controller.knowledge_profiles[0],
        )
        self.controller.set_knowledge_profile(profile.id)
        self._update_knowledge_status_label(profile.id)

    def _on_new_chat(self) -> None:
        self.controller.session.new_chat()
        self._render_transcript()
        self._set_evidence_text("")

    def _on_clear_chat(self) -> None:
        self._on_new_chat()

    def _on_toggle_offline_demo(self) -> None:
        self._offline_demo = self.offline_demo_var.get()
        if self._offline_demo:
            self.status_message_label.configure(text="Offline UI Demo — no model contacted", fg=theme.WARN)
        else:
            self.status_message_label.configure(text="Ready.", fg=theme.TEXT_MUTED)

    def _on_enter_pressed(self, _event) -> str:
        self._on_send()
        return "break"

    def _on_send(self) -> None:
        text = self.input_text.get("1.0", "end").strip()
        if not text:
            return
        if self.controller.session.has_active_request:
            return

        self.input_text.delete("1.0", "end")
        self._append_transcript_line("user", "You", text)
        self._set_busy(True)

        if self._offline_demo:
            self.controller.session.add_user_message(text)
            self.after(150, lambda: self._apply_offline_response())
            return

        # submit_message adds the user message to session state itself —
        # the line above only renders it into the transcript widget.
        request_id = self.controller.submit_message(
            text,
            on_done=self._on_send_result,
            on_scheduled_callback=lambda func: self.after(0, func),
        )
        if request_id is None:
            self._set_busy(False)

    def _apply_offline_response(self) -> None:
        self.controller.session.add_assistant_message(OFFLINE_DEMO_RESPONSE)
        self._append_transcript_line("assistant", "Assistant (offline demo)", OFFLINE_DEMO_RESPONSE)
        self._set_busy(False)

    def _on_send_result(self, result: SendResult) -> None:
        if not self.controller.session.is_current(result.request_id):
            # Canceled or superseded — ignore this late result entirely.
            return
        self.controller.session.end_request(result.request_id)
        self._set_busy(False)

        if result.error_message:
            self.controller.session.add_error_message(result.error_message)
            self._append_transcript_line("error", "Error", result.error_message)
            return

        chat_result = result.chat_result
        assert chat_result is not None
        self.controller.session.add_assistant_message(chat_result.content)
        footer = SUGGESTION_LABEL
        if result.evidence_count:
            footer += f"\n{SOURCES_LABEL}"
        self._append_transcript_line("assistant", "Assistant", chat_result.content, footer=footer)
        self._render_evidence_note(result.evidence_count)

    def _on_cancel(self) -> None:
        self.controller.cancel_active_request()
        self._set_busy(False)
        self.status_message_label.configure(text="Request canceled.", fg=theme.WARN)

    def _set_busy(self, busy: bool) -> None:
        self.send_button.configure(state="disabled" if busy else "normal")
        self.cancel_button.configure(state="normal" if busy else "disabled")
        if busy:
            self.status_message_label.configure(text="Waiting for provider response...", fg=theme.TEXT_MUTED)
        else:
            self.status_message_label.configure(text="Ready.", fg=theme.TEXT_MUTED)

    # --- transcript rendering ------------------------------------------------

    def _append_transcript_line(self, tag: str, speaker: str, text: str, footer: str | None = None) -> None:
        self.transcript.configure(state="normal")
        self.transcript.insert("end", f"{speaker}\n", "label")
        self.transcript.insert("end", f"{text}\n", tag)
        if footer:
            self.transcript.insert("end", f"{footer}\n", "label")
        self.transcript.insert("end", "\n")
        self.transcript.configure(state="disabled")
        self.transcript.see("end")
        self.context_size_label.configure(text=f"~{len(text)} chars in last message")

    def _render_transcript(self) -> None:
        self.transcript.configure(state="normal")
        self.transcript.delete("1.0", "end")
        self.transcript.configure(state="disabled")

    def _render_evidence_note(self, evidence_count: int) -> None:
        if evidence_count:
            self._set_evidence_text(f"{evidence_count} evidence item(s) attached to the last answer (non-authoritative).")
        else:
            self._set_evidence_text("No evidence attached to the last answer.")

    def _set_evidence_text(self, text: str) -> None:
        self.evidence_text.configure(state="normal")
        self.evidence_text.delete("1.0", "end")
        self.evidence_text.insert("1.0", text)
        self.evidence_text.configure(state="disabled")

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
