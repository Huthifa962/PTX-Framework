"""
core/workflow.py
================

Workflow service.

Resolves the roadmap (ordered phases) for a path and exposes it for the
renderer to draw as a diagram. Split from the renderer so the *logic* of what a
workflow contains is separate from *how* it is drawn -- a future export-to-
Markdown or Mermaid feature would live here, not in the UI layer.
"""

from __future__ import annotations

from .database import PathEntry, Phase


class WorkflowService:
    """Provides roadmap data for a path."""

    def phases(self, path: PathEntry) -> tuple[Phase, ...]:
        """Return the ordered phases that make up ``path``'s roadmap."""
        return path.roadmap

    def as_text_chain(self, path: PathEntry) -> str:
        """Render the roadmap as a plain-text vertical chain.

        Handy for logs, exports, or non-Rich environments.
        """
        if not path.roadmap:
            return f"{path.name}: (no roadmap defined)"
        lines: list[str] = []
        for i, phase in enumerate(path.roadmap):
            lines.append(phase.name)
            if i < len(path.roadmap) - 1:
                lines.append("  ↓")
        return "\n".join(lines)
