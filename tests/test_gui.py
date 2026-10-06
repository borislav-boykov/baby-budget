"""Smoke test of the Tk window; skipped where no display is available (e.g. CI)."""

import tkinter as tk
import tkinter.ttk

import pytest

from baby_budget import storage
from baby_budget.gui import SECTION_PREFIX
from baby_budget.model import Item, Option, ShoppingList


@pytest.fixture(scope="module")
def tk_root():
    # One Tk interpreter per process: creating several is flaky on Windows.
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def app(tk_root, tmp_path):
    from baby_budget.gui import App

    root = tk.Toplevel(tk_root)
    root.withdraw()

    path = tmp_path / "data.json"
    monitor = Item(name="Бебефон", section="Сън", id="m")
    monitor.add_option(Option(name="Philips", price=80, id="p"))
    monitor.add_option(Option(name="Motorola", price=60, id="o"))
    storage.save(ShoppingList(items=[monitor, Item(name="Вана", section="Къпане", id="v")]), path)
    yield App(root, path)
    root.destroy()


def test_edit_fields_updates_budget_and_file(app):
    assert "80,00" in app.total_var.get()

    app.tree.selection_set("m")
    app.root.update()
    assert app.current.id == "m"

    app.qty_var.set("2")
    assert "160,00" in app.total_var.get()

    app.options.selection_set("o")
    app.toggle_option()  # choose Motorola too: 2 × 80 + 1 × 60
    assert "220,00" in app.total_var.get()
    assert app.tree.set("m", "choice") == "Philips + Motorola"
    app.options.selection_set("p")
    app.toggle_option()  # un-choose Philips
    assert "60,00" in app.total_var.get()

    app.status_var.set("Ще бъде подарено")
    app.on_field("status")
    app.gift_var.set("Мария")
    assert "0,00" in app.total_var.get()

    saved = storage.load(app.path).get("m")
    assert (saved.quantity, saved.chosen_ids, saved.status, saved.gift_from) == (2, ["o"], "gift", "Мария")


def test_filter_hides_rows(app):
    app.hide_done.set(True)
    app.data.get("v").status = "bought"
    app.refresh()
    assert not app.tree.exists("v")
    assert app.tree.exists("m")


def test_target_budget(app):
    app.target_var.set("100")
    assert app.data.target == 100
    assert "Остават 20,00 €" in app.target_status.cget("text")
    app.target_var.set("50")
    assert "Над целта с 30,00 €" in app.target_status.cget("text")
    assert storage.load(app.path).target == 50
    app.target_var.set("abc,")
    assert app.target_status.cget("text") == "Невалидна сума"
    assert app.data.target == 50


def test_gifted_status(app):
    app.tree.selection_set("m")
    app.root.update()
    app.status_var.set("Подарено")
    app.on_field("status")
    assert app.current.status == "gifted"
    assert "gifted" in app.tree.item("m", "tags")
    assert "получени 1" in app.extra_var.get()
    assert str(app.gift_entry.cget("state")) != "disabled"

    app.status_var.set("непознато")
    app.on_field("status")
    assert app.current.status == "gifted"


def test_paid_field_only_for_bought(app):
    app.tree.selection_set("v")
    app.root.update()
    assert "disabled" in app.paid_entry.state()
    app.status_var.set("Купено")
    app.on_field("status")
    assert "disabled" not in app.paid_entry.state()
    app.paid_var.set("42,50")
    assert app.data.get("v").paid == 42.5
    assert "122,50" in app.total_var.get()  # 80 monitor + 42.50 paid bath


def test_reload_after_change_elsewhere(app):
    app.tree.selection_set("m")
    app.root.update()
    other = storage.load(app.path)
    other.get("m").name = "Бебефон (от другия компютър)"
    other.target = 300
    import os
    import time
    time.sleep(0.01)
    storage.save(other, app.path)
    os.utime(app.path, ns=(time.time_ns(), time.time_ns()))

    assert app._changed_elsewhere()
    app._poll_file()
    assert app.data.target == 300
    assert app.current.id == "m"
    assert app.name_var.get() == "Бебефон (от другия компютър)"
    assert not app._changed_elsewhere()


