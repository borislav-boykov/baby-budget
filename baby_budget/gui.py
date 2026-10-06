"""Tkinter desktop UI.

Left: items grouped by section, with the chosen product and its cost.
Right: details of the selected item and the products to choose from.
Bottom: live budget summary. Every change is saved to the JSON file at once.
"""

from __future__ import annotations

import sys
import tkinter as tk
import tkinter.font as tkfont
import traceback
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from . import export, settings, storage, templates
from .budget import summarize
from .i18n import (
    LANGUAGE_NAMES,
    fmt_money,
    fmt_number,
    parse_price,
    priority_label,
    set_language,
    status_label,
    system_language,
    t,
    target_text,
)
from .model import PRIORITIES, STATUSES, Item, Option, Shop

SECTION_PREFIX = "section::"
POLL_MS = 3000  # how often to look for changes made elsewhere (cloud sync)


class FormDialog(tk.Toplevel):
    """Modal dialog with labelled fields. ``result`` is a dict, or None if cancelled.

    ``fields`` is a list of ``(key, label, kind, choices)`` with kind
    ``"entry"``, ``"combo"`` or ``"text"``.
    """

    def __init__(self, parent: tk.Misc, title: str, fields: list, values: dict | None = None):
        super().__init__(parent)
        self.title(title)
        self.transient(parent.winfo_toplevel())
        self.result: dict | None = None
        values = values or {}
        self._getters = {}

        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        first = None
        for row, (key, label, kind, choices) in enumerate(fields):
            ttk.Label(body, text=label).grid(row=row, column=0, sticky="nw", padx=(0, 8), pady=4)
            if kind == "text":
                widget = tk.Text(body, width=55, height=5, wrap="word", font="TkDefaultFont")
                widget.insert("1.0", values.get(key, ""))
                self._getters[key] = lambda w=widget: w.get("1.0", "end-1c").strip()
            else:
                var = tk.StringVar(value=values.get(key, ""))
                if kind == "combo":
                    widget = ttk.Combobox(body, textvariable=var, values=choices, width=53)
                else:
                    widget = ttk.Entry(body, textvariable=var, width=55)
                widget.bind("<Return>", lambda e: self._ok())
                self._getters[key] = lambda v=var: v.get().strip()
            widget.grid(row=row, column=1, sticky="ew", pady=4)
            first = first or widget

        buttons = ttk.Frame(body)
        buttons.grid(row=len(fields), column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(buttons, text=t("ok"), command=self._ok).pack(side="left", padx=4)
        ttk.Button(buttons, text=t("cancel"), command=self.destroy).pack(side="left")
        self.bind("<Escape>", lambda e: self.destroy())

        top = parent.winfo_toplevel()
        self.geometry(f"+{top.winfo_rootx() + 120}+{top.winfo_rooty() + 100}")
        first.focus_set()
        self.grab_set()
        self.wait_window()

    def _ok(self) -> None:
        self.result = {key: get() for key, get in self._getters.items()}
        self.destroy()


class App:
    def __init__(self, root: tk.Tk, path: Path, language: str | None = None):
        """Open ``path``. The UI language is fixed for the whole session: ``language``,
        else the file's own, else the system's. A new file gets the sample list in it."""
        self.root = root
        self.language = language or settings.file_language(path) or system_language()
        set_language(self.language)
        self._mtime: int | None = None
        if not self._load_file(path):
            raise SystemExit(1)

        self.current: Item | None = None
        self.selected_section: str | None = None
        self._loading = False
        self._collapsed: set[str] = set()
        self._priority_filter: str | None = None
        self.hide_done = tk.BooleanVar(master=root, value=False)

        root.geometry("1300x760")
        root.minsize(950, 550)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._build_styles()
        self._build_ui()
        self.root.after(POLL_MS, self._poll_file)

    # ---------- file handling ----------

    def _load_file(self, path: Path) -> bool:
        """Make ``path`` the open list. Returns False if it cannot be used.

        A missing file is created with the sample list in the session language;
        a list in the other language is refused (the language is chosen at start).
        """
        try:
            data = storage.load(path, self.language)
        except ValueError as exc:
            data = self._recover(path, exc)
            if data is None:
                return False
        if data.language != self.language:
            name = LANGUAGE_NAMES[data.language]
            messagebox.showerror(
                t("wrong_language_title"), t("wrong_language", language=name), parent=self.root
            )
            return False
        self.path, self.data = path, data
        self._mtime = storage.modified_time(path)
        if self._mtime is None:
            self.save()
        else:
            storage.backup(path)
        settings.remember(self.language, path)
        return True

    def _recover(self, path: Path, error: Exception):
        if not messagebox.askyesno(
            t("corrupt_title"), t("corrupt_restore", path=path, error=error), parent=self.root
        ):
            return None
        backup = storage.restore_latest_valid(path)
        if backup is None:
            messagebox.showerror(t("corrupt_title"), t("corrupt_no_backup"), parent=self.root)
            return None
        messagebox.showinfo(
            t("corrupt_title"),
            t("corrupt_restored", backup=backup, damaged=path.name + ".damaged"),
            parent=self.root,
        )
        return storage.load(path)

    def _changed_elsewhere(self) -> bool:
        current = storage.modified_time(self.path)
        return None not in (current, self._mtime) and current != self._mtime

    def _poll_file(self) -> None:
        # Skip while a dialog is open; its result would land in reloaded data.
        if self._changed_elsewhere() and self.root.grab_current() is None:
            self.reload()
        self.root.after(POLL_MS, self._poll_file)

    def reload(self) -> None:
        """Load the file again after it was changed elsewhere, keeping the selection."""
        try:
            data = storage.load(self.path)
        except ValueError:
            return  # probably still syncing; the next poll tries again
        current_id = self.current.id if self.current else None
        self.data = data
        self._mtime = storage.modified_time(self.path)
        self.current = next((i for i in data.items if i.id == current_id), None)
        self._build_ui()

    def open_file(self) -> None:
        name = filedialog.askopenfilename(
            parent=self.root, initialdir=self.path.parent,
            filetypes=[(t("json_files"), "*.json")],
        )
        if name and self._load_file(Path(name)):
            self.current, self.selected_section = None, None
            self._collapsed.clear()
            self._build_ui()

    def new_sample_list(self) -> None:
        """Start a new file filled with the sample list in the session language."""
        name = filedialog.asksaveasfilename(
            parent=self.root, initialdir=self.path.parent,
            initialfile=t("sample_filename") + ".json",
            defaultextension=".json", filetypes=[(t("json_files"), "*.json")],
        )
        if not name:
            return
        path = Path(name)
        try:
            storage.backup(path)  # the save dialog already asked before overwriting
            storage.save(templates.default_list(self.language), path)
        except OSError as exc:
            messagebox.showerror(t("save_error"), str(exc), parent=self.root)
            return
        if self._load_file(path):
            self.current, self.selected_section = None, None
            self._collapsed.clear()
            self._build_ui()

    def save_as(self) -> None:
        """Move the list to another place, e.g. a OneDrive folder shared by two people."""
        name = filedialog.asksaveasfilename(
            parent=self.root, initialdir=self.path.parent, initialfile=self.path.name,
            defaultextension=".json", filetypes=[(t("json_files"), "*.json")],
        )
        if not name:
            return
        self.path = Path(name)
        self._mtime = None
        self.save()
        settings.remember(self.language, self.path)
        self.root.title(t("app_title", path=self.path))

    def _build_ui(self) -> None:
        """(Re)create every widget, e.g. after another list was opened."""
        for child in self.root.winfo_children():
            if not isinstance(child, tk.Toplevel):
                child.destroy()
        self.root.title(t("app_title", path=self.path))
        self._build_menu()
        self._build_summary()
        self._build_body()
        self.show_item(self.current)
        self.refresh()

    # ---------- layout ----------

    def _build_styles(self) -> None:
        style = ttk.Style(self.root)
        base = tkfont.nametofont("TkDefaultFont")
        rowheight = base.metrics("linespace") + 8
        style.configure("Treeview", rowheight=rowheight)
        self.bold = base.copy()
        self.bold.configure(weight="bold")
        self.big = base.copy()
        self.big.configure(size=base.cget("size") + 5, weight="bold")

    def _build_menu(self) -> None:
        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label=t("menu_new_sample"), command=self.new_sample_list)
        file_menu.add_command(label=t("menu_open"), command=self.open_file)
        file_menu.add_command(label=t("menu_save_as"), command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label=t("menu_export_md"), command=self.export_markdown)
        file_menu.add_command(label=t("menu_export_csv"), command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label=t("menu_exit"), command=self.close)
        menu.add_cascade(label=t("menu_file"), menu=file_menu)

        edit_menu = tk.Menu(menu, tearoff=False)
        edit_menu.add_command(label=t("menu_new_item"), accelerator="Ctrl+N", command=self.add_item)
        edit_menu.add_command(label=t("menu_delete"), command=self.delete_selected)
        edit_menu.add_command(label=t("menu_move_up"), command=lambda: self.move(-1))
        edit_menu.add_command(label=t("menu_move_down"), command=lambda: self.move(1))
        edit_menu.add_separator()
        edit_menu.add_command(label=t("menu_rename_section"), command=self.rename_section)
        edit_menu.add_command(label=t("menu_shops"), command=self.edit_shops)
        menu.add_cascade(label=t("menu_edit"), menu=edit_menu)
        self.root.config(menu=menu)
        self.root.bind("<Control-n>", lambda e: self.add_item())

    def _build_summary(self) -> None:
        bar = ttk.Frame(self.root, padding=(12, 8))
        bar.pack(side="bottom", fill="x")
        ttk.Separator(self.root).pack(side="bottom", fill="x")

        self.total_var = tk.StringVar()
        self.priority_var_text = tk.StringVar()
        self.spent_var = tk.StringVar()
        self.extra_var = tk.StringVar()

        left = ttk.Frame(bar)
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(left, textvariable=self.total_var, font=self.big).pack(anchor="w")
        ttk.Label(left, textvariable=self.priority_var_text).pack(anchor="w")

        middle = ttk.Frame(bar)
        middle.pack(side="left", padx=20)
        row = ttk.Frame(middle)
        row.pack(anchor="w")
        ttk.Label(row, text=t("target"), font=self.bold).pack(side="left")
        self.target_var = tk.StringVar(
            value=fmt_number(self.data.target) if self.data.target else ""
        )
        ttk.Entry(row, textvariable=self.target_var, width=12, justify="right").pack(
            side="left", padx=6
        )
        ttk.Label(row, text=self.data.currency).pack(side="left")
        self.target_status = ttk.Label(middle, font=self.bold)
        self.target_status.pack(anchor="w", pady=(4, 0))
        self.target_hint = ttk.Label(middle)
        self.target_hint.pack(anchor="w")
        self.target_var.trace_add("write", lambda *a: self.on_target())

        right = ttk.Frame(bar)
        right.pack(side="right")
        ttk.Label(right, textvariable=self.spent_var, font=self.bold).pack(anchor="e")
        self.progress = ttk.Progressbar(right, length=320, maximum=1)
        self.progress.pack(anchor="e", pady=2)
        ttk.Label(right, textvariable=self.extra_var).pack(anchor="e")

    def _build_body(self) -> None:
        panes = ttk.PanedWindow(self.root, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=8, pady=8)
        panes.add(self._build_list(panes), weight=3)
        panes.add(self._build_detail(panes), weight=2)
        self.root.after(50, lambda: self._place_divider(panes))

    def _place_divider(self, panes: ttk.PanedWindow, tries: int = 40) -> None:
        """Give the list 60 % of the width once the window has been laid out."""
        if not panes.winfo_exists():  # the UI was rebuilt meanwhile
            return
        width = panes.winfo_width()
        if width < 200:  # not laid out yet (or hidden): try again shortly
            if tries:
                self.root.after(50, lambda: self._place_divider(panes, tries - 1))
            return
        panes.sashpos(0, max(int(width * 0.6), min(780, width - 320)))

    def _build_list(self, parent: tk.Misc) -> ttk.Frame:
        frame = ttk.Frame(parent)
        bar = ttk.Frame(frame)
        bar.pack(fill="x", pady=(0, 6))
        ttk.Button(bar, text=t("add_item"), command=self.add_item).pack(side="left")
        ttk.Button(bar, text=t("delete"), command=self.delete_selected).pack(side="left", padx=4)
        ttk.Button(bar, text="▲", width=3, command=lambda: self.move(-1)).pack(side="left")
        ttk.Button(bar, text="▼", width=3, command=lambda: self.move(1)).pack(side="left", padx=4)

        ttk.Checkbutton(
            bar, text=t("hide_done"), variable=self.hide_done, command=self.refresh
        ).pack(side="right")
        self.filter_combo = ttk.Combobox(
            bar, state="readonly", width=14,
            values=[t("all"), *(priority_label(p) for p in PRIORITIES)],
        )
        self.filter_combo.current(
            PRIORITIES.index(self._priority_filter) + 1 if self._priority_filter else 0
        )
        self.filter_combo.pack(side="right", padx=8)
        self.filter_combo.bind("<<ComboboxSelected>>", lambda e: self.on_filter())
        ttk.Label(bar, text=t("priority_filter")).pack(side="right")

        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill="both", expand=True)
        columns = ("choice", "qty", "cost", "priority", "status")
        self.tree = ttk.Treeview(tree_frame, columns=columns, selectmode="browse")
        headings = {
            "#0": (t("col_item"), 250), "choice": (t("col_choice"), 190),
            "qty": (t("col_qty"), 45), "cost": (t("col_cost"), 90),
            "priority": (t("col_priority"), 100), "status": (t("col_status"), 190),
        }
        for col, (text, width) in headings.items():
            self.tree.heading(col, text=text, anchor="w")
            self.tree.column(col, width=width, minwidth=40, stretch=col in ("#0", "choice"))
        self.tree.column("qty", anchor="e")
        self.tree.column("cost", anchor="e")
        self.tree.tag_configure("section", font=self.bold, background="#eef2f7")
        self.tree.tag_configure("bought", foreground="#2e7d32")
        self.tree.tag_configure("gift", foreground="#7b1fa2")
        self.tree.tag_configure("gifted", foreground="#00796b")
        self.tree.tag_configure("unchosen", foreground="#808080")

        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<<TreeviewOpen>>", lambda e: self._track_open(True))
        self.tree.bind("<<TreeviewClose>>", lambda e: self._track_open(False))
        self.tree.bind("<Delete>", lambda e: self.delete_selected())
        return frame

    def _build_detail(self, parent: tk.Misc) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=(8, 0, 0, 0))

        form = ttk.LabelFrame(frame, text=t("item_frame"), padding=10)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        self.name_var = tk.StringVar()
        self.section_var = tk.StringVar()
        self.qty_var = tk.StringVar()
        self.priority_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.gift_var = tk.StringVar()
        self.paid_var = tk.StringVar()

        self.name_entry = ttk.Entry(form, textvariable=self.name_var)
        self.section_combo = ttk.Combobox(form, textvariable=self.section_var)
        self.qty_spin = ttk.Spinbox(form, textvariable=self.qty_var, from_=1, to=999, width=6)
        self.priority_combo = ttk.Combobox(
            form, textvariable=self.priority_var, state="readonly",
            values=[priority_label(p) for p in PRIORITIES],
        )
        self.status_combo = ttk.Combobox(
            form, textvariable=self.status_var, state="readonly",
            values=[status_label(s) for s in STATUSES],
        )
        self.gift_entry = ttk.Entry(form, textvariable=self.gift_var)
        self.paid_entry = ttk.Entry(form, textvariable=self.paid_var, width=12, justify="right")
        self.notes_text = tk.Text(form, height=3, wrap="word", font="TkDefaultFont")

        rows = [
            (t("name"), self.name_entry), (t("section"), self.section_combo),
            (t("quantity"), self.qty_spin), (t("priority"), self.priority_combo),
            (t("status"), self.status_combo), (t("paid"), self.paid_entry),
            (t("gift_from"), self.gift_entry),
            (t("notes"), self.notes_text),
        ]
        for row, (label, widget) in enumerate(rows):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="nw", padx=(0, 8), pady=3)
            sticky = "w" if widget in (self.qty_spin, self.paid_entry) else "ew"
            widget.grid(row=row, column=1, sticky=sticky, pady=3)

        self.name_var.trace_add("write", lambda *a: self.on_field("name"))
        self.qty_var.trace_add("write", lambda *a: self.on_field("quantity"))
        self.gift_var.trace_add("write", lambda *a: self.on_field("gift_from"))
        self.paid_var.trace_add("write", lambda *a: self.on_field("paid"))
        self.priority_combo.bind("<<ComboboxSelected>>", lambda e: self.on_field("priority"))
        self.status_combo.bind("<<ComboboxSelected>>", lambda e: self.on_field("status"))
        for event in ("<<ComboboxSelected>>", "<FocusOut>", "<Return>"):
            self.section_combo.bind(event, lambda e: self.apply_section())
        self.notes_text.bind("<KeyRelease>", lambda e: self.on_field("notes"))

        box = ttk.LabelFrame(frame, text=t("options_frame"), padding=10)
        box.pack(fill="both", expand=True, pady=(8, 0))
        bar = ttk.Frame(box)
        bar.pack(fill="x", pady=(0, 6))
        self.option_buttons = [
            ttk.Button(bar, text=t("add_option"), command=self.add_option),
            ttk.Button(bar, text=t("edit"), command=self.edit_option),
            ttk.Button(bar, text=t("delete"), command=self.delete_option),
            ttk.Button(bar, text=t("choose"), command=self.toggle_option),
            ttk.Button(bar, text=t("open_link"), command=self.open_link),
        ]
        for button in self.option_buttons:
            button.pack(side="left", padx=(0, 4))

        self.options = ttk.Treeview(
            box, columns=("mark", "name", "shop", "qty", "price", "url"), show="headings",
            height=7,
            selectmode="browse",
        )
        for col, text, width, stretch in (
            ("mark", "", 30, False), ("name", t("col_product"), 180, True),
            ("shop", t("col_shop"), 100, False), ("qty", t("col_qty"), 45, False),
            ("price", t("col_price"), 90, False),
            ("url", t("col_link"), 140, True),
        ):
            self.options.heading(col, text=text, anchor="w")
            self.options.column(col, width=width, stretch=stretch)
        self.options.column("price", anchor="e")
        self.options.column("qty", anchor="e")
        self.options.tag_configure("chosen", font=self.bold, foreground="#2e7d32")
        self.options.pack(fill="both", expand=True)
        self.options.bind("<<TreeviewSelect>>", lambda e: self.show_description())
        self.options.bind("<Double-1>", lambda e: self.edit_option())
        self.options.bind("<Delete>", lambda e: self.delete_option())

        self.desc_var = tk.StringVar()
        self.desc_label = ttk.Label(box, textvariable=self.desc_var, wraplength=420, justify="left")
        # packed before the list, so a short window shrinks the list, not the description
        self.desc_label.pack(side="bottom", fill="x", pady=(6, 0), before=self.options)
        box.bind("<Configure>", lambda e: self.desc_label.configure(wraplength=e.width - 30))

        self.detail_widgets = [
            self.name_entry, self.section_combo, self.qty_spin, self.priority_combo,
            self.status_combo, self.paid_entry, self.gift_entry, *self.option_buttons,
        ]
        return frame

    # ---------- list ----------

    def on_filter(self) -> None:
        index = self.filter_combo.current()
        self._priority_filter = PRIORITIES[index - 1] if index > 0 else None
        self.refresh()

    def _visible(self, item: Item) -> bool:
        wanted = self._priority_filter
        if wanted and item.priority != wanted:
            return False
        return not (self.hide_done.get() and item.status in ("bought", "gift", "gifted"))

    def _row(self, item: Item) -> tuple[tuple, tuple]:
        cur = self.data.currency
        chosen = item.chosen_options
        if chosen:
            choice = " + ".join(o.name for o in chosen)
        else:
            choice = t("not_chosen") if item.options else t("no_options")
        status = status_label(item.status)
        if item.is_gift and item.gift_from:
            status += f" ({item.gift_from})"
        values = (
            choice,
            item.chosen_quantity or item.quantity,
            fmt_money(item.effective_cost, cur) if item.effective_cost is not None else "",
            priority_label(item.priority),
            status,
        )
        if item.status in ("bought", "gift", "gifted"):
            tags = (item.status,)
        else:
            tags = () if chosen else ("unchosen",)
        return values, tags

    def refresh(self) -> None:
        """Rebuild the whole list and summary (after structural changes)."""
        tree = self.tree
        tree.delete(*tree.get_children())
        for section in self.data.sections():
            items = [i for i in self.data.items_in(section) if self._visible(i)]
            if not items:
                continue
            sid = SECTION_PREFIX + section
            tree.insert(
                "", "end", iid=sid, text=section, values=self._section_values(section),
                open=section not in self._collapsed, tags=("section",),
            )
            for item in items:
                values, tags = self._row(item)
                tree.insert(sid, "end", iid=item.id, text=item.name, values=values, tags=tags)

        if self.current and tree.exists(self.current.id):
            tree.selection_set(self.current.id)
            tree.see(self.current.id)
        self.section_combo.configure(values=self.data.sections())
        self.update_summary()

    def _section_values(self, section: str) -> tuple:
        total = summarize(self.data.items_in(section)).total
        return ("", "", fmt_money(total, self.data.currency), "", "")

    def update_current_row(self) -> None:
        """Cheap update of one row, its section subtotal and the summary."""
        item = self.current
        if item and self.tree.exists(item.id):
            values, tags = self._row(item)
            self.tree.item(item.id, text=item.name, values=values, tags=tags)
            sid = SECTION_PREFIX + item.section
            self.tree.item(sid, values=self._section_values(item.section))
        self.update_summary()

    def update_summary(self) -> None:
        cur = self.data.currency
        s = summarize(self.data.items, self.data.shops)
        self.total_var.set(t("total", amount=fmt_money(s.total, cur)))
        parts = [f"{priority_label(p)}: {fmt_money(s.by_priority[p], cur)}" for p in PRIORITIES]
        if s.shipping:
            parts.append(t("shipping_line", amount=fmt_money(s.shipping, cur)))
        self.priority_var_text.set("   ·   ".join(parts))
        self.spent_var.set(
            t("spent_left", spent=fmt_money(s.spent, cur), left=fmt_money(s.remaining, cur))
        )
        self.progress.configure(maximum=max(s.total, 0.01), value=s.spent)
        extra = t(
            "gifts", count=s.gift_count, received=s.gifts_received,
            amount=fmt_money(s.gift_value, cur),
        )
        if s.unchosen_count:
            extra += "   ·   " + t(
                "unchosen", count=s.unchosen_count, amount=fmt_money(s.unchosen_min, cur)
            )
        self.extra_var.set(extra)
        self.update_target(s)

    def on_target(self) -> None:
        try:
            target = parse_price(self.target_var.get())
        except ValueError:
            self.target_status.configure(text=t("invalid_amount"), foreground="#c62828")
            return
        self.data.target = target
        self.save()
        self.update_summary()

    def update_target(self, s) -> None:
        target = self.data.target
        if target <= 0:
            self.target_status.configure(text=t("target_empty"), foreground="#808080")
            self.target_hint.configure(text="")
            return

        cur = self.data.currency
        over = s.total > target
        verdict = target_text(target, s.total, cur)
        self.target_status.configure(
            text=("✖ " if over else "✔ ") + verdict[0].upper() + verdict[1:],
            foreground="#c62828" if over else "#2e7d32",
        )
        if s.unchosen_min > 0:
            projected = s.total + s.unchosen_min
            self.target_hint.configure(
                text=t(
                    "target_projected", amount=fmt_money(projected, cur),
                    verdict=target_text(target, projected, cur),
                ),
                foreground="#c62828" if projected > target else "",
            )
        else:
            self.target_hint.configure(text="")

    def _track_open(self, is_open: bool) -> None:
        iid = self.tree.focus()
        if iid.startswith(SECTION_PREFIX):
            section = iid[len(SECTION_PREFIX):]
            if is_open:
                self._collapsed.discard(section)
            else:
                self._collapsed.add(section)

    def on_tree_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        iid = selection[0]
        if iid.startswith(SECTION_PREFIX):
            self.selected_section = iid[len(SECTION_PREFIX):]
            self.current = None
            self.show_item(None)
            return
        if self.current and self.current.id == iid:
            return
        self.current = self.data.get(iid)
        self.selected_section = self.current.section
        self.show_item(self.current)

    # ---------- item details ----------

    def show_item(self, item: Item | None) -> None:
        self._loading = True
        try:
            self.name_var.set(item.name if item else "")
            self.section_var.set(item.section if item else "")
            self.qty_var.set(str(item.quantity) if item else "")
            self.priority_var.set(priority_label(item.priority) if item else "")
            self.status_var.set(status_label(item.status) if item else "")
            self.gift_var.set(item.gift_from if item else "")
            self.paid_var.set(fmt_number(item.paid) if item and item.paid is not None else "")
            self.notes_text.configure(state="normal")
            self.notes_text.delete("1.0", "end")
            if item:
                self.notes_text.insert("1.0", item.notes)
        finally:
            self._loading = False

        for widget in self.detail_widgets:
            if item is None:
                widget.state(["disabled"])
            elif widget in (self.priority_combo, self.status_combo):
                widget.state(["!disabled", "readonly"])
            else:
                widget.state(["!disabled"])
        self.notes_text.configure(state="normal" if item else "disabled")
        if item and not item.is_gift:
            self.gift_entry.state(["disabled"])
        if item and item.status != "bought":
            self.paid_entry.state(["disabled"])
        self.refresh_options()

    def on_field(self, field: str) -> None:
        item = self.current
        if self._loading or item is None:
            return
        if field == "name":
            item.name = self.name_var.get()
        elif field == "quantity":
            try:
                qty = int(self.qty_var.get())
            except ValueError:
                return
            if qty < 1:
                return
            item.set_quantity(qty)
            self.refresh_options(self._selected_option_id())
        elif field == "gift_from":
            item.gift_from = self.gift_var.get().strip()
        elif field == "paid":
            text = self.paid_var.get().strip()
            try:
                item.paid = parse_price(text) if text else None
            except ValueError:
                return
        elif field == "notes":
            item.notes = self.notes_text.get("1.0", "end-1c")
        elif field == "priority":
            index = self.priority_combo.current()
            if index < 0:
                return
            item.priority = PRIORITIES[index]
        elif field == "status":
            index = self.status_combo.current()
            if index < 0:
                return
            item.status = STATUSES[index]
            self.gift_entry.state(["!disabled" if item.is_gift else "disabled"])
            self.paid_entry.state(["!disabled" if item.status == "bought" else "disabled"])
        self.save()
        if field in ("priority", "status"):
            self.refresh()  # filters may hide or show the row
        else:
            self.update_current_row()

    def apply_section(self) -> None:
        item = self.current
        if self._loading or item is None:
            return
        section = self.section_var.get().strip() or t("other_section")
        if section == item.section:
            return
        item.section = section
        self.selected_section = section
        self._collapsed.discard(section)
        self.save()
        self.refresh()

    # ---------- item actions ----------

    def add_item(self) -> None:
        sections = self.data.sections()
        default = self.selected_section or (sections[0] if sections else t("other_section"))
        result = FormDialog(
            self.root, t("new_item"),
            [("name", t("name"), "entry", None), ("section", t("section"), "combo", sections)],
            {"section": default},
        ).result
        if not result or not result["name"]:
            return
        item = Item(name=result["name"], section=result["section"] or t("other_section"))
        siblings = self.data.items_in(item.section)
        if self.current and self.current.section == item.section:
            after = self.current.id
        else:
            after = siblings[-1].id if siblings else None
        self.data.add(item, after_id=after)
        self._collapsed.discard(item.section)
        self.current = item
        self.selected_section = item.section
        self.save()
        self.refresh()
        self.show_item(item)
        self.name_entry.focus_set()

    def delete_selected(self) -> None:
        if self.current is None:
            section = self.selected_section
            selection = self.tree.selection()
            if not (section and selection and selection[0].startswith(SECTION_PREFIX)):
                return
            count = len(self.data.items_in(section))
            if not messagebox.askyesno(
                t("delete_title"), t("confirm_delete_section", section=section, count=count)
            ):
                return
            storage.backup(self.path)
            self.data.remove_section(section)
            self.selected_section = None
        else:
            name = self.current.name
            if not messagebox.askyesno(t("delete_title"), t("confirm_delete", name=name)):
                return
            self.data.remove(self.current.id)
            self.current = None
            self.show_item(None)
        self.save()
        self.refresh()

    def move(self, delta: int) -> None:
        """Move the selected item within its section, or the selected section as a whole."""
        if self.current:
            moved = self.data.move(self.current.id, delta)
        elif self.selected_section in self.data.sections():
            moved = self.data.move_section(self.selected_section, delta)
        else:
            return
        if moved:
            self.save()
            self.refresh()
            if self.current is None:
                sid = SECTION_PREFIX + self.selected_section
                if self.tree.exists(sid):
                    self.tree.selection_set(sid)
                    self.tree.see(sid)

    def rename_section(self) -> None:
        section = self.selected_section
        if not section:
            messagebox.showinfo(t("section_title"), t("select_section_first"))
            return
        new = simpledialog.askstring(
            t("rename_title"), t("rename_prompt"), initialvalue=section, parent=self.root
        )
        if not new or not new.strip() or new.strip() == section:
            return
        self.data.rename_section(section, new.strip())
        self.selected_section = new.strip()
        self.save()
        self.refresh()
        self.show_item(self.current)

    # ---------- options ----------

    def refresh_options(self, select: str | None = None) -> None:
        tree = self.options
        tree.delete(*tree.get_children())
        item = self.current
        if item is not None:
            for opt in sorted(item.options, key=lambda o: o.price):
                chosen = item.is_chosen(opt.id)
                tree.insert(
                    "", "end", iid=opt.id, tags=("chosen",) if chosen else (),
                    values=(
                        "✔" if chosen else "", opt.name, opt.shop, opt.quantity,
                        fmt_money(opt.price, self.data.currency), opt.url,
                    ),
                )
            if select and tree.exists(select):
                tree.selection_set(select)
        self.show_description()

    def _selected_option_id(self) -> str | None:
        selection = self.options.selection()
        return selection[0] if selection else None

    def selected_option(self) -> Option | None:
        selection = self.options.selection()
        if self.current is None or not selection:
            return None
        return self.current.find_option(selection[0])

    def show_description(self) -> None:
        opt = self.selected_option()
        self.desc_var.set(opt.description if opt else "")

    def _ask_option(self, title: str, values: dict) -> dict | None:
        fields = [
            ("name", t("product"), "entry", None),
            ("price", t("price", currency=self.data.currency), "entry", None),
            ("quantity", t("option_quantity"), "entry", None),
            ("shop", t("shop"), "combo", self.data.shop_names()),
            ("url", t("link"), "entry", None),
            ("description", t("description"), "text", None),
        ]
        while True:
            result = FormDialog(self.root, title, fields, values).result
            if result is None:
                return None
            values = result
            if not result["name"]:
                messagebox.showerror(t("error"), t("need_product_name"))
                continue
            try:
                result["price"] = parse_price(result["price"])
            except ValueError:
                messagebox.showerror(t("error"), t("invalid_price", value=result["price"]))
                continue
            try:
                result["quantity"] = int(result["quantity"] or 1)
                if result["quantity"] < 1:
                    raise ValueError
            except ValueError:
                messagebox.showerror(t("error"), t("invalid_quantity"))
                continue
            return result

    def _options_changed(self, select: str | None = None) -> None:
        self.save()
        self.refresh_options(select)
        self.update_current_row()

    def add_option(self) -> None:
        if self.current is None:
            return
        # a product added while nothing is chosen will be the one we buy: suggest all we need
        qty = 1 if self.current.chosen_ids else self.current.quantity
        result = self._ask_option(t("new_option", name=self.current.name), {"quantity": str(qty)})
        if result is None:
            return
        opt = Option(**result)
        self.current.add_option(opt)
        self._options_changed(opt.id)

    def edit_option(self) -> None:
        opt = self.selected_option()
        if opt is None:
            return
        result = self._ask_option(
            t("edit_option"),
            {"name": opt.name, "price": fmt_number(opt.price), "quantity": str(opt.quantity),
             "shop": opt.shop,
             "url": opt.url, "description": opt.description},
        )
        if result is None:
            return
        opt.name, opt.price, opt.quantity, opt.shop, opt.url, opt.description = (
            result["name"], result["price"], result["quantity"], result["shop"], result["url"],
            result["description"],
        )
        self._options_changed(opt.id)

    def delete_option(self) -> None:
        opt = self.selected_option()
        if opt is None or not messagebox.askyesno(
            t("delete_title"), t("confirm_delete", name=opt.name)
        ):
            return
        self.current.remove_option(opt.id)
        self._options_changed()

    def toggle_option(self) -> None:
        opt = self.selected_option()
        if opt is None:
            messagebox.showinfo(t("choose_title"), t("select_option_first"))
            return
        self.current.toggle_choice(opt.id)
        self._options_changed(opt.id)

    def open_link(self) -> None:
        opt = self.selected_option()
        if opt and opt.url:
            webbrowser.open(opt.url)

    # ---------- shops ----------

    def edit_shops(self) -> None:
        cur = self.data.currency
        win = tk.Toplevel(self.root)
        win.title(t("shops_title"))
        win.transient(self.root)
        frame = ttk.Frame(win, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=t("shops_hint"), wraplength=480).pack(anchor="w", pady=(0, 8))

        tree = ttk.Treeview(frame, columns=("shipping", "free_over"), height=10, selectmode="browse")
        tree.heading("#0", text=t("col_shop"), anchor="w")
        tree.heading("shipping", text=t("col_shipping"), anchor="w")
        tree.heading("free_over", text=t("col_free_over"), anchor="w")
        tree.column("#0", width=220)
        tree.column("shipping", width=110, anchor="e")
        tree.column("free_over", width=130, anchor="e")
        tree.pack(fill="both", expand=True)

        def fill() -> None:
            tree.delete(*tree.get_children())
            for name in self.data.shop_names():
                shop = self.data.shops.get(name, Shop())
                free = fmt_money(shop.free_over, cur) if shop.free_over else "—"
                tree.insert("", "end", iid=name, text=name,
                            values=(fmt_money(shop.shipping, cur), free))

        def edit() -> None:
            selection = tree.selection()
            if not selection:
                return
            name = selection[0]
            shop = self.data.shops.get(name, Shop())
            values = {"shipping": fmt_number(shop.shipping), "free_over": fmt_number(shop.free_over)}
            fields = [
                ("shipping", t("shipping", currency=cur), "entry", None),
                ("free_over", t("free_over", currency=cur), "entry", None),
            ]
            while True:
                result = FormDialog(win, name, fields, values).result
                if result is None:
                    return
                values = result
                try:
                    self.data.shops[name] = Shop(
                        shipping=parse_price(result["shipping"]),
                        free_over=parse_price(result["free_over"]),
                    )
                except ValueError:
                    messagebox.showerror(t("error"), t("invalid_amount"), parent=win)
                    continue
                break
            self.save()
            fill()
            tree.selection_set(name)
            self.update_summary()

        tree.bind("<Double-1>", lambda e: edit())
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text=t("close"), command=win.destroy).pack(side="right")
        ttk.Button(buttons, text=t("edit"), command=edit).pack(side="right", padx=4)
        fill()
        win.geometry(f"+{self.root.winfo_rootx() + 150}+{self.root.winfo_rooty() + 120}")
        win.grab_set()

    # ---------- files ----------

    def save(self) -> None:
        if self._changed_elsewhere():
            if messagebox.askyesno(t("conflict_title"), t("conflict_msg"), parent=self.root):
                self.reload()
                return
        try:
            storage.save(self.data, self.path)
        except OSError as exc:
            messagebox.showerror(t("save_error"), str(exc))
            return
        self._mtime = storage.modified_time(self.path)

    def _ask_export_path(self, ext: str, kind: str) -> Path | None:
        name = filedialog.asksaveasfilename(
            parent=self.root, title=t("export_title"), defaultextension=ext,
            initialdir=self.path.parent, initialfile=f"{t('export_filename')}{ext}",
            filetypes=[(kind, f"*{ext}")],
        )
        return Path(name) if name else None

    def export_markdown(self) -> None:
        path = self._ask_export_path(".md", "Markdown")
        if path:
            export.write_markdown(self.data, path)
            messagebox.showinfo(t("export_title"), t("export_done", path=path))

    def export_csv(self) -> None:
        path = self._ask_export_path(".csv", "CSV")
        if path:
            export.write_csv(self.data, path)
            messagebox.showinfo(t("export_title"), t("export_done", path=path))

    def close(self) -> None:
        self.root.destroy()  # every change is already saved


