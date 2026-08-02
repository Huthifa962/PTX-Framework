"""
core/banner.py
==============

Renders the PTX startup banner. The ASCII art is stored here (not in the shell)
so the presentation layer stays isolated and the banner can be re-themed or
swapped without touching program logic.
"""

from __future__ import annotations

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .colors import PALETTE

# Raw ASCII art. Kept as a module constant so `banner` command and startup can
# both reuse it. Braces / backslashes are safe here because it is a plain str.
_ASCII: str = r"""
██████╗ ████████╗██╗  ██╗
██╔══██╗╚══██╔══╝╚██╗██╔╝
██████╔╝   ██║    ╚███╔╝
██╔═══╝    ██║    ██╔██╗
██║        ██║   ██╔╝ ██╗
╚═╝        ╚═╝   ╚═╝  ╚═╝
"""


def render_banner(console: Console, version: str) -> None:
    """Print the framework banner to ``console``.

    Parameters
    ----------
    console:
        The active Rich console used for output.
    version:
        Semantic version string shown under the title.
    """
    art = Text(_ASCII.strip("\n"), style=PALETTE.title)
    subtitle = Text("Professional Pentesting Framework", style=PALETTE.subtitle)
    meta = Text(f"Version {version}", style=PALETTE.muted)
    hint = Text('Type "help" to list available commands.', style=PALETTE.text)

    body = Text("\n").join([art, Text(""), subtitle, meta, Text(""), hint])
    console.print(
        Panel(
            Align.center(body),
            border_style=PALETTE.border,
            padding=(1, 4),
        )
    )
