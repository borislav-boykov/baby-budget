"""User-facing strings (Bulgarian / English) and language-aware money formatting.

The active language is module state: call ``set_language()`` once the data file
is loaded, then use ``t(key, **kwargs)`` everywhere a string is shown.
"""

from __future__ import annotations

import re

LANGUAGES = ("bg", "en")
LANGUAGE_NAMES = {"bg": "Български", "en": "English"}

STRINGS: dict[str, dict[str, str]] = {
    "bg": {
        # window and menus
        "app_title": "Бебе бюджет — {path}",
        "menu_file": "Файл",
        "menu_new_sample": "Нов списък с примерни покупки…",
        "sample_filename": "primeren-spisak",
        "wrong_language_title": "Друг език",
        "wrong_language": "Този списък е на {language}.\n\nЕзикът се избира при стартиране на "
                          "програмата – затворете я и я пуснете отново, като изберете {language}.",
        "menu_open": "Отвори…",
        "menu_save_as": "Запази като…",
        "menu_shops": "Магазини и доставка…",
        "json_files": "Списък (JSON)",
        "paid": "Платено (вкл. доставка)",
        "shop": "Магазин",
        "col_shop": "Магазин",
        "shipping_line": "в т.ч. доставки: {amount}",
        "shops_title": "Магазини и доставка",
        "shops_hint": "Доставката се брои веднъж за всеки магазин, от който има избран продукт.",
        "col_shipping": "Доставка",
        "col_free_over": "Безплатна над",
        "shipping": "Доставка ({currency})",
        "free_over": "Безплатна доставка над ({currency}, 0 = никога)",
        "close": "Затвори",
        "conflict_title": "Файлът е променен",
        "conflict_msg": "Файлът е променен от друго място (например от другия компютър).\n\n"
                        "Да – зареди новата версия (последната ти промяна се губи)\n"
                        "Не – запиши твоята версия върху нея",
        "reloaded": "Заредени са промени, направени от друго място.",
        "corrupt_title": "Повреден файл",
        "corrupt_restore": "Файлът не може да се прочете:\n{path}\n\n{error}\n\n"
                           "Да заредя ли последното работещо резервно копие?",
        "corrupt_restored": "Заредено е резервно копие:\n{backup}\n\n"
                            "Повреденият файл е запазен като {damaged}.",
        "corrupt_no_backup": "Няма работещо резервно копие. Програмата ще се затвори.",
        "unexpected_error": "Неочаквана грешка",
        "menu_export_md": "Експорт в Markdown…",
        "menu_export_csv": "Експорт в CSV (Excel)…",
        "menu_exit": "Изход",
        "menu_edit": "Редактиране",
        "menu_new_item": "Нова покупка",
        "menu_delete": "Изтрий избраното",
        "menu_move_up": "Премести нагоре",
        "menu_move_down": "Премести надолу",
        "menu_rename_section": "Преименувай раздел…",
        # list
        "add_item": "+ Покупка",
        "delete": "Изтрий",
        "hide_done": "Скрий купени и подаръци",
        "priority_filter": "Приоритет:",
        "all": "Всички",
        "col_item": "Покупка",
        "col_choice": "Избран продукт",
        "col_qty": "Бр.",
        "col_cost": "Сума",
        "col_priority": "Приоритет",
        "col_status": "Статус",
        "not_chosen": "— не е избран —",
        "no_options": "— няма продукти —",
        "other_section": "Други",
        # item form
        "item_frame": "Покупка",
        "name": "Име",
        "section": "Раздел",
        "quantity": "Нужни бр.",
        "priority": "Приоритет",
        "status": "Статус",
        "gift_from": "Подарък от",
        "notes": "Бележка",
        # options
        "options_frame": "Продукти за избор",
        "add_option": "+ Продукт",
        "edit": "Редактирай",
        "choose": "✔ Избери",
        "open_link": "Отвори линк",
        "col_product": "Продукт",
        "col_price": "Цена",
        "col_link": "Линк",
        "product": "Продукт",
        "price": "Цена ({currency})",
        "link": "Линк",
        "description": "Описание",
        "option_quantity": "Брой (ако е избран)",
        "invalid_quantity": "Броят трябва да е цяло число, поне 1.",
        # summary
        "total": "Нужен бюджет: {amount}",
        "spent_left": "Похарчено: {spent}   ·   Остава: {left}",
        "gifts": "Подаръци: {count}, получени {received} (~{amount})",
        "unchosen": "Без избран продукт: {count} (мин. {amount})",
        "target": "Целеви бюджет:",
        "target_left": "остават {amount}",
        "target_over": "над целта с {amount}",
        "target_empty": "въведи сума, в която искаш да се вместиш",
        "target_projected": "С неизбраните (мин. {amount}): {verdict}",
        "invalid_amount": "Невалидна сума",
        # dialogs
        "ok": "OK",
        "cancel": "Отказ",
        "new_item": "Нова покупка",
        "delete_title": "Изтриване",
        "confirm_delete_section": "Да изтрия ли раздел „{section}“ и всички {count} покупки в него?",
        "confirm_delete": "Да изтрия ли „{name}“?",
        "section_title": "Раздел",
        "select_section_first": "Първо избери раздел или покупка от него.",
        "rename_title": "Преименуване",
        "rename_prompt": "Ново име на раздела:",
        "new_option": "Нов продукт за „{name}“",
        "edit_option": "Редактиране на продукт",
        "error": "Грешка",
        "need_product_name": "Въведи име на продукта.",
        "invalid_price": "Невалидна цена: {value}",
        "choose_title": "Избор",
        "select_option_first": "Първо маркирай продукт от списъка.",
        "save_error": "Грешка при запис",
        "export_title": "Експорт",
        "export_done": "Записано в:\n{path}",
        "export_filename": "spisak-final",
        # export
        "md_title": "Списък за бебето",
        "md_total": "Нужен бюджет: {amount}",
        "md_spent_left": "похарчено {spent} · остава {left}",
        "md_target": "Целеви бюджет: {amount}",
        "md_header": "| Покупка | Избран продукт | Цена | Бр. | Сума | Приоритет | Статус |",
        "status_gift_from": "{status} от {name}",
        "csv_header": "Раздел;Покупка;Избран продукт;Цена;Количество;Сума;Приоритет;Статус;"
                      "Подарък от;Магазин;Линк;Описание;Бележка",
        # enums
        "priority_must": "Задължително",
        "priority_nice": "Желателно",
        "priority_later": "По-късно",
        "status_todo": "За купуване",
        "status_bought": "Купено",
        "status_gift": "Ще бъде подарено",
        "status_gifted": "Подарено",
    },
    "en": {
        "app_title": "Baby budget — {path}",
        "menu_file": "File",
        "menu_new_sample": "New list with sample items…",
        "sample_filename": "sample-list",
        "wrong_language_title": "Different language",
        "wrong_language": "This list is in {language}.\n\nThe language is chosen when the app "
                          "starts – close it, start it again and choose {language}.",
        "menu_open": "Open…",
        "menu_save_as": "Save as…",
        "menu_shops": "Shops and delivery…",
        "json_files": "List (JSON)",
        "paid": "Paid (incl. delivery)",
        "shop": "Shop",
        "col_shop": "Shop",
        "shipping_line": "incl. delivery: {amount}",
        "shops_title": "Shops and delivery",
        "shops_hint": "Delivery is counted once for every shop that has a chosen product.",
        "col_shipping": "Delivery",
        "col_free_over": "Free over",
        "shipping": "Delivery ({currency})",
        "free_over": "Free delivery over ({currency}, 0 = never)",
        "close": "Close",
        "conflict_title": "File changed",
        "conflict_msg": "The file was changed elsewhere (for example on the other computer).\n\n"
                        "Yes – load the new version (your last change is lost)\n"
                        "No – save your version over it",
        "reloaded": "Loaded changes made elsewhere.",
        "corrupt_title": "Damaged file",
        "corrupt_restore": "The file cannot be read:\n{path}\n\n{error}\n\n"
                           "Load the latest working backup?",
        "corrupt_restored": "Loaded backup:\n{backup}\n\n"
                            "The damaged file was kept as {damaged}.",
        "corrupt_no_backup": "No working backup found. The app will close.",
        "unexpected_error": "Unexpected error",
        "menu_export_md": "Export to Markdown…",
        "menu_export_csv": "Export to CSV (Excel)…",
        "menu_exit": "Exit",
        "menu_edit": "Edit",
        "menu_new_item": "New item",
        "menu_delete": "Delete selected",
        "menu_move_up": "Move up",
        "menu_move_down": "Move down",
        "menu_rename_section": "Rename section…",
        "add_item": "+ Item",
        "delete": "Delete",
        "hide_done": "Hide bought and gifts",
        "priority_filter": "Priority:",
        "all": "All",
        "col_item": "Item",
        "col_choice": "Chosen product",
        "col_qty": "Qty",
        "col_cost": "Cost",
        "col_priority": "Priority",
        "col_status": "Status",
        "not_chosen": "— not chosen —",
        "no_options": "— no products —",
        "other_section": "Other",
        "item_frame": "Item",
        "name": "Name",
        "section": "Section",
        "quantity": "Needed",
        "priority": "Priority",
        "status": "Status",
        "gift_from": "Gift from",
        "notes": "Notes",
        "options_frame": "Products to choose from",
        "add_option": "+ Product",
        "edit": "Edit",
        "choose": "✔ Choose",
        "open_link": "Open link",
        "col_product": "Product",
        "col_price": "Price",
        "col_link": "Link",
        "product": "Product",
        "price": "Price ({currency})",
        "link": "Link",
        "description": "Description",
        "option_quantity": "Quantity (if chosen)",
        "invalid_quantity": "Quantity must be a whole number, at least 1.",
        "total": "Budget needed: {amount}",
        "spent_left": "Spent: {spent}   ·   Left: {left}",
        "gifts": "Gifts: {count}, {received} received (~{amount})",
        "unchosen": "No product chosen: {count} (min. {amount})",
        "target": "Target budget:",
        "target_left": "{amount} left",
        "target_over": "{amount} over target",
        "target_empty": "enter the amount you want to stay within",
        "target_projected": "Incl. unchosen (min. {amount}): {verdict}",
        "invalid_amount": "Invalid amount",
        "ok": "OK",
        "cancel": "Cancel",
        "new_item": "New item",
        "delete_title": "Delete",
        "confirm_delete_section": "Delete section “{section}” and all {count} items in it?",
        "confirm_delete": "Delete “{name}”?",
        "section_title": "Section",
        "select_section_first": "Select a section or one of its items first.",
        "rename_title": "Rename",
        "rename_prompt": "New section name:",
        "new_option": "New product for “{name}”",
        "edit_option": "Edit product",
        "error": "Error",
        "need_product_name": "Enter a product name.",
        "invalid_price": "Invalid price: {value}",
        "choose_title": "Choose",
        "select_option_first": "Select a product in the list first.",
        "save_error": "Save failed",
        "export_title": "Export",
        "export_done": "Saved to:\n{path}",
        "export_filename": "baby-list-final",
        "md_title": "Baby shopping list",
        "md_total": "Budget needed: {amount}",
        "md_spent_left": "spent {spent} · left {left}",
        "md_target": "Target budget: {amount}",
        "md_header": "| Item | Chosen product | Price | Qty | Cost | Priority | Status |",
        "status_gift_from": "{status} by {name}",
        "csv_header": "Section;Item;Chosen product;Price;Quantity;Cost;Priority;Status;"
                      "Gift from;Shop;Link;Description;Notes",
        "priority_must": "Must have",
        "priority_nice": "Nice to have",
        "priority_later": "Later",
        "status_todo": "To buy",
        "status_bought": "Bought",
        "status_gift": "To be gifted",
        "status_gifted": "Gifted",
    },
}