def choose_language(root: tk.Tk, default: str) -> str | None:
    """Start-up dialog: pick the language for this session. None if it was closed.

    Under each language it shows which list will open, or that a new one with
    sample items will be made.
    """
    win = tk.Toplevel(root)
    win.title("Baby budget")
    win.resizable(False, False)
    result: list[str] = []

    def pick(lang: str) -> None:
        result.append(lang)
        win.destroy()

    body = ttk.Frame(win, padding=20)
    body.pack()
    ttk.Label(body, text="Изберете език\nChoose a language", justify="center",
              font=("TkDefaultFont", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 14))
    new_list = {"bg": "нов списък с примерни покупки", "en": "new list with sample items"}
    buttons = {}
    for col, lang in enumerate(("bg", "en")):
        path = settings.choose_file(lang)
        hint = path.name if path.exists() else new_list[lang]
        buttons[lang] = ttk.Button(body, text=LANGUAGE_NAMES[lang], width=18,
                                   command=lambda lang=lang: pick(lang))
        buttons[lang].grid(row=1, column=col, padx=8, ipady=6)
        ttk.Label(body, text=hint, foreground="#666666", wraplength=190, justify="center").grid(
            row=2, column=col, padx=8, pady=(6, 0))
    win.bind("<Return>", lambda e: pick(str(win.focus_get() == buttons["en"] and "en" or "bg")))
    win.bind("<Escape>", lambda e: win.destroy())
    buttons[default].focus_set()
    win.update_idletasks()
    x = (win.winfo_screenwidth() - win.winfo_reqwidth()) // 2
    y = (win.winfo_screenheight() - win.winfo_reqheight()) // 3
    win.geometry(f"+{x}+{y}")
    win.grab_set()
    win.wait_window()
    return result[0] if result else None


def run(data: Path | None = None, language: str | None = None) -> None:
    """Start the app.

    Without ``language`` the user picks one first. Without ``data`` the list used
    last in that language opens, or a new one with the sample items is made.
    A given ``data`` file that exists decides the language itself.
    """
    try:  # crisp text on high-DPI Windows screens
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    root = tk.Tk()

    def report(exc_type, exc, tb) -> None:
        details = "".join(traceback.format_exception(exc_type, exc, tb))
        messagebox.showerror(t("unexpected_error"), details[-3000:], parent=root)

    # Started with pythonw there is no console, so show errors in a dialog.
    root.report_callback_exception = report
    root.withdraw()
    if data is not None and data.exists():
        language = settings.file_language(data) or language
    if language is None:
        language = choose_language(root, settings.last_language() or system_language())
        if language is None:
            root.destroy()
            return
    path = data or settings.choose_file(language)
    root.deiconify()
    try:
        App(root, path, language)
    except SystemExit:
        root.destroy()
        return
    except Exception:
        report(*sys.exc_info())
        root.destroy()
        return
    root.mainloop()
