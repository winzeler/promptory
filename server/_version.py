"""Single source of truth for the Promptdis version (read from root VERSION file)."""

from pathlib import Path

__version__ = (Path(__file__).parent.parent / "VERSION").read_text().strip()
