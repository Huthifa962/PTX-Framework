"""
core/navigator.py
=================

The level state machine.

PTX is navigated like a nested shell (inspired by msfconsole + Cisco IOS):

    Level 0  ptx>                                 -- no context
    Level 1  ptx(Network Penetration Testing)>    -- a path is selected
    Level 2  ptx(Network.../Reconnaissance)>      -- a phase is selected
    Level 3  ptx(Network.../Recon/nmap)>          -- a tool is selected

The :class:`Navigator` holds the current selection and knows how to move
``use`` / ``back`` / ``home`` between levels. It contains no rendering and no
I/O -- it is a pure state object, which keeps it trivial to test.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Optional

from .database import Database, PathEntry, Phase, Tool


class Level(IntEnum):
    """The four navigation depths."""

    ROOT = 0
    PATH = 1
    PHASE = 2
    TOOL = 3


class NavigationError(Exception):
    """Raised when a ``use`` target cannot be resolved at the current level."""


class Navigator:
    """Tracks and mutates the current position in the knowledge base."""

    def __init__(self, database: Database) -> None:
        self._db = database
        self.path: Optional[PathEntry] = None
        self.phase: Optional[Phase] = None
        self.tool: Optional[Tool] = None

    # -- Introspection --------------------------------------------------------
    @property
    def level(self) -> Level:
        if self.tool is not None:
            return Level.TOOL
        if self.phase is not None:
            return Level.PHASE
        if self.path is not None:
            return Level.PATH
        return Level.ROOT

    def prompt_context(self) -> str:
        """Return the parenthetical context shown in the prompt.

        ``""``                                    at ROOT
        ``Network Penetration Testing``           at PATH
        ``Network Penetration Testing/Recon``     at PHASE
        ``Network.../Recon/nmap``                 at TOOL
        """
        parts: list[str] = []
        if self.path is not None:
            parts.append(self.path.name)
        if self.phase is not None:
            parts.append(self.phase.name)
        if self.tool is not None:
            parts.append(self.tool.name)
        return "/".join(parts)

    def breadcrumb(self) -> str:
        """Human-readable location for the ``pwd`` command."""
        context = self.prompt_context()
        return f"/{context}" if context else "/"

    # -- Movement -------------------------------------------------------------
    def use(self, target: str) -> Level:
        """Descend into ``target`` from the current level.

        Returns the new :class:`Level`. Raises :class:`NavigationError` when the
        target does not exist at the current depth.
        """
        target = target.strip()
        if not target:
            raise NavigationError("use requires a target (index, name, or slug).")

        # Expand global aliases (aliases.json) so `use web`, `use recon`, etc.
        # resolve to their canonical path / phase names.
        target = self._db.expand_alias(target)

        current = self.level
        if current is Level.ROOT:
            return self._use_path(target)
        if current is Level.PATH:
            return self._use_phase(target)
        if current is Level.PHASE:
            return self._use_tool(target)
        # Already at TOOL: allow hopping to a sibling tool for convenience.
        return self._use_sibling_tool(target)

    def _use_path(self, target: str) -> Level:
        path = self._db.resolve_path(target)
        if path is None:
            raise NavigationError(f"No such path: {target!r}")
        self.path, self.phase, self.tool = path, None, None
        return Level.PATH

    def _use_phase(self, target: str) -> Level:
        assert self.path is not None
        phase = self.path.phase_by_key(target)
        if phase is None:
            raise NavigationError(f"No such phase in {self.path.name}: {target!r}")
        self.phase, self.tool = phase, None
        return Level.PHASE

    def _use_tool(self, target: str) -> Level:
        assert self.path is not None and self.phase is not None
        tool = self._db.resolve_tool(target, self.path, self.phase)
        if tool is None:
            raise NavigationError(
                f"No such tool in {self.phase.name}: {target!r}"
            )
        self.tool = tool
        return Level.TOOL

    def _use_sibling_tool(self, target: str) -> Level:
        assert self.path is not None and self.phase is not None
        tool = self._db.resolve_tool(target, self.path, self.phase)
        if tool is None:
            raise NavigationError(f"No such tool: {target!r}")
        self.tool = tool
        return Level.TOOL

    # -- Ascending ------------------------------------------------------------
    def back(self) -> Level:
        """Ascend exactly one level. No-op (returns ROOT) if already at ROOT."""
        if self.tool is not None:
            self.tool = None
        elif self.phase is not None:
            self.phase = None
        elif self.path is not None:
            self.path = None
        return self.level

    def home(self) -> Level:
        """Jump straight back to ROOT."""
        self.path = self.phase = self.tool = None
        return Level.ROOT
