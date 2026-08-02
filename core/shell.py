"""
core/shell.py
=============

The interactive REPL.

Wraps the read-eval-print loop around the :class:`CommandDispatcher`. It owns:

* the dynamic, context-aware prompt (``ptx(Network.../Recon/nmap)>``)
* line editing, persistent history, and fuzzy auto-completion via
  prompt_toolkit -- when a real terminal is attached
* a graceful fallback to plain :func:`input` when stdin is not a TTY (piped
  input, CI, or environments without prompt_toolkit), so PTX is scriptable and
  testable

The shell contains no domain logic; it reads a line, hands it to the parser and
dispatcher, and repeats.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

from .colors import PALETTE
from .commands import CommandDispatcher
from .history import History
from .navigator import Level
from .parser import COMMAND_SPECS, Parser

# prompt_toolkit is optional at import time so PTX still runs (in fallback mode)
# where it is unavailable.
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import FuzzyCompleter, NestedCompleter
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.history import FileHistory

    _PTK_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    _PTK_AVAILABLE = False


class Shell:
    """Read-eval-print loop driving the dispatcher."""

    def __init__(
        self,
        dispatcher: CommandDispatcher,
        parser: Parser,
        history: History,
        history_file,
    ) -> None:
        self._dispatcher = dispatcher
        self._parser = parser
        self._history = history
        self._history_file = history_file
        self._logger = logging.getLogger("ptx")
        self._session: Optional["PromptSession"] = None
        self._interactive = sys.stdin.isatty() and _PTK_AVAILABLE
        if self._interactive:
            self._session = self._build_session()

    # -- Setup ----------------------------------------------------------------
    def _build_session(self) -> "PromptSession":
        """Construct the prompt_toolkit session with completion + history."""
        return PromptSession(
            history=FileHistory(str(self._history_file)),
            completer=FuzzyCompleter(self._build_completer()),
            complete_while_typing=True,
        )

    def _build_completer(self) -> "NestedCompleter":
        """Build a nested completer for commands and their sub-words.

        Kept simple: top-level commands plus ``show`` sub-targets. Dynamic
        completion of tool/path names could be layered on later; the structure
        is here so that is a small change, not a rewrite.
        """
        show_targets = {"paths": None, "methodology": None, "roadmap": None, "tools": None}
        mapping: dict[str, object] = {name: None for name in COMMAND_SPECS}
        mapping["show"] = show_targets
        mapping["help"] = {name: None for name in COMMAND_SPECS}
        return NestedCompleter.from_nested_dict(mapping)

    # -- Prompt ---------------------------------------------------------------
    def _prompt_text(self) -> str:
        """Compose the ``ptx(context)>`` prompt string for the current level."""
        context = self._dispatcher.ctx.navigator.prompt_context()
        return f"ptx({context})> " if context else "ptx> "

    def _prompt_html(self):
        """Colorized prompt for prompt_toolkit."""
        nav = self._dispatcher.ctx.navigator
        context = nav.prompt_context()
        if context:
            return HTML(
                f"<ansired><b>ptx</b></ansired>"
                f"(<ansibrightred>{_escape(context)}</ansibrightred>)"
                f"<ansired><b>&gt; </b></ansired>"
            )
        return HTML("<ansired><b>ptx&gt; </b></ansired>")

    # -- Confirmation (install prompts) ---------------------------------------
    def confirm(self, question: str) -> bool:
        """Ask a ``[Y/n]`` question and return the boolean answer.

        Defaults to Yes on an empty response, matching the spec's ``[Y/n]``.
        In non-interactive mode we decline, so scripted runs never block or
        trigger installs unexpectedly.
        """
        if not self._interactive:
            self._logger.info("Auto-declining '%s' in non-interactive mode.", question)
            return False
        try:
            answer = input(f"{question} [Y/n] ").strip().lower()
        except EOFError:
            return False
        return answer in ("", "y", "yes")

    # -- Main loop ------------------------------------------------------------
    def read_line(self) -> Optional[str]:
        """Read one input line, returning ``None`` on EOF."""
        try:
            if self._interactive and self._session is not None:
                return self._session.prompt(self._prompt_html())
            # Fallback: plain prompt (also used for piped / scripted input).
            line = input(self._prompt_text())
            # Echo in non-interactive mode so transcripts are readable.
            if not sys.stdin.isatty():
                print(line)
            return line
        except EOFError:
            return None
        except KeyboardInterrupt:
            # Ctrl-C at the prompt clears the line rather than exiting.
            print()
            return ""

    def run(self) -> None:
        """Run the REPL until ``exit`` or EOF."""
        while not self._dispatcher.should_exit:
            line = self.read_line()
            if line is None:  # EOF -> quit cleanly.
                break
            line = line.strip()
            if not line:
                continue
            self._history.add(line)
            parsed = self._parser.parse(line)
            self._dispatcher.dispatch(parsed)
        self._dispatcher.ctx.renderer.info("Goodbye.")


def _escape(text: str) -> str:
    """Minimal HTML escape for prompt_toolkit's HTML formatter."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
