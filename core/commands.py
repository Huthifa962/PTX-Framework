"""
core/commands.py
================

Command handlers.

This is the glue layer: it maps a :class:`~core.parser.ParsedCommand` to an
action, coordinating the navigator, database, renderer, executor, installer and
updater. Each handler is small and single-purpose. Handlers never draw directly
-- they call the renderer -- and never read input directly -- they use the
injected ``confirm`` callback -- which keeps this layer testable and UI-agnostic.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Callable, Optional

from .database import Database, Tool
from .executor import Executor
from .history import History
from .installer import Installer
from .navigator import Level, NavigationError, Navigator
from .parser import COMMAND_SPECS, ParsedCommand, Parser
from .renderer import Renderer
from .search import SearchService
from .updater import Updater
from .utils import which
from .workflow import WorkflowService


@dataclass
class CommandContext:
    """Everything a command handler needs, injected once at construction."""

    config: object
    database: Database
    navigator: Navigator
    renderer: Renderer
    history: History
    executor: Executor
    installer: Installer
    updater: Updater
    search: SearchService
    workflow: WorkflowService
    parser: Parser
    version: str
    # UI callbacks supplied by the shell.
    confirm: Callable[[str], bool]
    reprint_banner: Callable[[], None]


class CommandDispatcher:
    """Routes parsed commands to their handlers."""

    def __init__(self, context: CommandContext) -> None:
        self.ctx = context
        self._logger = logging.getLogger("ptx")
        self._should_exit = False
        # Command name -> bound handler.
        self._handlers: dict[str, Callable[[ParsedCommand], None]] = {
            "help": self._cmd_help,
            "show": self._cmd_show,
            "methodology": self._cmd_methodology,
            "use": self._cmd_use,
            "search": self._cmd_search,
            "info": self._cmd_info,
            "examples": self._cmd_examples,
            "cheatsheet": self._cmd_cheatsheet,
            "workflow": self._cmd_workflow,
            "which": self._cmd_which,
            "run": self._cmd_run,
            "install": self._cmd_install,
            "update": self._cmd_update,
            "back": self._cmd_back,
            "home": self._cmd_home,
            "pwd": self._cmd_pwd,
            "history": self._cmd_history,
            "banner": self._cmd_banner,
            "clear": self._cmd_clear,
            "exit": self._cmd_exit,
        }

    @property
    def should_exit(self) -> bool:
        return self._should_exit

    # -- Entry point ----------------------------------------------------------
    def dispatch(self, parsed: ParsedCommand) -> None:
        """Execute the command described by ``parsed``."""
        if parsed.is_empty:
            return
        handler = self._handlers.get(parsed.name)
        if handler is None:
            self.ctx.renderer.error(
                f"Unknown command: {parsed.name!r}. Type 'help'."
            )
            return
        # Generic -h / --help handling for every command.
        if parsed.wants_help:
            spec = COMMAND_SPECS.get(parsed.name)
            if spec:
                self.ctx.renderer.command_help(spec)
                return
        try:
            handler(parsed)
        except NavigationError as exc:
            self.ctx.renderer.error(str(exc))
        except Exception as exc:  # noqa: BLE001 -- never let the shell die.
            self._logger.exception("Command %s failed", parsed.name)
            self.ctx.renderer.error(f"Internal error: {exc}")

    # -- Helpers --------------------------------------------------------------
    def _require_tool(self) -> Optional[Tool]:
        """Return the current tool, or emit an error if none is selected."""
        tool = self.ctx.navigator.tool
        if tool is None:
            self.ctx.renderer.error("Select a tool first (use <tool>).")
        return tool

    def _auto_view(self) -> None:
        """After a ``use``, auto-display the next level (per the spec)."""
        nav = self.ctx.navigator
        level = nav.level
        if level is Level.PATH and nav.path is not None:
            self.ctx.renderer.roadmap(nav.path)
        elif level is Level.PHASE and nav.path is not None and nav.phase is not None:
            tools = self.ctx.database.tools_for(nav.path, nav.phase)
            self.ctx.renderer.tools(nav.path, nav.phase, tools)
        elif level is Level.TOOL and nav.tool is not None:
            self.ctx.renderer.info(
                f"Now in {nav.tool.name}. Try: info, examples, cheatsheet, run, which."
            )

    # -- Handlers -------------------------------------------------------------
    def _cmd_help(self, parsed: ParsedCommand) -> None:
        if parsed.args:
            spec = self.ctx.parser.spec(parsed.args[0])
            if spec:
                self.ctx.renderer.command_help(spec)
            else:
                self.ctx.renderer.error(f"No such command: {parsed.args[0]!r}")
            return
        self.ctx.renderer.help_overview()

    def _cmd_show(self, parsed: ParsedCommand) -> None:
        target = parsed.args[0].lower() if parsed.args else self._default_show()
        nav = self.ctx.navigator
        if target in ("paths", "path"):
            rest = {a.lower().lstrip("-") for a in parsed.args[1:]}
            if rest & {"flat", "f", "list"}:
                self.ctx.renderer.paths(self.ctx.database.paths)
            else:
                self.ctx.renderer.paths_grouped(self.ctx.database.paths_by_group())
        elif target in ("methodology", "method", "spine"):
            self.ctx.renderer.methodology(self.ctx.database.methodology)
        elif target in ("roadmap", "phases"):
            if nav.path is None:
                self.ctx.renderer.error("Select a path first (use <path>).")
            else:
                self.ctx.renderer.roadmap(nav.path)
        elif target in ("tools", "tool"):
            if nav.path is None or nav.phase is None:
                self.ctx.renderer.error("Select a path and phase first.")
            else:
                tools = self.ctx.database.tools_for(nav.path, nav.phase)
                self.ctx.renderer.tools(nav.path, nav.phase, tools)
        else:
            self.ctx.renderer.error(
                "Usage: show <paths [--flat]|methodology|roadmap|tools>"
            )

    def _default_show(self) -> str:
        """Pick a sensible ``show`` target based on the current level."""
        level = self.ctx.navigator.level
        return {
            Level.ROOT: "paths",
            Level.PATH: "roadmap",
            Level.PHASE: "tools",
            Level.TOOL: "tools",
        }[level]

    def _cmd_methodology(self, parsed: ParsedCommand) -> None:
        """Show the universal PTES / kill-chain spine that underlies every path."""
        self.ctx.renderer.methodology(self.ctx.database.methodology)

    def _cmd_use(self, parsed: ParsedCommand) -> None:
        if not parsed.args:
            self.ctx.renderer.error("Usage: use <index|name>")
            return
        target = " ".join(parsed.args)
        self.ctx.navigator.use(target)
        self._auto_view()

    def _cmd_search(self, parsed: ParsedCommand) -> None:
        if not parsed.args:
            self.ctx.renderer.error("Usage: search <query>")
            return
        query = " ".join(parsed.args)
        results = self.ctx.search.query(query)
        self.ctx.renderer.search_results(results)

    def _cmd_info(self, _parsed: ParsedCommand) -> None:
        tool = self._require_tool()
        if tool:
            self.ctx.renderer.tool_info(tool, which(tool.binary))

    def _cmd_examples(self, _parsed: ParsedCommand) -> None:
        tool = self._require_tool()
        if tool:
            self.ctx.renderer.examples(tool)

    def _cmd_cheatsheet(self, _parsed: ParsedCommand) -> None:
        tool = self._require_tool()
        if tool:
            self.ctx.renderer.cheatsheet(tool)

    def _cmd_workflow(self, _parsed: ParsedCommand) -> None:
        path = self.ctx.navigator.path
        if path is None:
            self.ctx.renderer.error("Select a path first (use <path>).")
            return
        self.ctx.renderer.workflow(path)

    def _cmd_which(self, _parsed: ParsedCommand) -> None:
        tool = self._require_tool()
        if not tool:
            return
        location = which(tool.binary)
        if location:
            self.ctx.renderer.success(location)
        else:
            self.ctx.renderer.warning(f"{tool.binary} is not installed.")

    def _cmd_run(self, parsed: ParsedCommand) -> None:
        tool = self._require_tool()
        if not tool:
            return
        if not tool.installed:
            self.ctx.renderer.warning(f"{tool.name} is not installed.")
            self._offer_install(tool)
            return
        result = self.ctx.executor.run(tool, parsed.args)
        if not result.launched:
            self.ctx.renderer.error(result.reason)
        elif result.return_code not in (0, None):
            self.ctx.renderer.warning(
                f"{tool.binary} exited with code {result.return_code}."
            )

    def _cmd_install(self, _parsed: ParsedCommand) -> None:
        tool = self._require_tool()
        if not tool:
            return
        if tool.installed:
            self.ctx.renderer.success(f"{tool.name} is already installed.")
            return
        self._offer_install(tool)

    def _offer_install(self, tool: Tool) -> None:
        """Shared install-confirmation flow used by `install` and `run`."""
        plan = self.ctx.installer.plan(tool)
        self.ctx.renderer.warning("Tool not found.")
        self.ctx.renderer.info(f"Package: {tool.package or tool.binary}")
        if plan is None:
            self.ctx.renderer.warning(
                "No known install method for this host. See documentation:"
            )
            self.ctx.renderer.info(tool.documentation or tool.website or "n/a")
            return
        self.ctx.renderer.info(f"Method: {plan.manager} -> {plan.command}")
        if not self.ctx.confirm("Install?"):
            self.ctx.renderer.info("Aborted.")
            return
        outcome = self.ctx.installer.install(plan)
        if outcome.ok:
            tool.refresh_installed()
            self.ctx.renderer.success(outcome.message)
        else:
            self.ctx.renderer.error(outcome.message)

    def _cmd_update(self, _parsed: ParsedCommand) -> None:
        tool = self._require_tool()
        if not tool:
            return
        outcome = self.ctx.updater.update(tool)
        if outcome.ok:
            self.ctx.renderer.success(outcome.message)
        else:
            self.ctx.renderer.error(outcome.message)

    def _cmd_back(self, _parsed: ParsedCommand) -> None:
        self.ctx.navigator.back()
        self._auto_view()

    def _cmd_home(self, _parsed: ParsedCommand) -> None:
        self.ctx.navigator.home()
        self.ctx.renderer.paths_grouped(self.ctx.database.paths_by_group())

    def _cmd_pwd(self, _parsed: ParsedCommand) -> None:
        self.ctx.renderer.info(self.ctx.navigator.breadcrumb())

    def _cmd_history(self, parsed: ParsedCommand) -> None:
        count: int | None = None
        if parsed.args and parsed.args[0].isdigit():
            count = int(parsed.args[0])
        items = self.ctx.history.recent(count)
        if not items:
            self.ctx.renderer.info("No history yet.")
            return
        offset = len(self.ctx.history) - len(items)
        for i, cmd in enumerate(items, start=offset + 1):
            self.ctx.renderer.info(f"{i:>4}  {cmd}")

    def _cmd_banner(self, _parsed: ParsedCommand) -> None:
        self.ctx.reprint_banner()

    def _cmd_clear(self, _parsed: ParsedCommand) -> None:
        os.system("cls" if os.name == "nt" else "clear")  # noqa: S605,S607

    def _cmd_exit(self, _parsed: ParsedCommand) -> None:
        self._should_exit = True
