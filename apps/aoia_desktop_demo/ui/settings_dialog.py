"""Settings dialog: provider/base URL/timeout/model + session-only API key."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import theme
from ..app import AppController
from ..providers.base import ProviderError


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent: tk.Widget, controller: AppController, on_saved) -> None:
        super().__init__(parent)
        self.controller = controller
        self._on_saved = on_saved
        self.title("Settings")
        self.configure(bg=theme.BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_widgets()
        self._load_from_settings()

    # --- layout ------------------------------------------------------------

    def _build_widgets(self) -> None:
        pad = {"padx": 10, "pady": 6}

        row = 0
        tk.Label(self, text="Provider", bg=theme.BG, fg=theme.TEXT_MUTED).grid(row=row, column=0, sticky="w", **pad)
        self.provider_var = tk.StringVar(value="openrouter")
        ttk.Combobox(self, textvariable=self.provider_var, values=["openrouter"], state="readonly", width=30).grid(
            row=row, column=1, sticky="w", **pad
        )

        row += 1
        tk.Label(self, text="API Base URL", bg=theme.BG, fg=theme.TEXT_MUTED).grid(row=row, column=0, sticky="w", **pad)
        self.base_url_var = tk.StringVar()
        tk.Entry(self, textvariable=self.base_url_var, width=42).grid(row=row, column=1, sticky="w", **pad)

        row += 1
        tk.Label(self, text="API Key", bg=theme.BG, fg=theme.TEXT_MUTED).grid(row=row, column=0, sticky="w", **pad)
        self.api_key_var = tk.StringVar()
        self._key_entry = tk.Entry(self, textvariable=self.api_key_var, width=42, show="*")
        self._key_entry.grid(row=row, column=1, sticky="w", **pad)

        row += 1
        self._show_key_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            self,
            text="Show key",
            variable=self._show_key_var,
            command=self._toggle_key_visibility,
            bg=theme.BG,
            fg=theme.TEXT,
            selectcolor=theme.PANEL,
            activebackground=theme.BG,
        ).grid(row=row, column=1, sticky="w", padx=10)

        row += 1
        tk.Label(self, text="App Title", bg=theme.BG, fg=theme.TEXT_MUTED).grid(row=row, column=0, sticky="w", **pad)
        self.app_title_var = tk.StringVar()
        tk.Entry(self, textvariable=self.app_title_var, width=42).grid(row=row, column=1, sticky="w", **pad)

        row += 1
        tk.Label(self, text="Request Timeout (s)", bg=theme.BG, fg=theme.TEXT_MUTED).grid(row=row, column=0, sticky="w", **pad)
        self.timeout_var = tk.StringVar()
        tk.Entry(self, textvariable=self.timeout_var, width=10).grid(row=row, column=1, sticky="w", **pad)

        row += 1
        tk.Label(self, text="Manual Model ID", bg=theme.BG, fg=theme.TEXT_MUTED).grid(row=row, column=0, sticky="w", **pad)
        self.manual_model_var = tk.StringVar()
        tk.Entry(self, textvariable=self.manual_model_var, width=42).grid(row=row, column=1, sticky="w", **pad)

        row += 1
        tk.Label(self, text="Max Response Tokens (optional)", bg=theme.BG, fg=theme.TEXT_MUTED).grid(
            row=row, column=0, sticky="w", **pad
        )
        self.max_tokens_var = tk.StringVar()
        tk.Entry(self, textvariable=self.max_tokens_var, width=10).grid(row=row, column=1, sticky="w", **pad)

        row += 1
        self.status_label = tk.Label(self, text="", bg=theme.BG, fg=theme.TEXT_MUTED, wraplength=420, justify="left")
        self.status_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(4, 0))

        row += 1
        button_bar = tk.Frame(self, bg=theme.BG)
        button_bar.grid(row=row, column=0, columnspan=2, pady=10)

        ttk.Button(button_bar, text="Test connection", command=self._on_test_connection).pack(side="left", padx=4)
        ttk.Button(button_bar, text="Use for this session", command=self._on_use_for_session).pack(side="left", padx=4)
        ttk.Button(button_bar, text="Clear key", command=self._on_clear_key).pack(side="left", padx=4)
        ttk.Button(button_bar, text="Save", command=self._on_save).pack(side="left", padx=4)
        ttk.Button(button_bar, text="Close", command=self.destroy).pack(side="left", padx=4)

    # --- behavior ------------------------------------------------------------

    def _toggle_key_visibility(self) -> None:
        self._key_entry.configure(show="" if self._show_key_var.get() else "*")

    def _load_from_settings(self) -> None:
        settings = self.controller.settings
        self.base_url_var.set(settings.api_base_url)
        self.app_title_var.set(settings.app_title)
        self.timeout_var.set(str(settings.timeout_seconds))
        self.manual_model_var.set(settings.manual_model_id)
        self.max_tokens_var.set(str(settings.max_response_tokens) if settings.max_response_tokens else "")
        if self.controller.secrets.api_key:
            self.api_key_var.set(self.controller.secrets.api_key)
            self._set_status(f"API key present (source: {self.controller.secrets.source}).", theme.TEXT_MUTED)
        else:
            self._set_status("No API key set. This field stays session-only unless a secure keyring is used.", theme.TEXT_MUTED)

    def _apply_non_secret_fields(self) -> None:
        settings = self.controller.settings
        settings.api_base_url = self.base_url_var.get().strip() or settings.api_base_url
        settings.app_title = self.app_title_var.get().strip() or settings.app_title
        try:
            settings.timeout_seconds = max(1.0, float(self.timeout_var.get().strip()))
        except ValueError:
            pass
        settings.manual_model_id = self.manual_model_var.get().strip()
        raw_max_tokens = self.max_tokens_var.get().strip()
        settings.max_response_tokens = int(raw_max_tokens) if raw_max_tokens.isdigit() else None

    def _on_use_for_session(self) -> None:
        key = self.api_key_var.get().strip()
        if not key:
            self._set_status("Enter a key first.", theme.WARN)
            return
        self.controller.secrets.set_for_session(key)
        self._set_status("API key set for this session (memory only, not written to disk).", theme.ACCENT)

    def _on_clear_key(self) -> None:
        self.controller.secrets.clear()
        self.api_key_var.set("")
        self._set_status("Session API key cleared.", theme.TEXT_MUTED)

    def _on_test_connection(self) -> None:
        self._on_use_for_session()
        self._set_status("Testing connection...", theme.TEXT_MUTED)
        self.update_idletasks()
        try:
            self.controller.test_connection()
            self._set_status("Connection OK.", theme.ACCENT)
        except ProviderError as error:
            self._set_status(f"Connection failed: {error}", theme.ERROR)

    def _on_save(self) -> None:
        self._apply_non_secret_fields()
        self.controller.save_current_settings()
        self._set_status("Non-secret settings saved. The API key is never written to disk by this action.", theme.ACCENT)
        if self._on_saved:
            self._on_saved()

    def _set_status(self, text: str, color: str) -> None:
        self.status_label.configure(text=text, fg=color)
