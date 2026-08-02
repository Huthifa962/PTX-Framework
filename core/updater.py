"""
core/updater.py
===============

Updates an already-installed tool.

Reuses the same package-manager resolution as the installer but prefers an
``update`` command when the tool's YAML provides one under its ``installation``
mapping (e.g. ``apt_update``). If none is provided it falls back to re-running
the normal install command, which for most managers upgrades in place.
"""

from __future__ import annotations

import logging

from .database import Tool
from .installer import InstallOutcome, InstallPlan, Installer


class Updater:
    """Thin wrapper over :class:`Installer` specialized for upgrades."""

    def __init__(self, installer: Installer | None = None) -> None:
        self._installer = installer or Installer()
        self._logger = logging.getLogger("ptx")

    def update(self, tool: Tool) -> InstallOutcome:
        """Update ``tool`` using the best available strategy."""
        # Look for an explicit *_update entry first (e.g. "apt_update").
        for key, command in tool.installation.items():
            if key.endswith("_update"):
                manager = key.removesuffix("_update")
                self._logger.info("Updating %s via %s", tool.name, manager)
                return self._installer.install(
                    InstallPlan(manager=manager, command=command)
                )
        # Otherwise re-run the standard install (upgrades in place for apt/brew).
        plan = self._installer.plan(tool)
        if plan is None:
            return InstallOutcome(
                ok=False,
                message="No known update method; see documentation.",
            )
        return self._installer.install(plan)
