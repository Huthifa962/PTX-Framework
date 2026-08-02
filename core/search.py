"""
core/search.py
==============

Search service.

A deliberately thin façade over :meth:`Database.search`. Keeping search behind
its own module means the ranking algorithm can grow (weighting installed tools,
boosting exact alias hits, adding category filters) without any command-layer
changes. The actual fuzzy scoring lives in ``utils.fuzzy_score`` /
``database.search`` today.
"""

from __future__ import annotations

from .database import Database, Tool


class SearchService:
    """Encapsulates search queries against the knowledge base."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def query(self, text: str, limit: int = 25) -> list[tuple[Tool, float]]:
        """Return ranked ``(tool, score)`` results for ``text``."""
        return self._db.search(text, limit=limit)
