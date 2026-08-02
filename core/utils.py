"""
core/utils.py
=============

Small, dependency-light helpers shared across the framework. Anything that does
not belong to a single subsystem but is broadly useful lives here. Kept
deliberately tiny to avoid becoming a dumping ground.
"""

from __future__ import annotations

import logging
import re
import shutil
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Iterable, Optional

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Normalize a display name into a lookup-friendly slug.

    ``"Network Penetration Testing"`` -> ``"network-penetration-testing"``.
    Used so that ``use 0``, ``use network``, and
    ``use "Network Penetration Testing"`` can all resolve to one record.
    """
    value = value.strip().lower()
    value = _SLUG_RE.sub("-", value)
    return value.strip("-")


def which(binary: str) -> Optional[str]:
    """Return the absolute path of ``binary`` on PATH, or ``None`` if absent.

    Thin wrapper around :func:`shutil.which` so the rest of the code depends on
    our abstraction and can be mocked in tests.
    """
    if not binary:
        return None
    return shutil.which(binary)


def is_installed(binary: str) -> bool:
    """Boolean convenience wrapper around :func:`which`."""
    return which(binary) is not None


def fuzzy_score(needle: str, haystack: str) -> float:
    """Very small, dependency-free fuzzy match score in the range [0, 1].

    Returns 1.0 for an exact (case-insensitive) match, a high score for a
    substring match, and a subsequence-based score otherwise. Good enough for
    ranking search results without pulling in a heavy dependency; the shell's
    completer uses prompt_toolkit's own fuzzy matcher separately.
    """
    needle = needle.lower().strip()
    haystack = haystack.lower().strip()
    if not needle:
        return 0.0
    if needle == haystack:
        return 1.0
    if needle in haystack:
        # Reward shorter haystacks (more specific matches) slightly.
        return 0.9 * (len(needle) / len(haystack))

    # Subsequence check: are all needle chars present in order?
    it = iter(haystack)
    matched = sum(1 for ch in needle if ch in it)
    if matched < len(needle):
        return 0.0
    return 0.5 * (matched / len(haystack))


def truncate(text: str, width: int) -> str:
    """Truncate ``text`` to ``width`` characters with an ellipsis."""
    if len(text) <= width:
        return text
    if width <= 1:
        return text[:width]
    return text[: width - 1] + "…"


def unique(items: Iterable[str]) -> list[str]:
    """Return ``items`` de-duplicated while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def setup_logging(log_file: Path, level: int = logging.INFO) -> logging.Logger:
    """Configure and return the shared PTX logger.

    Uses a rotating file handler so ``logs/ptx.log`` never grows unbounded.
    Console output is intentionally NOT attached here -- user-facing messages
    go through the Rich renderer, not the logger.
    """
    logger = logging.getLogger("ptx")
    if logger.handlers:  # Already configured (idempotent).
        return logger

    logger.setLevel(level)
    handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger
