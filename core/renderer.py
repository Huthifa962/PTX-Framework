"""
core/renderer.py
================

Everything that draws to the screen lives here. Command handlers stay free of
formatting concerns; they call semantic methods like ``renderer.paths(...)`` or
``renderer.tool_info(...)`` and the renderer owns the Rich layout, colors, and
Unicode. This isolation means the entire UI can be restyled from two files
(``colors.py`` + this one).
"""

from __future__ import annotations

from typing import Iterable, Sequence

from rich.box import ROUNDED, SIMPLE
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .colors import PALETTE
from .database import PathEntry, Phase, Tool
from .parser import COMMAND_SPECS, CommandSpec
from .utils import truncate


class Renderer:
    """Thin, semantic wrapper around a Rich :class:`~rich.console.Console`."""

    def __init__(self, console: Console) -> None:
        self.console = console

    # -- Generic messages -----------------------------------------------------
    def info(self, message: str) -> None:
        self.console.print(Text(message, style=PALETTE.text))

    def success(self, message: str) -> None:
        self.console.print(Text(f"[+] {message}", style=PALETTE.success))

    def warning(self, message: str) -> None:
        self.console.print(Text(f"[!] {message}", style=PALETTE.warning))

    def error(self, message: str) -> None:
        self.console.print(Text(f"[x] {message}", style=PALETTE.error))

    def blank(self) -> None:
        self.console.print()

    def _table(self, title: str) -> Table:
        """Build a consistently-styled table shell."""
        table = Table(
            title=title,
            title_style=PALETTE.title,
            box=ROUNDED,
            border_style=PALETTE.border,
            header_style=PALETTE.subtitle,
            expand=False,
            pad_edge=False,
        )
        return table

    # -- Level 1: paths -------------------------------------------------------
    def paths(self, paths: Sequence[PathEntry]) -> None:
        table = self._table("Penetration Testing Paths")
        table.add_column("#", justify="right", style=PALETTE.muted, no_wrap=True)
        table.add_column("Path", style=PALETTE.text)
        table.add_column("Group", style=PALETTE.subtitle, no_wrap=True)
        table.add_column("Description", style=PALETTE.muted)
        for path in paths:
            table.add_row(
                str(path.index), path.name, path.group, truncate(path.description, 52)
            )
        self.console.print(table)

    def paths_grouped(self, grouped: dict[str, Sequence[PathEntry]]) -> None:
        """Dashboard view: paths presented under their domain group headings."""
        renderables = []
        for group, members in grouped.items():
            inner = Table(box=SIMPLE, show_header=False, border_style=PALETTE.border,
                          pad_edge=False, expand=True)
            inner.add_column("#", justify="right", style=PALETTE.muted, no_wrap=True, width=4)
            inner.add_column("Path", style=PALETTE.text, no_wrap=True)
            inner.add_column("Description", style=PALETTE.muted)
            for path in members:
                inner.add_row(str(path.index), path.name, truncate(path.description, 54))
            renderables.append(
                Panel(
                    inner,
                    title=Text(group, style=PALETTE.title),
                    border_style=PALETTE.border,
                    padding=(0, 1),
                )
            )
        self.console.print(
            Panel(
                Group(*renderables),
                title=Text("PTX — Penetration Testing Domains", style=PALETTE.title),
                border_style=PALETTE.border,
                padding=(1, 1),
            )
        )

    def methodology(self, phases: Sequence[dict]) -> None:
        """Render the universal methodology spine as a numbered chain."""
        if not phases:
            self.warning("No methodology defined.")
            return
        lines: list[Text] = []
        for i, phase in enumerate(phases):
            row = Text()
            row.append(f"  {i}. ", style=PALETTE.subtitle)
            row.append(phase.get("name", ""), style=PALETTE.text)
            desc = phase.get("description", "")
            if desc:
                row.append(f"\n       {desc}", style=PALETTE.muted)
            lines.append(row)
            if i < len(phases) - 1:
                lines.append(Text(f"     {PALETTE.arrow}", style=PALETTE.subtitle))
        self.console.print(
            Panel(
                Group(*lines),
                title=Text("Universal Methodology (PTES / kill-chain)", style=PALETTE.title),
                border_style=PALETTE.border,
                padding=(1, 2),
            )
        )

    # -- Level 2: roadmap -----------------------------------------------------
    def roadmap(self, path: PathEntry) -> None:
        table = self._table(f"{path.name} — Roadmap")
        table.add_column("#", justify="right", style=PALETTE.muted, no_wrap=True)
        table.add_column("Phase", style=PALETTE.text)
        table.add_column("Description", style=PALETTE.muted)
        if not path.roadmap:
            self.warning(f"No roadmap defined for {path.name}.")
            return
        for phase in path.roadmap:
            table.add_row(str(phase.index), phase.name, truncate(phase.description, 60))
        self.console.print(table)

    # -- Level 3: tools -------------------------------------------------------
    def tools(self, path: PathEntry, phase: Phase, tools: Sequence[Tool]) -> None:
        table = self._table(f"{path.name} / {phase.name} — Tools")
        table.add_column("#", justify="right", style=PALETTE.muted, no_wrap=True)
        table.add_column("Tool", style=PALETTE.text, no_wrap=True)
        table.add_column("Description", style=PALETTE.muted)
        table.add_column("Installed", justify="center")
        table.add_column("Platform", style=PALETTE.text, no_wrap=True)
        table.add_column("Difficulty", style=PALETTE.text, no_wrap=True)
        if not tools:
            self.warning("No tools registered for this phase yet.")
            self.info("Drop a YAML file in the matching database/ folder to add one.")
            return
        for index, tool in enumerate(tools):
            name = f"★ {tool.name}" if tool.recommended else tool.name
            table.add_row(
                str(index),
                name,
                truncate(tool.description, 46),
                PALETTE.installed_glyph(tool.installed),
                tool.platform,
                self._difficulty(tool.difficulty),
            )
        self.console.print(table)
        if any(t.recommended for t in tools):
            self.console.print(
                Text("  ★ = most reached-for tool in this category", style=PALETTE.muted)
            )

    def _difficulty(self, value: str) -> Text:
        colors = {
            "easy": PALETTE.success,
            "medium": PALETTE.warning,
            "hard": PALETTE.missing,
        }
        return Text(value, style=colors.get(value.lower(), PALETTE.text))

    # -- Search results -------------------------------------------------------
    def search_results(self, results: Iterable[tuple[Tool, float]]) -> None:
        results = list(results)
        table = self._table("Search Results")
        table.add_column("Tool", style=PALETTE.text, no_wrap=True)
        table.add_column("Category", style=PALETTE.muted, no_wrap=True)
        table.add_column("Description", style=PALETTE.muted)
        table.add_column("Installed", justify="center")
        if not results:
            self.warning("No matches found.")
            return
        for tool, _score in results:
            table.add_row(
                tool.name,
                tool.category,
                truncate(tool.description, 50),
                PALETTE.installed_glyph(tool.installed),
            )
        self.console.print(table)

    # -- Tool info card -------------------------------------------------------
    def tool_info(self, tool: Tool, install_path: str | None) -> None:
        table = Table(box=SIMPLE, show_header=False, border_style=PALETTE.border,
                      pad_edge=False)
        table.add_column("Field", style=PALETTE.subtitle, no_wrap=True)
        table.add_column("Value", style=PALETTE.text)

        status = (
            Text(f"Yes  ({install_path})", style=PALETTE.installed)
            if tool.installed
            else Text("No", style=PALETTE.missing)
        )
        rows = [
            ("Name", tool.name),
            ("Description", tool.description),
            ("Purpose", tool.purpose),
            ("Recommended", "★ Yes — first reach in its category" if tool.recommended else "—"),
            ("Category", tool.category),
            ("Binary", tool.binary),
            ("Package", tool.package),
            ("Installation", ", ".join(tool.installation.keys()) or "n/a"),
            ("Website", tool.website),
            ("Documentation", tool.documentation),
            ("License", tool.license),
            ("Author", tool.author),
            ("Difficulty", tool.difficulty),
            ("Platform", tool.platform),
            ("Aliases", ", ".join(tool.aliases) or "—"),
            ("Related Tools", ", ".join(tool.related_tools) or "—"),
        ]
        for label, value in rows:
            table.add_row(label, value or "—")
        table.add_row("Installed", status)

        body: list = [table]
        if tool.note:
            body.append(Text(f"\n⚠ {tool.note}", style=PALETTE.warning))

        self.console.print(
            Panel(
                Group(*body),
                title=Text(tool.name, style=PALETTE.title),
                border_style=PALETTE.border,
                padding=(1, 2),
            )
        )

    # -- Examples -------------------------------------------------------------
    def examples(self, tool: Tool) -> None:
        if not tool.examples:
            self.warning(f"No examples recorded for {tool.name}.")
            return
        renderables = []
        for item in tool.examples:
            title = item.get("title", "")
            command = item.get("command", "")
            note = item.get("note", "")
            block = Text()
            block.append(f"# {title}\n", style=PALETTE.subtitle)
            block.append(f"  {command}\n", style=PALETTE.success)
            if note:
                block.append(f"  {note}", style=PALETTE.muted)
            renderables.append(block)
        self.console.print(
            Panel(
                Group(*renderables),
                title=Text(f"{tool.name} — Examples", style=PALETTE.title),
                border_style=PALETTE.border,
                padding=(1, 2),
            )
        )

    # -- Cheatsheet -----------------------------------------------------------
    def cheatsheet(self, tool: Tool) -> None:
        if not tool.cheatsheet:
            self.warning(f"No cheat sheet recorded for {tool.name}.")
            return
        table = self._table(f"{tool.name} — Cheat Sheet")
        table.add_column("Purpose", style=PALETTE.text)
        table.add_column("Command", style=PALETTE.success)
        for entry in tool.cheatsheet:
            table.add_row(entry.get("title", ""), entry.get("command", ""))
        self.console.print(table)

    # -- Workflow diagram -----------------------------------------------------
    def workflow(self, path: PathEntry) -> None:
        if not path.roadmap:
            self.warning(f"No workflow defined for {path.name}.")
            return
        lines: list[Text] = []
        for i, phase in enumerate(path.roadmap):
            lines.append(Text(f"  {phase.name}", style=PALETTE.text))
            if i < len(path.roadmap) - 1:
                lines.append(Text(f"    {PALETTE.arrow}", style=PALETTE.subtitle))
        self.console.print(
            Panel(
                Group(*lines),
                title=Text(f"{path.name} — Workflow", style=PALETTE.title),
                border_style=PALETTE.border,
                padding=(1, 2),
            )
        )

    # -- Help -----------------------------------------------------------------
    def help_overview(self) -> None:
        table = self._table("Commands")
        table.add_column("Command", style=PALETTE.subtitle, no_wrap=True)
        table.add_column("Description", style=PALETTE.text)
        for spec in COMMAND_SPECS.values():
            table.add_row(spec.name, spec.summary)
        self.console.print(table)
        self.info("Every command accepts -h / --help for details.")

    def command_help(self, spec: CommandSpec) -> None:
        body = Text()
        body.append(f"{spec.summary}\n\n", style=PALETTE.text)
        body.append("Usage: ", style=PALETTE.subtitle)
        body.append(f"{spec.usage}\n", style=PALETTE.success)
        if spec.details:
            body.append("\n")
            body.append(spec.details, style=PALETTE.muted)
        self.console.print(
            Panel(
                body,
                title=Text(spec.name, style=PALETTE.title),
                border_style=PALETTE.border,
                padding=(1, 2),
            )
        )
