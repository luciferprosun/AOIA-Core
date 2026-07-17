"""AOIA Control Chat — Competition Demo.

A lightweight, human-controlled desktop chat surface demonstrating
AOIA-Core's epistemic-control concept: provider output is never authority,
knowledge retrieval is evidence only, and no action is executed from this
application.

This package is intentionally isolated from the AOIA-Core production
runtime's execution, patch, git, browser, and package-installation
surfaces. It only reads an existing local knowledge index; it never
writes to it.
"""

__app_name__ = "AOIA Control Chat — Competition Demo"
