"""Shops and delivery, paid amounts, backups, damaged files, settings."""

import json

import pytest

from baby_budget import settings, storage
from baby_budget.budget import summarize
from baby_budget.model import Item, Option, Shop, ShoppingList


def chosen(name, price, shop="", **kw) -> Item:
    item = Item(name=name, **kw)
    item.add_option(Option(name=name, price=price, shop=shop))
    return item


def test_delivery_counted_once_per_shop_and_free_over_threshold():
    shops = {"aiko": Shop(shipping=5), "baby.bg": Shop(shipping=4, free_over=50)}
    items = [
        chosen("a", 20, "aiko"),
        chosen("b", 30, "aiko"),
        chosen("c", 60, "baby.bg"),       # over 50 -> free delivery
        chosen("d", 10, "unknown shop"),  # no terms -> no delivery
    ]
    s = summarize(items, shops)
    assert s.shipping == 5
    assert s.total == pytest.approx(125)
    assert summarize(items).shipping == 0  # section subtotals ignore delivery


def test_gifts_do_not_trigger_delivery():
    s = summarize([chosen("a", 20, "aiko", status="gift")], {"aiko": Shop(shipping=5)})
    assert s.shipping == 0 and s.total == 0


def test_paid_amount_replaces_planned_cost_and_includes_delivery():
    shops = {"aiko": Shop(shipping=5)}
    item = chosen("a", 100, "aiko", status="bought")
    item.paid = 97.5
    s = summarize([item], shops)
    assert (s.total, s.spent, s.shipping) == (97.5, 97.5, 0)

    item.status = "todo"  # paid only counts for bought items
    assert summarize([item], shops).total == 105


def test_bought_without_chosen_product_counts_when_paid():
    item = Item(name="Вана", status="bought", paid=25)
    s = summarize([item])
    assert (s.total, s.spent, s.unchosen_count) == (25, 25, 0)


def test_shops_and_paid_roundtrip():
    sl = ShoppingList(items=[chosen("a", 10, "aiko", paid=9)], shops={"aiko": Shop(5, 50)})
    restored = ShoppingList.from_dict(sl.to_dict())
    assert restored.to_dict() == sl.to_dict()
    assert restored.shop_names() == ["aiko"]


def test_backups_rotate(tmp_path):
    path = tmp_path / "list.json"
    storage.save(ShoppingList(), path)
    for _ in range(storage.KEEP_BACKUPS + 3):
        storage.backup(path)
    assert len(storage.list_backups(path)) == storage.KEEP_BACKUPS


def test_damaged_file_restored_from_latest_valid_backup(tmp_path):
    path = tmp_path / "list.json"
    storage.save(ShoppingList(items=[Item(name="Бебефон")]), path)
    storage.backup(path)
    newest = storage.backup(path)
    newest.write_text("{ broken", encoding="utf-8")  # a damaged backup is skipped
    path.write_text("{ also broken", encoding="utf-8")

    with pytest.raises(ValueError):
        storage.load(path)
    used = storage.restore_latest_valid(path)
    assert used is not None and used != newest
    assert storage.load(path).items[0].name == "Бебефон"
    assert (tmp_path / "list.json.damaged").exists()


def test_wrong_json_shape_is_reported_as_damage(tmp_path):
    path = tmp_path / "list.json"
    path.write_text('{"items": [1, 2]}', encoding="utf-8")
    with pytest.raises(ValueError):
        storage.load(path)


def test_settings_remember_last_file_per_language(tmp_path):
    assert settings.last_file("bg") is None and settings.last_language() is None
    settings.remember("bg", tmp_path / "bg.json")
    settings.remember("en", tmp_path / "en.json")
    assert settings.last_file("bg") == tmp_path / "bg.json"
    assert settings.last_file("en") == tmp_path / "en.json"
    assert settings.last_language() == "en"


def test_legacy_settings_are_read(tmp_path):
    lst = tmp_path / "old.json"
    storage.save(ShoppingList(language="bg"), lst)
    settings.config_dir().mkdir(parents=True)
    (settings.config_dir() / "settings.json").write_text(
        json.dumps({"last_file": str(lst)}), encoding="utf-8")
    assert settings.last_file("bg") == lst
    assert settings.last_file("en") is None


def test_choose_file_uses_last_list_of_that_language_else_a_new_one(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "default_data_file", lambda lang: tmp_path / f"baby-budget-{lang}.json")
    bg_list = tmp_path / "ours.json"
    storage.save(ShoppingList(language="bg"), bg_list)
    settings.remember("bg", bg_list)
    assert settings.choose_file("bg") == bg_list
    assert settings.choose_file("en") == tmp_path / "baby-budget-en.json"  # new
    assert not (tmp_path / "baby-budget-en.json").exists()

    # a remembered file in the wrong language is never picked
    settings.remember("en", bg_list)
    assert settings.choose_file("en") == tmp_path / "baby-budget-en.json"
    # and an existing default file in the other language is not overwritten
    storage.save(ShoppingList(language="bg"), tmp_path / "baby-budget-en.json")
    assert settings.choose_file("en") == tmp_path / "baby-budget-en-2.json"