_language = "bg"


def system_language() -> str:
    """Bulgarian if the operating system is set to Bulgarian, else English."""
    import locale

    try:
        name = locale.getlocale()[0] or ""
    except ValueError:
        name = ""
    return "bg" if name.lower().startswith(("bg", "bulgarian")) else "en"


def set_language(lang: str) -> None:
    global _language
    if lang not in LANGUAGES:
        raise ValueError(f"unsupported language: {lang}")
    _language = lang


def get_language() -> str:
    return _language


def t(key: str, **kwargs) -> str:
    text = STRINGS[_language][key]
    return text.format(**kwargs) if kwargs else text


def priority_label(priority: str) -> str:
    return t(f"priority_{priority}")


def status_label(status: str) -> str:
    return t(f"status_{status}")


def fmt_money(value: float, currency: str = "€") -> str:
    """``1 234,50 €`` in Bulgarian, ``€1,234.50`` in English."""
    if _language == "en":
        return f"{currency}{value:,.2f}"
    text = f"{value:,.2f}".replace(",", " ").replace(".", ",")
    return f"{text} {currency}"


def target_text(target: float, amount: float, currency: str = "€") -> str:
    """How an amount compares to the target: ``"остават X"`` / ``"над целта с X"``."""
    gap = target - amount
    if gap >= 0:
        return t("target_left", amount=fmt_money(gap, currency))
    return t("target_over", amount=fmt_money(-gap, currency))


def fmt_number(value: float) -> str:
    """Plain price for editing/CSV: ``1234,50`` (bg) or ``1234.50`` (en)."""
    text = f"{value:.2f}"
    return text if _language == "en" else text.replace(".", ",")


def parse_price(text: str) -> float:
    """Parse a price typed by the user. Empty means 0.

    Bulgarian: ``12,50``, ``12.50`` and ``1 234,50 €`` all work.
    English: commas are thousands separators (``1,234.50``).
    """
    cleaned = re.sub(r"[^\d,.\-]", "", text)
    if not cleaned:
        return 0.0
    if _language == "en" or ("," in cleaned and "." in cleaned):
        cleaned = cleaned.replace(",", "")
    else:
        cleaned = cleaned.replace(",", ".")
    value = float(cleaned)
    if value < 0:
        raise ValueError("price cannot be negative")
    return value
