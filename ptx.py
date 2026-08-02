#!/usr/bin/env python3
"""
ptx.py
======

PTX -- Professional Pentesting Framework.

Entry point. Deliberately tiny: it constructs the :class:`Application` from
``core.cli`` and hands over control. All real work lives in the ``core``
package so this file stays a stable, one-line launcher.

Usage
-----
    python ptx.py

Requires Python 3.13+. See ``requirements.txt`` for dependencies.
"""

from __future__ import annotations

import sys


def main() -> int:
    """Launch PTX and return its process exit code."""
    if sys.version_info < (3, 13):
        sys.stderr.write("PTX requires Python 3.13 or newer.\n")
        return 1

    # Imported here (after the version check) so a clear message is shown on old
    # interpreters instead of a syntax/typing error from the core package.
    from core.cli import Application

    try:
        return Application().run()
    except KeyboardInterrupt:
        sys.stderr.write("\nInterrupted.\n")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
