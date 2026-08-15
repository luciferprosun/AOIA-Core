"""Simple browser shell for the proven AOIA Critical Prompt Loop runtime."""

from .app import create_app
from .runtime import DemoEngine, OBSERVER_ROLES

__all__ = ["DemoEngine", "OBSERVER_ROLES", "create_app"]
