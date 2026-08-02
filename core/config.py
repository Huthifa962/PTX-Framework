"""
core/config.py
==============

Runtime configuration for PTX.

Responsibilities
----------------
* Resolve the important filesystem locations relative to the project root so
  the framework works regardless of the current working directory.
* Expose a single :class:`Config` object other modules read from.
* Load / merge an optional user config file (``config/ptx.toml``) in the
  future -- the loader is stubbed here so the rest of the code already depends
  on the abstraction (future-ready, per the spec).

Nothing here is hardcoded knowledge-base data; this module only knows about
*where* things live, not *what* tools exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


# The project root is two levels up from this file: core/config.py -> PTX/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Config:
    """Central configuration object.

    All paths are absolute :class:`~pathlib.Path` instances derived from the
    project root, which keeps PTX portable across machines and shells.
    """

    root: Path = _PROJECT_ROOT
    database_dir: Path = field(init=False)
    templates_dir: Path = field(init=False)
    docs_dir: Path = field(init=False)
    logs_dir: Path = field(init=False)
    cache_dir: Path = field(init=False)
    config_dir: Path = field(init=False)

    # File names used inside database_dir.
    paths_file: str = "paths.json"
    aliases_file: str = "aliases.json"
    workflows_file: str = "workflows.json"

    # Behavior toggles (future config file can override these).
    history_size: int = 1000
    confirm_install: bool = True

    def __post_init__(self) -> None:
        self.database_dir = self.root / "database"
        self.templates_dir = self.root / "templates"
        self.docs_dir = self.root / "docs"
        self.logs_dir = self.root / "logs"
        self.cache_dir = self.root / "cache"
        self.config_dir = self.root / "config"
        self._ensure_writable_dirs()

    def _ensure_writable_dirs(self) -> None:
        """Create the directories PTX writes to if they are missing."""
        for directory in (self.logs_dir, self.cache_dir, self.config_dir):
            directory.mkdir(parents=True, exist_ok=True)

    # -- Convenience accessors ------------------------------------------------
    @property
    def history_file(self) -> Path:
        """Path to the persistent command-history file."""
        return self.cache_dir / "history"

    @property
    def log_file(self) -> Path:
        """Path to the rotating application log."""
        return self.logs_dir / "ptx.log"

    def path_db_file(self) -> Path:
        return self.database_dir / self.paths_file

    def aliases_db_file(self) -> Path:
        return self.database_dir / self.aliases_file

    def workflows_db_file(self) -> Path:
        return self.database_dir / self.workflows_file