def test_shops_dialog_lists_shops_from_options(app):
    app.data.get("m").options[0].shop = "baby.bg"
    app.edit_shops()
    win = next(w for w in app.root.winfo_children() if isinstance(w, tk.Toplevel))
    trees = [w for w in win.winfo_children()[0].winfo_children() if isinstance(w, tk.ttk.Treeview)]
    assert trees[0].get_children() == ("baby.bg",)
    win.destroy()


def test_move_selected_section(app):
    assert app.data.sections() == ["Сън", "Къпане"]
    app.tree.selection_set(SECTION_PREFIX + "Къпане")
    app.root.update()
    app.move(-1)
    assert app.data.sections() == ["Къпане", "Сън"]
    assert app.tree.get_children()[0] == SECTION_PREFIX + "Къпане"
    assert app.tree.selection() == (SECTION_PREFIX + "Къпане",)
    assert storage.load(app.path).sections() == ["Къпане", "Сън"]


def test_remembers_opened_file_for_its_language(app):
    from baby_budget import settings

    assert settings.last_file("bg") == app.path
    assert settings.last_language() == "bg"


def test_new_file_gets_sample_items_in_the_session_language(tk_root, tmp_path):
    from baby_budget.gui import App

    root = tk.Toplevel(tk_root)
    root.withdraw()
    app = App(root, tmp_path / "new.json", language="en")
    assert app.data.language == "en"
    assert app.data.sections()[0] == "Sleep & nursery"
    assert app.total_var.get().startswith("Budget needed")
    assert storage.load(tmp_path / "new.json").items[0].name == "Cot / crib"
    root.destroy()


def test_opening_a_list_in_the_other_language_is_refused(app, tmp_path, monkeypatch):
    from baby_budget import gui

    other = tmp_path / "english.json"
    storage.save(ShoppingList(language="en", items=[Item(name="Cot")]), other)
    shown = []
    monkeypatch.setattr(gui.filedialog, "askopenfilename", lambda **kw: str(other))
    monkeypatch.setattr(gui.messagebox, "showerror", lambda *a, **kw: shown.append(a))
    before = app.path
    app.open_file()
    assert app.path == before and app.data.get("m")  # still the Bulgarian list
    assert shown and "English" in shown[0][1]


def test_new_sample_list_in_session_language(app, tmp_path, monkeypatch):
    from baby_budget import gui

    target = tmp_path / "demo.json"
    monkeypatch.setattr(gui.filedialog, "asksaveasfilename", lambda **kw: str(target))
    app.new_sample_list()
    assert app.path == target
    assert app.data.sections()[0] == "Сън и детска стая"


def test_language_dialog_returns_the_clicked_language(tk_root):
    from baby_budget import gui

    def click_english():
        win = next(w for w in tk_root.winfo_children() if isinstance(w, tk.Toplevel))
        buttons = [w for w in win.winfo_children()[0].winfo_children()
                   if isinstance(w, tk.ttk.Button)]
        next(b for b in buttons if b.cget("text") == "English").invoke()

    tk_root.after(100, click_english)
    assert gui.choose_language(tk_root, "bg") == "en"


def test_language_dialog_closed_returns_none(tk_root):
    from baby_budget import gui

    def close():
        next(w for w in tk_root.winfo_children() if isinstance(w, tk.Toplevel)).destroy()

    tk_root.after(100, close)
    assert gui.choose_language(tk_root, "bg") is None



def test_rebuilding_the_ui_quickly_raises_no_error(app):
    errors = []
    app.root.report_callback_exception = lambda *exc: errors.append(exc)
    app._build_ui()
    app._build_ui()  # the first build's delayed divider placement must not fail
    app.root.after(250, app.root.quit)
    app.root.mainloop()
    assert not errors
