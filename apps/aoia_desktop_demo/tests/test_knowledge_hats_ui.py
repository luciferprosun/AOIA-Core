from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from apps.aoia_desktop_demo.app import (
    STATUS_HUMAN_REQUIRED,
    SUGGESTION_LABEL,
)
from apps.aoia_desktop_demo.knowledge.hats.contracts import HatDescriptor, HatStatus
from apps.aoia_desktop_demo.knowledge.hats.registry import HatRegistry
from apps.aoia_desktop_demo.tests.knowledge_hat_test_support import make_attachment
from apps.aoia_desktop_demo.ui.hat_evidence_dialog import (
    EVIDENCE_ONLY_MARKER,
    HUMAN_REVIEW_MARKER,
    format_hat_evidence,
)
from apps.aoia_desktop_demo.ui.main_window import MainWindow
from apps.aoia_desktop_demo.ui.settings_dialog import SettingsDialog


class _Label:
    def __init__(self) -> None:
        self.options: dict[str, object] = {}

    def configure(self, **options) -> None:
        self.options.update(options)


def _descriptor() -> HatDescriptor:
    return HatDescriptor(
        hat_id="fixture_hat",
        display_name="Fixture HAT",
        domain="fixture_domain",
        adapter_id="fixture_hat_v1",
        descriptor_schema_version=1,
        evidence_schema_version=1,
        external_resource=True,
        authoritative=False,
    )


def _status(state: str) -> HatStatus:
    if state == "ready":
        return HatStatus(
            hat_id="fixture_hat",
            state="ready",
            library_id="fixture-library",
            library_version="1",
            manifest_id="fixture-manifest",
            manifest_digest="1" * 64,
            index_id="fixture-index",
            index_digest="2" * 64,
            indexed_source_count=1,
            read_only=True,
            local_only=True,
            error_category=None,
        )
    return HatStatus(
        hat_id="fixture_hat",
        state=state,
        library_id=None,
        library_version=None,
        manifest_id=None,
        manifest_digest=None,
        index_id=None,
        index_digest=None,
        indexed_source_count=None,
        read_only=True,
        local_only=True,
        error_category=f"fixture_{state}",
    )


class EvidencePreviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.attachment = make_attachment(_descriptor())

    def test_preview_contains_all_identities_hashes_and_authority_markers(self) -> None:
        preview = format_hat_evidence(self.attachment)
        for expected in (
            EVIDENCE_ONLY_MARKER,
            HUMAN_REVIEW_MARKER,
            "Knowledge HAT: Fixture HAT",
            "Logical id: fixture_hat",
            "Library: fixture-library 1",
            "Manifest: fixture-manifest",
            self.attachment.bundle.manifest_digest,
            "Index: fixture-index",
            self.attachment.bundle.index_digest,
            self.attachment.bundle.passages[0].source_title,
            self.attachment.bundle.passages[0].source_id,
            self.attachment.bundle.passages[0].source_locator,
            self.attachment.bundle.bundle_hash,
            self.attachment.attachment_hash,
        ):
            self.assertIn(expected, preview)
        self.assertNotIn(str(Path.home()), preview)
        self.assertNotIn(str(Path("/tmp")), preview)

    def test_opening_preview_uses_retained_attachment_and_does_not_retrieve(self) -> None:
        calls = {"retrieval": 0}

        class _Controller:
            def retained_hat_attachment(self):
                return self.attachment

            def prepare_attachment(self):
                calls["retrieval"] += 1

        controller = _Controller()
        controller.attachment = self.attachment
        window = object.__new__(MainWindow)
        window.controller = controller
        window.view_hat_evidence_button = object()
        with patch(
            "apps.aoia_desktop_demo.ui.main_window.HatEvidenceDialog"
        ) as dialog:
            MainWindow._view_hat_evidence(window)
        dialog.assert_called_once_with(
            window,
            self.attachment,
            window.view_hat_evidence_button,
        )
        self.assertEqual(calls["retrieval"], 0)

    def test_formatting_is_read_only_and_deterministic(self) -> None:
        before_hash = self.attachment.attachment_hash
        first = format_hat_evidence(self.attachment)
        second = format_hat_evidence(self.attachment)
        self.assertEqual(first, second)
        self.assertEqual(self.attachment.attachment_hash, before_hash)


