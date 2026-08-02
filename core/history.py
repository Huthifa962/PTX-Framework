"""
core/history.py
===============

Persistent command history.

Keeps an in-memory ring of recent commands for the ``history`` command and
mirrors it to disk so history survives restarts. prompt_toolkit maintains its
own FileHistory for line editing (up-arrow recall); this class is the
*application-level* record used by the ``history`` command and logging.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Deque


class History:
    """Bounded, persisted command history."""

    def __init__(self, file: Path, max_size: int = 1000) -> None:
        self._file = file
        self._max_size = max_size
        self._items: Deque[str] = deque(maxlen=max_size)
        self._load()

    def _load(self) -> None:
        """Populate the ring from the on-disk file if it exists."""
        if not self._file.exists():
            return
        try:
            lines = self._file.read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        for line in lines[-self._max_size :]:
            if line.strip():
                self._items.append(line)

    def add(self, command: str) -> None:
        """Record a command and append it to the on-disk history."""
        command = command.strip()
        if not command:
            return
        # Skip consecutive duplicates for a cleaner history.
        if self._items and self._items[-1] == command:
            return
        self._items.append(command)
        try:
            with self._file.open("a", encoding="utf-8") as handle:
                handle.write(command + "\n")
        except OSError:
            pass  # History is best-effort; never crash the shell over it.

    def recent(self, count: int | None = None) -> list[str]:
        """Return the most recent ``count`` commands (all if ``None``)."""
        items = list(self._items)
        if count is None:
            return items
        return items[-count:]

    def __len__(self) -> int:
        return len(self._items)
