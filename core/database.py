"""
core/database.py
================

The knowledge base.

This module defines the immutable data model (:class:`PathEntry`,
:class:`Phase`, :class:`Tool`) and the :class:`Database` loader that builds it
*entirely from files on disk*. No tool, phase, or path is ever hardcoded in
Python -- everything comes from:

    database/paths.json       -> the 12 top-level testing paths
    database/workflows.json   -> the ordered roadmap (phases) for each path
    database/aliases.json     -> extra global aliases
    database/<path>/*.yaml    -> individual tool definitions

To add a tool you drop a YAML file in the right folder; to add a whole path you
add an entry to paths.json and a roadmap to workflows.json. The framework picks
it up automatically on next launch.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from .utils import fuzzy_score, is_installed, slugify, unique


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Phase:
    """A single step in a path's roadmap (e.g. 'Reconnaissance')."""

    index: int
    name: str
    slug: str
    description: str = ""


@dataclass(frozen=True)
class PathEntry:
    """A top-level testing path (e.g. 'Network Penetration Testing')."""

    index: int
    name: str
    slug: str
    folder: str
    description: str = ""
    group: str = ""
    roadmap: tuple[Phase, ...] = ()

    def phase_by_key(self, key: str) -> Optional[Phase]:
        """Resolve a phase by index (``"0"``), name, or slug."""
        key = key.strip()
        if key.isdigit():
            idx = int(key)
            for phase in self.roadmap:
                if phase.index == idx:
                    return phase
            return None
        wanted = slugify(key)
        for phase in self.roadmap:
            if phase.slug == wanted or phase.name.lower() == key.lower():
                return phase
        return None


@dataclass
class Tool:
    """A single tool definition loaded from a YAML file.

    Mutable only so :meth:`refresh_installed` can update the cached
    installation state; all list/dict fields default via ``field`` factories to
    avoid the classic shared-mutable-default bug.
    """

    name: str
    binary: str
    package: str
    description: str
    path_slug: str
    phase_slugs: tuple[str, ...]
    category: str = ""
    difficulty: str = "Unknown"
    platform: str = "Linux"
    recommended: bool = False
    note: str = ""
    purpose: str = ""
    author: str = ""
    license: str = ""
    website: str = ""
    documentation: str = ""
    aliases: list[str] = field(default_factory=list)
    installation: dict[str, str] = field(default_factory=dict)
    examples: list[dict[str, str]] = field(default_factory=list)
    cheatsheet: list[dict[str, str]] = field(default_factory=list)
    related_tools: list[str] = field(default_factory=list)
    source_file: Optional[Path] = None
    _installed: Optional[bool] = None

    @property
    def slug(self) -> str:
        return slugify(self.name)

    @property
    def installed(self) -> bool:
        """Whether the tool's binary is on PATH (cached after first check)."""
        if self._installed is None:
            self._installed = is_installed(self.binary)
        return self._installed

    def refresh_installed(self) -> bool:
        """Force a re-check of installation state (e.g. after an install)."""
        self._installed = is_installed(self.binary)
        return self._installed

    def search_haystack(self) -> str:
        """Flattened text used for fuzzy search matching."""
        parts = [self.name, self.binary, self.description, self.category]
        parts.extend(self.aliases)
        return " ".join(parts)

    @classmethod
    def from_yaml(
        cls, data: dict, path_slug: str, folder: str, source: Path
    ) -> "Tool":
        """Build a :class:`Tool` from a parsed YAML mapping.

        Missing optional keys fall back to sensible defaults so a minimal YAML
        file (just name / binary / package / description) is still valid.
        """
        phases = data.get("phases") or data.get("phase") or []
        if isinstance(phases, str):
            phases = [phases]
        phase_slugs = tuple(slugify(p) for p in phases)

        return cls(
            name=str(data.get("name", "")).strip(),
            binary=str(data.get("binary", "")).strip(),
            package=str(data.get("package", "")).strip(),
            description=str(data.get("description", "")).strip(),
            path_slug=path_slug,
            phase_slugs=phase_slugs,
            category=str(data.get("category", folder)).strip(),
            difficulty=str(data.get("difficulty", "Unknown")).strip(),
            platform=str(data.get("platform", "Linux")).strip(),
            recommended=bool(data.get("recommended", False)),
            note=str(data.get("note", "")).strip(),
            purpose=str(data.get("purpose", "")).strip(),
            author=str(data.get("author", "")).strip(),
            license=str(data.get("license", "")).strip(),
            website=str(data.get("website", "")).strip(),
            documentation=str(data.get("documentation", "")).strip(),
            aliases=[str(a).strip() for a in (data.get("aliases") or [])],
            installation=dict(data.get("installation") or {}),
            examples=list(data.get("examples") or []),
            cheatsheet=list(data.get("cheatsheet") or []),
            related_tools=[str(r).strip() for r in (data.get("related_tools") or [])],
            source_file=source,
        )


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------
class DatabaseError(Exception):
    """Raised when the knowledge base cannot be loaded."""


