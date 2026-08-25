"""Curated, offline evidence for AOIA-Core's dated-evidence review module.

The registry is deliberately small and human-readable. It is not a general
legal knowledge base. The bundled URLs point to official German government
sources and were checked again on 2026-08-25.
"""

from __future__ import annotations

from copy import deepcopy


_SCENARIO = {
    "id": "de-minimum-wage-2026",
    "title": "German employment law: dated minimum-wage review",
    "jurisdiction": "Germany",
    "domain": "employment law",
    "risk_domain": "HIGH_STAKES_EMPLOYMENT_LAW",
    "as_of_date": "2026-08-25",
    "language": "de",
    "prompt": "Wie hoch ist der gesetzliche Mindestlohn in Deutschland im Juli 2026?",
    "candidate_answer": (
        "Der gesetzliche Mindestlohn beträgt in Deutschland 12,82 Euro brutto "
        "pro Stunde. Das gilt grundsätzlich auch für Minijobs. Damit ist die "
        "Frage eindeutig beantwortet."
    ),
    "corrected_example": (
        "Nach der Fünften Mindestlohnanpassungsverordnung beträgt der allgemeine "
        "gesetzliche Mindestlohn seit dem 1. Januar 2026 13,90 Euro brutto je "
        "Zeitstunde. Ob und welche Sonderregelungen im Einzelfall gelten, muss "
        "anhand der aktuellen offiziellen Quellen geprüft werden."
    ),
    "expected_current_value": "13.90",
    "known_previous_value": "12.82",
    "evidence": [
        {
            "source_id": "DE-BMAS-MINDESTLOHN-OVERVIEW-2026",
            "title": "Der gesetzliche Mindestlohn - Ein Überblick",
            "publisher": "Bundesministerium für Arbeit und Soziales (BMAS)",
            "url": (
                "https://www.bmas.de/DE/Arbeit/Arbeitsrecht/Mindestlohn/"
                "Informationen-zum-Mindestlohn/informationen-zum-mindestlohn-deutsch.html"
            ),
            "checked_at": "2026-08-25",
            "effective_from": "2026-01-01",
            "fact": (
                "The general statutory minimum wage is EUR 13.90 gross per hour "
                "from 1 January 2026."
            ),
            "authority_kind": "official ministry guidance",
        },
        {
            "source_id": "DE-MILOV5-2025",
            "title": "Fünfte Mindestlohnanpassungsverordnung (MiLoV5)",
            "publisher": "Bundesministerium der Justiz / Bundesamt für Justiz",
            "url": "https://www.gesetze-im-internet.de/milov5/MiLoV5.pdf",
            "checked_at": "2026-08-25",
            "effective_from": "2026-01-01",
            "fact": (
                "Section 1 sets EUR 13.90 gross per hour from 1 January 2026 and "
                "EUR 14.60 from 1 January 2027."
            ),
            "authority_kind": "official regulation text",
        },
        {
            "source_id": "DE-BMAS-MINIMUM-WAGE-HISTORY",
            "title": "Gesetzlicher Mindestlohn - rate history",
            "publisher": "Bundesministerium für Arbeit und Soziales (BMAS)",
            "url": (
                "https://www.bmas.de/DE/Arbeit/Arbeitsrecht/Mindestlohn/Glossar/G/"
                "Gesetzlicher-Mindestlohn.html"
            ),
            "checked_at": "2026-08-25",
            "effective_from": "2025-01-01",
            "fact": (
                "The official history lists EUR 12.82 from 1 January 2025 and "
                "EUR 13.90 from 1 January 2026."
            ),
            "authority_kind": "official ministry rate history",
        },
    ],
}


def bundled_scenario() -> dict[str, object]:
    """Return an isolated copy so callers cannot mutate the registry."""

    return deepcopy(_SCENARIO)
