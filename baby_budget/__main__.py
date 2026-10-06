"""Entry point: ``python -m baby_budget [--data FILE] [--lang bg|en]``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

NO_TKINTER = """baby-budget needs Tkinter (Python's built-in window library), and it is not installed.

  Ubuntu / Debian:     sudo apt install python3-tk
  Fedora:              sudo dnf install python3-tkinter
  macOS with Homebrew: brew install python-tk
  Windows / macOS:     reinstall Python from https://www.python.org/downloads/
                       (Tkinter is included there)
"""

NO_DISPLAY = """baby-budget is a desktop app and could not open its window:
  {error}

Run it on a computer with a desktop (not over plain SSH or on a headless server).
"""


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="baby-budget",
        description="Plan and budget a baby shopping list.",
    )
    parser.add_argument(
        "--lang",
        choices=["bg", "en"],
        help="language for this session (default: asked at start)",
    )
    parser.add_argument(
        "--data",
        type=Path,
        help="list file to open (default: the one used last in the chosen language; "
        "a new list with sample items is made if there is none)",
    )
    args = parser.parse_args(argv)

    try:
        import tkinter
    except ImportError:
        sys.exit(NO_TKINTER)
    from .gui import run

    try:
        run(args.data.resolve() if args.data else None, args.lang)
    except tkinter.TclError as exc:  # raised before any window exists, e.g. no display
        sys.exit(NO_DISPLAY.format(error=exc))


if __name__ == "__main__":
    main()
