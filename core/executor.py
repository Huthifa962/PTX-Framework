"""
core/executor.py
================

Launches the selected tool's real binary with user-supplied arguments.

PTX is a *launcher and reference*, not an attack engine: this module never
fabricates payloads or targets. It simply forwards the arguments the operator
typed after ``run`` to the tool binary that is already installed on their
system -- exactly as if they had typed the command themselves, but from within
the framework's workflow.

Safety notes
------------
* We call the binary directly with an argument *list* (``shell=False``) so the
  operator's arguments are never re-interpreted by a shell. No string
  concatenation into ``sh -c``.
* If the binary is not installed we refuse to run and hand the caller back a
  clear result so the command layer can offer to install it.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass

from .database import Tool
from .utils import which


@dataclass
class RunResult:
    """Outcome of a :meth:`Executor.run` call."""

    launched: bool
    return_code: int | None = None
    reason: str = ""


class Executor:
    """Runs installed tool binaries safely."""

    def __init__(self) -> None:
        self._logger = logging.getLogger("ptx")

    def run(self, tool: Tool, args: list[str]) -> RunResult:
        """Execute ``tool``'s binary with ``args``.

        Returns a :class:`RunResult`; does not raise on a non-zero tool exit
        (that is normal for many security tools) but does report if the binary
        is missing so the caller can prompt for installation.
        """
        binary_path = which(tool.binary)
        if binary_path is None:
            self._logger.info("run refused: %s not installed", tool.binary)
            return RunResult(
                launched=False,
                reason=f"{tool.binary} is not installed.",
            )

        command = [binary_path, *args]
        self._logger.info("Executing: %s", " ".join(command))
        try:
            completed = subprocess.run(command, check=False)  # noqa: S603
        except FileNotFoundError:
            return RunResult(launched=False, reason="Binary disappeared before launch.")
        except KeyboardInterrupt:
            # Let the user Ctrl-C a long scan without killing PTX itself.
            return RunResult(launched=True, return_code=130, reason="Interrupted.")
        except OSError as exc:
            self._logger.error("Execution failed: %s", exc)
            return RunResult(launched=False, reason=f"Could not launch: {exc}")

        return RunResult(launched=True, return_code=completed.returncode)
