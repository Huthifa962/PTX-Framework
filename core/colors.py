"""
core/colors.py
==============

Single source of truth for every color / style used across PTX.

The palette is intentionally restrained and professional -- no rainbow output.
All styles are expressed as Rich markup style strings so they can be reused by
any renderer. Keeping them here means the entire look & feel of the framework
can be re-themed from one file.

Color contract (from the PTX design spec):

    Green   -> installed / success
    Red     -> not installed / error
    Yellow  -> warnings
    Blue    -> titles / headings
    White   -> body text
    Gray    -> borders / muted detail
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    """Immutable collection of the styles PTX is allowed to use."""

    # Semantic styles ---------------------------------------------------------
    # Brand color is RED. Installed status stays green (✔) so the positive
    # signal still contrasts hard against the red "missing" (✘) and red titles.
    installed: str = "bold green"
    missing: str = "bold red3"     # not installed -- deeper red than the brand
    warning: str = "yellow"
    title: str = "bold red1"       # titles / headings (was blue)
    subtitle: str = "red"          # column headers / secondary titles (was blue)
    text: str = "white"
    muted: str = "grey58"          # gray -> borders / secondary detail
    border: str = "grey42"
    accent: str = "red1"           # live prompt accent (was cyan)
    success: str = "green"
    error: str = "bold red3"
    prompt: str = "bold red1"

    # Glyphs ------------------------------------------------------------------
    yes_glyph: str = "✔"
    no_glyph: str = "✘"
    arrow: str = "↓"

    def installed_glyph(self, is_installed: bool) -> str:
        """Return a colorized check / cross glyph for a boolean state."""
        if is_installed:
            return f"[{self.installed}]{self.yes_glyph}[/]"
        return f"[{self.missing}]{self.no_glyph}[/]"


# A ready-to-use singleton. Import `PALETTE` everywhere rather than building
# new Palette instances, so the theme stays consistent.
PALETTE = Palette()
