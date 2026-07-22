"""Accessible settings dialog for the premium controlled desktop cockpit."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from . import theme
from .cockpit_state import CockpitState
from ..app import AppController
from ..providers.base import ProviderError

API_KEY_ENTRY_MASK = "*"


class SettingsDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Widget,
        controller: AppController,
        cockpit: CockpitState,
        model_supplier: Callable[[], dict[str, tuple[str, ...]]],
        on_saved: Callable[[], None],
        on_refresh_models: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.cockpit = cockpit
        self._model_supplier = model_supplier
        self._on_saved = on_saved
        self._on_refresh_models = on_refresh_models
        self.title("AOIA Settings")
        self.configure(bg=theme.BG)
        self.geometry("760x640")
        self.minsize(680, 540)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Escape>", lambda _event: self._close())
        self._build_widgets()
        self._load_from_settings()

    def _build_widgets(self) -> None:
        header = tk.Frame(self, bg=theme.PANEL)
        header.pack(fill="x")
        tk.Label(header, text="SETTINGS", bg=theme.PANEL, fg=theme.ACCENT, font=theme.base_font(14, "bold")).pack(
            side="left", padx=16, pady=12
        )
        tk.Label(header, text="Operator-controlled configuration", bg=theme.PANEL, fg=theme.TEXT_MUTED).pack(
            side="left", padx=4
        )
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)
        self.connections_tab = tk.Frame(notebook, bg=theme.BG)
        self.primary_tab = tk.Frame(notebook, bg=theme.BG)
        self.loop_tab = tk.Frame(notebook, bg=theme.BG)
        self.telemetry_tab = tk.Frame(notebook, bg=theme.BG)
        self.safety_tab = tk.Frame(notebook, bg=theme.BG)
        notebook.add(self.connections_tab, text="Provider Connections")
        notebook.add(self.primary_tab, text="Primary Model")
        notebook.add(self.loop_tab, text="Critical Prompt Loop")
        notebook.add(self.telemetry_tab, text="Telemetry")
        notebook.add(self.safety_tab, text="Session / Safety")
        self._build_connections_tab()
        self._build_primary_tab()
        self._build_loop_tab()
        self._build_telemetry_tab()
        self._build_safety_tab()
        footer = tk.Frame(self, bg=theme.PANEL)
        footer.pack(fill="x")
        self.status_label = tk.Label(footer, text="", bg=theme.PANEL, fg=theme.TEXT_MUTED, anchor="w")
        self.status_label.pack(side="left", fill="x", expand=True, padx=12, pady=10)
        ttk.Button(footer, text="Save non-secret settings", command=self._on_save).pack(side="right", padx=4, pady=7)
        ttk.Button(footer, text="Close", command=self._close).pack(side="right", padx=(4, 12), pady=7)

    def _add_entry(self, parent: tk.Widget, row: int, label: str, variable: tk.StringVar, *, secret: bool = False) -> tk.Entry:
        tk.Label(parent, text=label, bg=theme.BG, fg=theme.TEXT_MUTED).grid(row=row, column=0, sticky="w", padx=16, pady=7)
        entry = tk.Entry(parent, textvariable=variable, width=54, show=API_KEY_ENTRY_MASK if secret else "")
        entry.grid(row=row, column=1, sticky="ew", padx=16, pady=7)
        return entry

    def _build_connections_tab(self) -> None:
        self.connections_tab.columnconfigure(1, weight=1)
        self.provider_var = tk.StringVar()
        self.base_url_var = tk.StringVar()
        self.api_key_var = tk.StringVar()
        self.app_title_var = tk.StringVar()
        self.timeout_var = tk.StringVar()
        self.max_tokens_var = tk.StringVar()
        self._add_entry(self.connections_tab, 0, "Provider name", self.provider_var)
        self._add_entry(self.connections_tab, 1, "Base URL", self.base_url_var)
        self._key_entry = self._add_entry(self.connections_tab, 2, "API key (this session only)", self.api_key_var, secret=True)
        self._add_entry(self.connections_tab, 3, "Application title", self.app_title_var)
        self._add_entry(self.connections_tab, 4, "Request timeout (seconds)", self.timeout_var)
        self._add_entry(self.connections_tab, 5, "Max response tokens (optional)", self.max_tokens_var)
        tk.Label(
            self.connections_tab,
            text="The key is masked, never prefilled, and never saved. A connection is eligible only after complete operator entry.",
            bg=theme.BG, fg=theme.TEXT_MUTED, wraplength=620, justify="left",
        ).grid(row=6, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 14))
        controls = tk.Frame(self.connections_tab, bg=theme.BG)
        controls.grid(row=7, column=0, columnspan=2, sticky="w", padx=16)
        ttk.Button(controls, text="Use key for this session", command=self._on_use_for_session).pack(side="left", padx=(0, 6))
        ttk.Button(controls, text="Clear session key", command=self._on_clear_key).pack(side="left", padx=6)
        ttk.Button(controls, text="Test connection", command=self._on_test_connection).pack(side="left", padx=6)

    def _build_primary_tab(self) -> None:
        self.primary_tab.columnconfigure(1, weight=1)
        tk.Label(self.primary_tab, text="Primary model", bg=theme.BG, fg=theme.TEXT_MUTED).grid(
            row=0, column=0, sticky="w", padx=16, pady=(18, 7)
        )
        self.primary_model_var = tk.StringVar()
        # Kept as a compatibility alias for the earlier controlled form and
        # its tests; it still refers to the same primary selector.
        self.manual_model_var = self.primary_model_var
        self.primary_model_combo = ttk.Combobox(self.primary_tab, textvariable=self.primary_model_var, state="readonly", width=52)
        self.primary_model_combo.grid(row=0, column=1, sticky="ew", padx=16, pady=(18, 7))
        self.primary_model_combo.bind("<<ComboboxSelected>>", lambda _event: self._on_primary_selected())
        ttk.Button(self.primary_tab, text="Refresh provider catalog", command=self._on_catalog_refresh).grid(
            row=1, column=1, sticky="w", padx=16, pady=7
        )
        tk.Label(
            self.primary_tab,
            text="Only model IDs from a configured provider connection are shown. No model is invented, selected automatically, or switched after an error.",
            bg=theme.BG, fg=theme.TEXT_MUTED, wraplength=600, justify="left",
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=16, pady=10)

    def _build_loop_tab(self) -> None:
        self.loop_tab.columnconfigure(2, weight=1)
        self.observer_vars: list[dict[str, tk.Variable]] = []
        for index, slot in enumerate(self.cockpit.observer_slots):
            frame = tk.Frame(self.loop_tab, bg=theme.PANEL, highlightbackground=theme.BORDER, highlightthickness=1)
            frame.grid(row=index, column=0, columnspan=3, sticky="ew", padx=14, pady=(14 if index == 0 else 5, 5))
            frame.columnconfigure(4, weight=1)
            enabled = tk.BooleanVar(value=slot.enabled)
            provider = tk.StringVar(value=slot.provider_id)
            model = tk.StringVar(value=slot.model_id)
            role = tk.StringVar(value=slot.role)
            tk.Checkbutton(frame, text="Enabled", variable=enabled, bg=theme.PANEL, fg=theme.TEXT, selectcolor=theme.PANEL_ALT,
                           activebackground=theme.PANEL).grid(row=0, column=0, padx=10, pady=8, sticky="w")
            ttk.Combobox(frame, textvariable=role, values=("Logic & Claims", "Safety & Authority", "Evidence & Consistency"),
                         state="readonly", width=24).grid(row=0, column=1, padx=5, pady=8, sticky="w")
            provider_combo = ttk.Combobox(frame, textvariable=provider, state="readonly", width=14)
            provider_combo.grid(row=0, column=2, padx=5, pady=8, sticky="w")
            model_combo = ttk.Combobox(frame, textvariable=model, state="readonly", width=34)
            model_combo.grid(row=0, column=3, padx=5, pady=8, sticky="ew")
            tk.Label(frame, text="METADATA ONLY • NO AUTHORITY", bg=theme.PANEL, fg=theme.TEXT_MUTED,
                     font=theme.base_font(8, "bold")).grid(row=1, column=0, columnspan=4, sticky="w", padx=10, pady=(0, 8))
            variables: dict[str, tk.Variable] = {"enabled": enabled, "provider": provider, "model": model, "role": role}
            self.observer_vars.append(variables)
            provider_combo.bind("<<ComboboxSelected>>", lambda _event, n=index: self._on_observer_provider_changed(n))
            model_combo.bind("<<ComboboxSelected>>", lambda _event, n=index: self._sync_observer(n))
            for variable in (enabled, role):
                variable.trace_add("write", lambda *_args, n=index: self._sync_observer(n))
            variables["provider_combo"] = provider_combo
            variables["model_combo"] = model_combo
        tk.Label(self.loop_tab, text="Run Critical Review is manual. Each enabled valid observer receives one bounded independent request; review never starts automatically.",
                 bg=theme.BG, fg=theme.WARN, wraplength=650, justify="left").grid(row=3, column=0, columnspan=3, sticky="w", padx=16, pady=10)

    def _build_telemetry_tab(self) -> None:
        tk.Label(self.telemetry_tab, text="SMART ROUTER TELEMETRY — NOT CONNECTED IN THIS DEMO", bg=theme.BG, fg=theme.WARN,
                 font=theme.base_font(12, "bold")).pack(anchor="w", padx=18, pady=(24, 10))
        tk.Label(self.telemetry_tab, text="This desktop demo does not add SmartRouter telemetry or change routing policy. No secret, authorization header, or session key is collected here.",
                 bg=theme.BG, fg=theme.TEXT_MUTED, wraplength=620, justify="left").pack(anchor="w", padx=18)

    def _build_safety_tab(self) -> None:
        tk.Label(self.safety_tab, text="Session and safety boundary", bg=theme.BG, fg=theme.TEXT, font=theme.base_font(12, "bold")).pack(
            anchor="w", padx=18, pady=(22, 8)
        )
        tk.Label(self.safety_tab, text="Provider output remains untrusted. Observer output is metadata only and has no authority. Requests are sent only after an operator presses Send; there is no retry, fallback, streaming, or automatic model switch.",
                 bg=theme.BG, fg=theme.TEXT_MUTED, wraplength=620, justify="left").pack(anchor="w", padx=18)
        tk.Label(
            self.safety_tab,
            text="ALERT — SECRET EXPOSURE RISK: never paste a key into the chat, telemetry, or an error report. Use only the masked session field.",
            bg=theme.PANEL_ALT, fg=theme.WARN, wraplength=620, justify="left", padx=10, pady=10,
        ).pack(fill="x", padx=18, pady=(18, 0))

    # --- state --------------------------------------------------------------

    def _load_from_settings(self) -> None:
        settings = self.controller.settings
        self.provider_var.set(settings.provider)
        self.base_url_var.set(settings.api_base_url)
        self.app_title_var.set(settings.app_title)
        self.timeout_var.set(str(settings.timeout_seconds))
        self.max_tokens_var.set(str(settings.max_response_tokens) if settings.max_response_tokens else "")
        self._populate_model_controls()
        self._set_status(
            "API key set for this session (masked; not persisted)." if self.controller.secrets.api_key else "No API key set for this session.",
            theme.TEXT_MUTED,
        )

    def _populate_model_controls(self) -> None:
        models = self._model_supplier()
        providers = tuple(models)
        self.primary_model_combo.configure(values=models.get(self.controller.settings.provider, ()))
        current = self.cockpit.primary_model_id or self.controller.effective_model_id()
        self.primary_model_var.set(current if current in models.get(self.controller.settings.provider, ()) else "")
        for index, variables in enumerate(self.observer_vars):
            provider_combo = variables["provider_combo"]
            model_combo = variables["model_combo"]
            provider_combo.configure(values=providers)
            selected_provider = str(variables["provider"].get())
            model_combo.configure(values=models.get(selected_provider, ()))
            if str(variables["model"].get()) not in models.get(selected_provider, ()):
                variables["model"].set("")
            self._sync_observer(index)

    def _apply_non_secret_fields(self) -> None:
        settings = self.controller.settings
        settings.provider = self.provider_var.get().strip().casefold()
        settings.api_base_url = self.base_url_var.get().strip()
        settings.app_title = self.app_title_var.get().strip() or settings.app_title
        try:
            settings.timeout_seconds = max(1.0, float(self.timeout_var.get().strip()))
        except ValueError:
            pass
        primary_var = getattr(self, "primary_model_var", getattr(self, "manual_model_var", None))
        selected = primary_var.get().strip() if primary_var is not None else ""
        if not selected and hasattr(self, "manual_model_var"):
            selected = self.manual_model_var.get().strip()
        if selected:
            settings.manual_model_id = selected
            settings.selected_model_id = selected
            if hasattr(self, "cockpit"):
                self.cockpit.set_primary_model(selected)
        raw_max_tokens = self.max_tokens_var.get().strip()
        settings.max_response_tokens = int(raw_max_tokens) if raw_max_tokens.isdigit() else None
        if hasattr(self, "observer_vars"):
            for index in range(3):
                self._sync_observer(index)

    def _on_primary_selected(self) -> None:
        selected = self.primary_model_var.get().strip()
        if selected:
            self.cockpit.set_primary_model(selected)
            self._set_status("Primary model selected for this session. Save to retain it after restart.", theme.ACCENT)

    def _on_observer_provider_changed(self, index: int) -> None:
        variables = self.observer_vars[index]
        provider = str(variables["provider"].get())
        variables["model_combo"].configure(values=self._model_supplier().get(provider, ()))
        variables["model"].set("")
        self._sync_observer(index)

    def _sync_observer(self, index: int) -> None:
        slot = self.cockpit.observer_slots[index]
        variables = self.observer_vars[index]
        slot.enabled = bool(variables["enabled"].get())
        slot.provider_id = str(variables["provider"].get())
        slot.model_id = str(variables["model"].get())
        slot.role = str(variables["role"].get())
        slot.state = "Ready for manual review" if slot.enabled and slot.provider_id and slot.model_id else "Not configured"

    def _on_catalog_refresh(self) -> None:
        self._apply_non_secret_fields()
        if self._on_refresh_models is None:
            self._set_status("Provider catalog refresh is unavailable.", theme.WARN)
            return
        self._on_refresh_models()
        self._populate_model_controls()

    def _on_use_for_session(self) -> None:
        key = self.api_key_var.get().strip()
        if not key:
            self._set_status("Enter a key manually first.", theme.WARN)
            return
        self.controller.secrets.set_for_session(key)
        self.api_key_var.set("")
        self._set_status("API key set for this session (masked; memory only).", theme.ACCENT)

    def _on_clear_key(self) -> None:
        self.controller.secrets.clear()
        self.api_key_var.set("")
        self._set_status("Session API key cleared.", theme.TEXT_MUTED)

    def _on_test_connection(self) -> None:
        self._apply_non_secret_fields()
        if not self.controller.secrets.api_key:
            self._set_status("Enter and apply a session key before testing.", theme.WARN)
            return
        self._set_status("Testing controlled connection…", theme.TEXT_MUTED)
        self.update_idletasks()
        try:
            self.controller.test_connection()
        except ProviderError as error:
            self._set_status(f"Connection failed: {error}", theme.ERROR)
            return
        self._set_status("Connection OK.", theme.ACCENT)

    def _on_save(self) -> None:
        self._apply_non_secret_fields()
        self.controller.save_current_settings()
        self._on_saved()
        self._set_status("Non-secret settings saved. API keys are never written to disk.", theme.ACCENT)

    def _set_status(self, text: str, color: str) -> None:
        self.status_label.configure(text=text, fg=color)

    def _close(self) -> None:
        self.grab_release()
        self.destroy()
