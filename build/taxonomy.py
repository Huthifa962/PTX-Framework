"""
build/taxonomy.py
=================

The single source of truth for PTX's knowledge base *structure*, transcribed
from the consolidated pentesting-domain map. `generate.py` reads this module and
emits database/paths.json, database/workflows.json, and every tool YAML.

This is a build-time artifact: editing here + re-running the generator rebuilds
the whole database. It is NOT imported by the running framework.

Design choices
--------------
* Domains are grouped (Cross-cutting / Core / Application / Infrastructure /
  Hardware / Emerging) so the dashboard can present them the way the map does.
* Every tool carries the phase(s) it is most used in, matching the universal
  methodology spine, because many tools span domains and phases.
* PTX is a launcher/reference. Tool entries carry metadata + official docs.
  Offensive-tradecraft tools (C2, evasion, MFA-phishing, relay/coercion) are
  catalogued for reference and point to official documentation rather than
  shipping operational recipes.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# The universal methodology spine (PTES / kill-chain). Shown by `methodology`.
# ---------------------------------------------------------------------------
METHODOLOGY: list[dict[str, str]] = [
    {"name": "Pre-engagement", "description": "Scope, rules of engagement, authorization, goals."},
    {"name": "Reconnaissance", "description": "Passive (OSINT, no touch) then active discovery."},
    {"name": "Scanning & Enumeration", "description": "Map services, versions, users, attack surface."},
    {"name": "Vulnerability Analysis", "description": "Match findings to known weaknesses."},
    {"name": "Exploitation / Initial Access", "description": "Gain the first foothold."},
    {"name": "Post-Exploitation", "description": "Privilege escalation, lateral movement, persistence."},
    {"name": "Impact / Objectives", "description": "Prove business impact (data, domain admin, etc.)."},
    {"name": "Reporting & Remediation", "description": "The deliverable that actually pays."},
]


# ---------------------------------------------------------------------------
# Small DSL so the taxonomy stays readable and short.
# ---------------------------------------------------------------------------
def ph(name: str, description: str = "") -> dict[str, str]:
    """A roadmap phase for a domain."""
    return {"name": name, "description": description}


def T(
    name: str,
    desc: str,
    phases: list[str],
    *,
    cat: str = "",
    diff: str = "Medium",
    plat: str = "Linux",
    star: bool = False,
    binary: str | None = None,
    pkg: str | None = None,
    apt: bool | str = False,
    pipx: bool | str = False,
    pip: bool | str = False,
    go: str = "",
    cargo: bool | str = False,
    gem: bool | str = False,
    git: str = "",
    web: str = "",
    docs: str = "",
    aliases: list[str] | None = None,
    examples: list[dict[str, str]] | None = None,
    cheats: list[dict[str, str]] | None = None,
    related: list[str] | None = None,
    note: str = "",
) -> dict[str, Any]:
    """Compact tool constructor.

    Install flags may be ``True`` (auto-build the command from the package) or a
    string (use verbatim). Binary defaults to a slugged name; package defaults
    to the binary.
    """
    b = binary if binary is not None else name.lower().split()[0]
    p = pkg if pkg is not None else b
    install: dict[str, str] = {}
    if apt:
        install["apt"] = apt if isinstance(apt, str) else f"sudo apt install -y {p}"
    if pipx:
        install["pipx"] = pipx if isinstance(pipx, str) else f"pipx install {p}"
    if pip:
        install["pip"] = pip if isinstance(pip, str) else f"pip install {p}"
    if go:
        install["go"] = f"go install {go}"
    if cargo:
        install["cargo"] = cargo if isinstance(cargo, str) else f"cargo install {p}"
    if gem:
        install["gem"] = gem if isinstance(gem, str) else f"sudo gem install {p}"
    if git:
        install["git"] = f"git clone {git}"

    entry: dict[str, Any] = {
        "name": name,
        "binary": b,
        "package": p,
        "description": desc,
        "phases": phases,
        "category": cat,
        "difficulty": diff,
        "platform": plat,
        "recommended": star,
        "installation": install,
        "website": web,
        "documentation": docs or web,
        "aliases": aliases or [],
        "examples": examples or [],
        "cheatsheet": cheats or [],
        "related_tools": related or [],
        "note": note,
    }
    return entry


# The domain list is assembled by the sibling modules (one per group) and
# collected here so generate.py has a single import surface.
DOMAINS: list[dict[str, Any]] = []


def register(domain: dict[str, Any]) -> None:
    """Append a domain definition to the global DOMAINS list."""
    DOMAINS.append(domain)
