"""
core/cli.py
===========

Application composition root.

:class:`Application` wires every subsystem together (dependency injection by
hand -- no framework needed) and exposes a single :meth:`run` method. Keeping
construction in one place makes the data flow obvious and the pieces easy to
swap or test in isolation.
"""

from __future__ import annotations

import logging

from rich.console import Console

from . import __version__
from .banner import render_banner
from .commands import CommandContext, CommandDispatcher
from .config import Config
from .database import Database, DatabaseError
from .executor import Executor
from .history import History
from .installer import Installer
from .navigator import Navigator
from .parser import Parser
from .renderer import Renderer
from .search import SearchService
from .shell import Shell
from .updater import Updater
from .utils import setup_logging
from .workflow import WorkflowService


class Application:
    """The composed PTX application."""

    def __init__(self) -> None:
        self.config = Config()
        self.logger = setup_logging(self.config.log_file)
        self.console = Console()
        self.renderer = Renderer(self.console)
        self.parser = Parser()
        self.database = Database(self.config)

    def _bootstrap(self) -> bool:
        """Load the knowledge base. Returns False on fatal load error."""
        try:
            self.database.load()
        except DatabaseError as exc:
            self.renderer.error(f"Failed to load knowledge base: {exc}")
            self.logger.error("Bootstrap failed: %s", exc)
            return False
        return True

    def run(self) -> int:
        """Start PTX. Returns a process exit code."""
        self.logger.info("Starting PTX %s", __version__)
        render_banner(self.console, __version__)

        if not self._bootstrap():
            return 1

        navigator = Navigator(self.database)
        history = History(self.config.history_file, self.config.history_size)
        installer = Installer()
        dispatcher_holder: dict[str, CommandDispatcher] = {}

        # The shell must exist before the dispatcher (for callbacks) but the
        # dispatcher must exist before the shell (to drive it). We break the
        # cycle by building the context with lazy callbacks.
        context = CommandContext(
            config=self.config,
            database=self.database,
            navigator=navigator,
            renderer=self.renderer,
            history=history,
            executor=Executor(),
            installer=installer,
            updater=Updater(installer),
            search=SearchService(self.database),
            workflow=WorkflowService(),
            parser=self.parser,
            version=__version__,
            confirm=lambda q: shell.confirm(q),
            reprint_banner=lambda: render_banner(self.console, __version__),
        )
        dispatcher = CommandDispatcher(context)
        dispatcher_holder["d"] = dispatcher

        shell = Shell(dispatcher, self.parser, history, self.config.history_file)

        # Show the top-level paths immediately so the user has a starting point.
        self.renderer.blank()
        self.renderer.paths_grouped(self.database.paths_by_group())
        self.renderer.blank()

        try:
            shell.run()
        except Exception:  # noqa: BLE001
            self.logger.exception("Unhandled error in shell loop")
            self.renderer.error("A fatal error occurred; see logs/ptx.log.")
            return 1
        return 0