class HatSettingsUiStateTests(unittest.TestCase):
    def test_operator_selection_explicitly_sets_logical_hat_id(self) -> None:
        none = HatDescriptor(
            hat_id="none",
            display_name="None",
            domain="none",
            adapter_id="none",
            descriptor_schema_version=1,
            evidence_schema_version=1,
            external_resource=False,
            authoritative=False,
        )
        german = HatDescriptor(
            hat_id="german_federal_employment_worker_law",
            display_name="German Federal Law",
            domain="german_federal_employment_law",
            adapter_id="german_federal_employment_worker_law_v1",
            descriptor_schema_version=1,
            evidence_schema_version=1,
            external_resource=True,
            authoritative=False,
        )
        selected: list[str] = []
        dialog = object.__new__(SettingsDialog)
        dialog.controller = SimpleNamespace(
            knowledge_hats=(none, german),
            set_knowledge_hat=selected.append,
        )
        dialog.hat_var = SimpleNamespace(get=lambda: "German Federal Law")
        dialog._render_hat_status = lambda: None
        dialog._set_status = lambda _text, _color: None
        SettingsDialog._on_hat_selected(dialog)
        self.assertEqual(selected, ["german_federal_employment_worker_law"])

    def test_status_renderer_supports_ready_unavailable_and_invalid(self) -> None:
        for state in ("ready", "unavailable", "invalid"):
            with self.subTest(state=state):
                dialog = object.__new__(SettingsDialog)
                dialog.controller = SimpleNamespace(
                    inspect_knowledge_hat=lambda state=state: _status(state),
                    settings=SimpleNamespace(
                        knowledge_hat_configuration_notice=""
                    ),
                )
                dialog.hat_status_labels = {
                    key: _Label()
                    for key in (
                        "state",
                        "library",
                        "manifest",
                        "index",
                        "count",
                        "local",
                        "read_only",
                        "authority",
                    )
                }
                SettingsDialog._render_hat_status(dialog)
                self.assertEqual(
                    dialog.hat_status_labels["state"].options["text"],
                    state,
                )
                self.assertEqual(
                    dialog.hat_status_labels["authority"].options["text"],
                    "EVIDENCE ONLY — NON-AUTHORITATIVE",
                )
                if state == "ready":
                    self.assertIn(
                        "SHA-256",
                        dialog.hat_status_labels["manifest"].options["text"],
                    )
                    self.assertIn(
                        "SHA-256",
                        dialog.hat_status_labels["index"].options["text"],
                    )

    def test_actual_ui_labels_and_final_non_authority_markers_are_present(self) -> None:
        main_source = (
            Path(__file__).resolve().parents[1] / "ui" / "main_window.py"
        ).read_text(encoding="utf-8")
        settings_source = (
            Path(__file__).resolve().parents[1] / "ui" / "settings_dialog.py"
        ).read_text(encoding="utf-8")
        for label in ("Settings", "View HAT Evidence", "Send"):
            self.assertIn(f'text="{label}"', main_source)
        for label in (
            "Knowledge HAT",
            "Logic & Claims",
            "Safety & Authority",
            "Evidence & Consistency",
        ):
            self.assertIn(label, settings_source)
        self.assertEqual(
            [
                descriptor.display_name
                for descriptor in HatRegistry.default().list_descriptors()
            ],
            ["None", "German Federal Law"],
        )
        self.assertIn("not authority", SUGGESTION_LABEL)
        self.assertEqual(STATUS_HUMAN_REQUIRED, "Human control: Required")


if __name__ == "__main__":
    unittest.main()
