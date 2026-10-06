import pytest

from baby_budget import export, i18n
from baby_budget.model import Item, Option, ShoppingList
from baby_budget.templates import default_list


def test_every_language_has_the_same_keys():
    assert set(i18n.STRINGS["bg"]) == set(i18n.STRINGS["en"])


def test_target_text_in_both_languages():
    assert i18n.target_text(500, 450) == "остават 50,00 €"
    assert i18n.target_text(500, 620) == "над целта с 120,00 €"
    i18n.set_language("en")
    assert i18n.target_text(500, 450) == "€50.00 left"
    assert i18n.target_text(500, 620) == "€120.00 over target"


def test_english_money_format_and_parsing():
    i18n.set_language("en")
    assert i18n.fmt_money(1234.5) == "€1,234.50"
    assert i18n.fmt_number(12.5) == "12.50"
    assert i18n.parse_price("1,200") == 1200
    assert i18n.parse_price("€12.50") == 12.5


def test_unknown_language_rejected():
    with pytest.raises(ValueError):
        i18n.set_language("de")


def test_english_template_and_export(tmp_path):
    sl = default_list("en")
    assert sl.language == "en" and sl.items[0].section == "Sleep & nursery"

    i18n.set_language("en")
    item = Item(name="Baby monitor", section="Sleep", status="gift", gift_from="Maria")
    item.add_option(Option(name="Philips", price=89))
    md = export.to_markdown(ShoppingList(items=[item]))
    assert "# Baby shopping list" in md
    assert "To be gifted by Maria" in md

    path = tmp_path / "out.csv"
    export.write_csv(ShoppingList(items=[item]), path)
    header = path.read_text(encoding="utf-8-sig").splitlines()[0]
    assert header.startswith("Section,Item,Chosen product")


def test_language_saved_in_data():
    sl = ShoppingList(language="en")
    assert ShoppingList.from_dict(sl.to_dict()).language == "en"
    assert ShoppingList.from_dict({"language": "xx"}).language == "bg"


def test_starter_list_has_both_languages_and_no_unsafe_items():
    from baby_budget.templates import DEFAULT_ITEMS

    bg, en = default_list("bg"), default_list("en")
    assert len(bg.items) == len(en.items) == len(DEFAULT_ITEMS)
    assert bg.sections()[0] == "Сън и детска стая" and en.sections()[0] == "Sleep & nursery"
    names = " ".join(i.name.lower() for i in en.items)
    assert "bumper" not in names and "pillow" not in names.replace("nursing pillow", "")
