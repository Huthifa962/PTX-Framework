"""
core/parser.py
==============

Turns a raw input line into a structured :class:`ParsedCommand` and centralizes
per-command help. Every command supports ``-h`` / ``--help``; the parser
detects those flags generically so individual handlers do not have to.

The parser uses :func:`shlex.split` so quoted arguments work naturally, e.g.::

    use "Network Penetration Testing"
    search "sql injection"
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CommandSpec:
    """Static metadata describing a single command's help output."""

    name: str
    summary: str
    usage: str
    details: str = ""


@dataclass
class ParsedCommand:
    """The result of parsing one input line."""

    name: str
    args: list[str] = field(default_factory=list)
    wants_help: bool = False
    raw: str = ""

    @property
    def is_empty(self) -> bool:
        return not self.name


# Central registry of command help. Keeping specs here (data, not logic) means
# `help` and per-command `-h` stay perfectly in sync.
COMMAND_SPECS: dict[str, CommandSpec] = {
    "help": CommandSpec("help", "List commands or show help for one.", "help [command]"),
    "show": CommandSpec(
        "show",
        "Display paths, methodology, roadmap, or tools for the current level.",
        "show <paths [--flat]|methodology|roadmap|tools>",
    ),
    "methodology": CommandSpec(
        "methodology",
        "Show the universal PTES / kill-chain phase spine.",
        "methodology",
        "The 8-phase backbone (pre-engagement -> reporting) shared by every path.",
    ),
    "use": CommandSpec(
        "use",
        "Select a path, phase, or tool by index / name.",
        'use <index|name>',
        "Works at every level. Example: `use 0`, `use nmap`, "
        'or `use "Web Penetration Testing"`.',
    ),
    "search": CommandSpec(
        "search",
        "Fuzzy-search tools by name, keyword, description, or alias.",
        "search <query>",
    ),
    "info": CommandSpec("info", "Show the full data sheet for the current tool.", "info"),
    "examples": CommandSpec("examples", "Show usage examples for the current tool.", "examples"),
    "cheatsheet": CommandSpec("cheatsheet", "Show the quick reference for the current tool.", "cheatsheet"),
    "workflow": CommandSpec("workflow", "Show the roadmap diagram for the current path.", "workflow"),
    "which": CommandSpec("which", "Show the install path of the current tool's binary.", "which"),
    "run": CommandSpec(
        "run",
        "Launch the current tool, passing through any arguments.",
        "run [tool-args...]",
        "Example inside a tool context: `run -A 192.168.1.5` executes "
        "`nmap -A 192.168.1.5`.",
    ),
    "install": CommandSpec("install", "Install the current tool via its package manager.", "install"),
    "update": CommandSpec("update", "Update the current tool via its package manager.", "update"),
    "back": CommandSpec("back", "Go up one level.", "back"),
    "home": CommandSpec("home", "Return to the top level.", "home"),
    "pwd": CommandSpec("pwd", "Print the current navigation location.", "pwd"),
    "history": CommandSpec("history", "Show recent commands.", "history [count]"),
    "banner": CommandSpec("banner", "Reprint the PTX banner.", "banner"),
    "clear": CommandSpec("clear", "Clear the screen.", "clear"),
    "exit": CommandSpec("exit", "Quit PTX.", "exit"),
}

# Common aliases mapped to canonical command names.
COMMAND_ALIASES: dict[str, str] = {
    "quit": "exit",
    "q": "exit",
    "ls": "show",
    "cls": "clear",
    "?": "help",
    "cd": "use",
}

_HELP_FLAGS = {"-h", "--help"}


class Parser:
    """Stateless line parser (safe to share a single instance)."""

    def parse(self, line: str) -> ParsedCommand:
        """Tokenize ``line`` into a :class:`ParsedCommand`.

        Falls back to naive whitespace splitting if the line contains an
        unbalanced quote, so a stray ``"`` never crashes the shell.
        """
        raw = line.strip()
        if not raw:
            return ParsedCommand(name="", raw=raw)
        try:
            tokens = shlex.split(raw)
        except ValueError:
            tokens = raw.split()

        name = tokens[0].lower()
        name = COMMAND_ALIASES.get(name, name)
        rest = tokens[1:]

        wants_help = any(tok in _HELP_FLAGS for tok in rest)
        args = [tok for tok in rest if tok not in _HELP_FLAGS]
        return ParsedCommand(name=name, args=args, wants_help=wants_help, raw=raw)

    @staticmethod
    def spec(command: str) -> CommandSpec | None:
        """Return the :class:`CommandSpec` for ``command`` if it exists."""
        return COMMAND_SPECS.get(COMMAND_ALIASES.get(command, command))
