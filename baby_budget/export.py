"""Export the final list to Markdown or CSV, in the active UI language."""

from __future__ import annotations

import csv
from pathlib import Path

from .budget import summarize
from .i18n import fmt_money, fmt_number, get_language, priority_label, status_label, t, target_text
from .model import PRIORITIES, Item, Option, ShoppingList


def csv_header() -> list[str]:
    return t("csv_header").split(";")


def status_text(item: Item) -> str:
    text = status_label(item.status)
    if item.is_gift and item.gift_from:
        text = t("status_gift_from", status=text, name=item.gift_from)
    return text


def _md_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def to_markdown(shopping_list: ShoppingList) -> str:
    cur = shopping_list.currency

    def money(value: float) -> str:
        return fmt_money(value, cur)

    s = summarize(shopping_list.items, shopping_list.shops)
    lines = [
        f"# {t('md_title')}",
        "",
        f"**{t('md_total', amount=money(s.total))}** · "
        + t("md_spent_left", spent=money(s.spent), left=money(s.remaining)),
        "",
        " · ".join(
            [f"{priority_label(p)}: {money(s.by_priority[p])}" for p in PRIORITIES]
            + ([t("shipping_line", amount=money(s.shipping))] if s.shipping else [])
        ),
        "",
        t("gifts", count=s.gift_count, received=s.gifts_received, amount=money(s.gift_value)),
    ]
    if shopping_list.target > 0:
        lines[3:3] = [
            f"{t('md_target', amount=money(shopping_list.target))} · "
            f"{target_text(shopping_list.target, s.total, cur)}",
            "",
        ]
    if s.unchosen_count:
        lines.append(t("unchosen", count=s.unchosen_count, amount=money(s.unchosen_min)))

    for section in shopping_list.sections():
        items = shopping_list.items_in(section)
        lines += [
            "",
            f"## {section} ({money(summarize(items).total)})",
            "",
            t("md_header"),
            "|---|---|---:|---:|---:|---|---|",
        ]
        for item in items:
            cost = money(item.effective_cost) if item.effective_cost is not None else ""
            tail = f"| {priority_label(item.priority)} | {_md_cell(status_text(item))} |"
            chosen = item.chosen_options
            if not chosen:
                lines.append(
                    f"| {_md_cell(item.name)} | {t('not_chosen')} |  | {item.quantity} | {cost} {tail}"
                )
                continue
            # several chosen products: the item's name and total go on the first row only
            for n, opt in enumerate(chosen):
                product = f"[{_md_cell(opt.name)}]({opt.url})" if opt.url else _md_cell(opt.name)
                if opt.shop:
                    product += f" ({_md_cell(opt.shop)})"
                first = n == 0
                lines.append(
                    f"| {_md_cell(item.name) if first else ''} | {product} | {money(opt.price)} "
                    f"| {opt.quantity} | {cost if first else ''} {tail if first else '|  |  |'}"
                )
    return "\n".join(lines) + "\n"


def write_markdown(shopping_list: ShoppingList, path: Path) -> None:
    path.write_text(to_markdown(shopping_list), encoding="utf-8")


def write_csv(shopping_list: ShoppingList, path: Path) -> None:
    """Excel-friendly CSV with BOM, one row per chosen product.

    Bulgarian Excel expects ``;`` and comma decimals; English Excel expects ``,``.
    """
    delimiter = "," if get_language() == "en" else ";"
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow(csv_header())
        for section in shopping_list.sections():
            for item in shopping_list.items_in(section):
                for n, opt in enumerate(item.chosen_options or [None]):
                    writer.writerow(_csv_row(section, item, opt, first=n == 0))


def _csv_row(section: str, item: Item, opt: Option | None, first: bool) -> list:
    if opt is None:
        cost = item.effective_cost
    elif item.is_paid:  # the paid amount covers all chosen products: show it once
        cost = item.paid if first else None
    else:
        cost = opt.cost
    return [
        section,
        item.name,
        opt.name if opt else "",
        fmt_number(opt.price) if opt else "",
        opt.quantity if opt else item.quantity,
        fmt_number(cost) if cost is not None else "",
        priority_label(item.priority),
        status_label(item.status),
        item.gift_from if item.is_gift else "",
        opt.shop if opt else "",
        opt.url if opt else "",
        opt.description if opt else "",
        item.notes,
    ]
