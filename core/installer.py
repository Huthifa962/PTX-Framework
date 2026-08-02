"""
core/installer.py
=================

Package-manager aware installation of tools.

Each tool's YAML declares an ``installation`` mapping of
``manager -> command``, e.g.::

    installation:
      apt: "sudo apt install -y nmap"
      brew: "brew install nmap"

The installer picks the first manager that is actually available on the host
(``apt``, ``snap``, ``pip``, ``pipx``, ``go``, ``cargo``, ``git``, ``brew``)
and runs its command. If no known method is available it hands back the tool's
documentation so the operator can install manually.

The installer never guesses install commands and never runs anything without
the command layer having confirmed with the user first.
"""

from __future__ import annotations

import logging
import shlex
import subprocess
from dataclasses import dataclass

from .database import Tool
from .utils import which

# Preference order: system package managers first, language managers next,
# source build last. Reflects the spec's supported managers.
_MANAGER_PRIORITY: tuple[str, ...] = (
    "apt",
    "brew",
    "snap",
    "pipx",
    "pip",
    "go",
    "cargo",
    "git",
)

# The executable that must exist for a given manager key to be usable.
_MANAGER_BINARY: dict[str, str] = {
    "apt": "apt",
    "brew": "brew",
    "snap": "snap",
    "pipx": "pipx",
    "pip": "pip",
    "go": "go",
    "cargo": "cargo",
    "git": "git",
}


@dataclass
class InstallPlan:
    """A chosen installation strategy for a tool."""

    manager: str
    command: str


@dataclass
class InstallOutcome:
    """Result of an installation attempt."""

    ok: bool
    manager: str = ""
    message: str = ""


class Installer:
    """Chooses and runs the appropriate install command for a tool."""

    def __init__(self) -> None:
        self._logger = logging.getLogger("ptx")

    def plan(self, tool: Tool) -> InstallPlan | None:
        """Pick the best available install method for ``tool``.

        Returns ``None`` when the tool declares no method we can satisfy on this
        host, signalling the caller to show documentation instead.
        """
        available = tool.installation
        if not available:
            return None
        for manager in _MANAGER_PRIORITY:
            if manager in available:
                probe = _MANAGER_BINARY.get(manager, manager)
                if which(probe) is not None:
                    return InstallPlan(manager=manager, command=available[manager])
        # Declared methods exist but none are installable here.
        return None

    def install(self, plan: InstallPlan) -> InstallOutcome:
        """Run the install command from ``plan``.

        The command string comes from the tool's own YAML; we split it with
        :func:`shlex.split` and run without a shell to avoid injection.
        """
        self._logger.info("Installing via %s: %s", plan.manager, plan.command)
        try:
            args = shlex.split(plan.command)
        except ValueError:
            return InstallOutcome(ok=False, message="Malformed install command.")
        if not args:
            return InstallOutcome(ok=False, message="Empty install command.")
        try:
            completed = subprocess.run(args, check=False)  # noqa: S603
        except FileNotFoundError:
            return InstallOutcome(
                ok=False,
                manager=plan.manager,
                message=f"{args[0]} not found on PATH.",
            )
        except OSError as exc:
            return InstallOutcome(ok=False, manager=plan.manager, message=str(exc))

        if completed.returncode == 0:
            return InstallOutcome(ok=True, manager=plan.manager,
                                  message="Installation completed.")
        return InstallOutcome(
            ok=False,
            manager=plan.manager,
            message=f"Installer exited with code {completed.returncode}.",
        )
