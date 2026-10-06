"""Start-up problems end with a clear message, not a traceback."""

import sys
import tkinter

import pytest

from baby_budget import __main__ as entry


def test_missing_tkinter_explains_how_to_install_it(monkeypatch):
    monkeypatch.setitem(sys.modules, "tkinter", None)  # makes "import tkinter" fail
    with pytest.raises(SystemExit) as exit_info:
        entry.main([])
    message = str(exit_info.value.code)
    assert "Tkinter" in message
    assert "sudo apt install python3-tk" in message
    assert "brew install python-tk" in message


def test_no_display_explains_the_problem(monkeypatch):
    from baby_budget import gui

    def no_display(*args, **kwargs):
        raise tkinter.TclError("no display name and no $DISPLAY environment variable")

    monkeypatch.setattr(gui, "run", no_display)
    with pytest.raises(SystemExit) as exit_info:
        entry.main(["--lang", "en"])
    message = str(exit_info.value.code)
    assert "could not open its window" in message
    assert "no $DISPLAY" in message