class Database:
    """Loads and indexes the entire on-disk knowledge base.

    Instantiate once at startup, call :meth:`load`, then query via the public
    accessor methods. All heavy file work happens in :meth:`load` so the shell
    stays responsive afterwards.
    """

    def __init__(self, config) -> None:  # noqa: ANN001 (avoid import cycle)
        self._config = config
        self._paths: list[PathEntry] = []
        self._tools: list[Tool] = []
        self._global_aliases: dict[str, str] = {}
        self._methodology: list[dict[str, str]] = []
        self._logger = None

    # -- Loading --------------------------------------------------------------
    def load(self) -> None:
        """Read every database file and build the in-memory index."""
        import logging

        self._logger = logging.getLogger("ptx")
        roadmaps = self._load_workflows()
        self._paths = self._load_paths(roadmaps)
        self._global_aliases = self._load_aliases()
        self._methodology = self._load_methodology()
        self._tools = self._load_tools()
        self._logger.info(
            "Loaded %d paths and %d tools", len(self._paths), len(self._tools)
        )

    def _read_json(self, file: Path) -> dict | list:
        if not file.exists():
            raise DatabaseError(f"Required database file missing: {file}")
        try:
            with file.open(encoding="utf-8") as handle:
                return json.load(handle)
        except json.JSONDecodeError as exc:
            raise DatabaseError(f"Invalid JSON in {file}: {exc}") from exc

    def _load_workflows(self) -> dict[str, list[dict]]:
        data = self._read_json(self._config.workflows_db_file())
        if not isinstance(data, dict):
            raise DatabaseError("workflows.json must be a JSON object")
        return data  # type: ignore[return-value]

    def _load_paths(self, roadmaps: dict) -> list[PathEntry]:
        raw = self._read_json(self._config.path_db_file())
        if not isinstance(raw, list):
            raise DatabaseError("paths.json must be a JSON array")

        paths: list[PathEntry] = []
        for index, item in enumerate(raw):
            name = str(item["name"]).strip()
            slug = slugify(name)
            folder = str(item.get("folder", slug.replace("-", "_")))
            phases_raw = roadmaps.get(slug, roadmaps.get(folder, []))
            phases = tuple(
                Phase(
                    index=i,
                    name=str(p["name"]).strip(),
                    slug=slugify(str(p["name"])),
                    description=str(p.get("description", "")).strip(),
                )
                for i, p in enumerate(phases_raw)
            )
            paths.append(
                PathEntry(
                    index=index,
                    name=name,
                    slug=slug,
                    folder=folder,
                    description=str(item.get("description", "")).strip(),
                    group=str(item.get("group", "")).strip(),
                    roadmap=phases,
                )
            )
        return paths

    def _load_aliases(self) -> dict[str, str]:
        file = self._config.aliases_db_file()
        if not file.exists():
            return {}
        data = self._read_json(file)
        if not isinstance(data, dict):
            raise DatabaseError("aliases.json must be a JSON object")
        return {str(k).lower(): str(v) for k, v in data.items()}

    def _load_methodology(self) -> list[dict[str, str]]:
        file = self._config.database_dir / "methodology.json"
        if not file.exists():
            return []
        data = self._read_json(file)
        return data if isinstance(data, list) else []

    def _load_tools(self) -> list[Tool]:
        tools: list[Tool] = []
        for path in self._paths:
            folder_dir = self._config.database_dir / path.folder
            if not folder_dir.is_dir():
                continue
            for yaml_file in sorted(folder_dir.glob("*.y*ml")):
                tool = self._load_tool_file(yaml_file, path)
                if tool is not None:
                    tools.append(tool)
        return tools

    def _load_tool_file(self, yaml_file: Path, path: PathEntry) -> Optional[Tool]:
        try:
            with yaml_file.open(encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
        except yaml.YAMLError as exc:
            if self._logger:
                self._logger.error("Bad YAML %s: %s", yaml_file, exc)
            return None
        if not isinstance(data, dict) or not data.get("name"):
            if self._logger:
                self._logger.error("Skipping malformed tool file %s", yaml_file)
            return None
        return Tool.from_yaml(data, path.slug, path.folder, yaml_file)

    # -- Accessors ------------------------------------------------------------
    @property
    def paths(self) -> list[PathEntry]:
        return list(self._paths)

    @property
    def tools(self) -> list[Tool]:
        return list(self._tools)

    @property
    def methodology(self) -> list[dict[str, str]]:
        return list(self._methodology)

    def paths_by_group(self) -> dict[str, list[PathEntry]]:
        """Return paths bucketed by their group, preserving first-seen order."""
        grouped: dict[str, list[PathEntry]] = {}
        for path in self._paths:
            grouped.setdefault(path.group or "Other", []).append(path)
        return grouped

    def expand_alias(self, key: str) -> str:
        """Expand a global alias (from aliases.json) to its canonical target.

        Returns ``key`` unchanged when no alias matches. Used by the navigator
        so ``use web``, ``use recon``, ``use privesc`` etc. resolve to the full
        path / phase name.
        """
        return self._global_aliases.get(key.strip().lower(), key)

    def resolve_path(self, key: str) -> Optional[PathEntry]:
        """Resolve a path by index (``"0"``), exact name, or slug."""
        key = key.strip()
        if key.isdigit():
            idx = int(key)
            for path in self._paths:
                if path.index == idx:
                    return path
            return None
        wanted = slugify(key)
        for path in self._paths:
            if path.slug == wanted or path.name.lower() == key.lower():
                return path
        return None

    def tools_for(self, path: PathEntry, phase: Phase) -> list[Tool]:
        """All tools tagged for a given path + roadmap phase."""
        return [
            tool
            for tool in self._tools
            if tool.path_slug == path.slug and phase.slug in tool.phase_slugs
        ]

    def resolve_tool(
        self,
        key: str,
        path: Optional[PathEntry] = None,
        phase: Optional[Phase] = None,
    ) -> Optional[Tool]:
        """Resolve a tool by index, name, binary, or alias.

        When ``path`` and ``phase`` are provided the numeric index is
        interpreted relative to that filtered list (matching what the user
        sees in the Level 3 table); otherwise the search is global.
        """
        key = key.strip()
        scope = (
            self.tools_for(path, phase)
            if path is not None and phase is not None
            else self._tools
        )
        if key.isdigit():
            idx = int(key)
            if 0 <= idx < len(scope):
                return scope[idx]
            return None
        lowered = key.lower()
        for tool in scope:
            if (
                tool.name.lower() == lowered
                or tool.binary.lower() == lowered
                or tool.slug == slugify(key)
                or lowered in (a.lower() for a in tool.aliases)
            ):
                return tool
        return None

    def search(self, query: str, limit: int = 25) -> list[tuple[Tool, float]]:
        """Fuzzy-search every tool, returning (tool, score) sorted best-first."""
        query = query.strip()
        if not query:
            return []
        scored: list[tuple[Tool, float]] = []
        for tool in self._tools:
            score = fuzzy_score(query, tool.search_haystack())
            # Also try the plain name / aliases for stronger direct hits.
            score = max(score, fuzzy_score(query, tool.name))
            for alias in tool.aliases:
                score = max(score, fuzzy_score(query, alias))
            if score > 0:
                scored.append((tool, score))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:limit]

    def related_names(self, tool: Tool) -> list[str]:
        """Return de-duplicated related-tool display names."""
        return unique(tool.related_tools)
