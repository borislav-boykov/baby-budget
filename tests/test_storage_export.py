import csv

import pytest

from baby_budget import export, storage
from baby_budget.i18n import fmt_money, parse_price
from baby_budget.model import Item, Option, ShoppingList


@pytest.mark.parametrize(
    "text, expected",
    [("12,50", 12.5), ("12.50", 12.5), ("1 234,50 €", 1234.5), ("1,234.50", 1234.5), ("", 0.0)],
)
def test_parse_price(text, expected):
    assert parse_price(text) == pytest.approx(expected)


@pytest.mark.parametrize("text", ["abc,", "-5"])
def test_parse_price_rejects_invalid(text):
    with pytest.raises(ValueError):
        parse_price(text)


def test_fmt_money():
    assert fmt_money(1234.5) == "1 234,50 €"


def test_missing_file_gives_template(tmp_path):
    sl = storage.load(tmp_path / "none.json")
    assert len(sl.items) > 10


def test_save_load_roundtrip_and_backup(tmp_path):
    path = tmp_path / "data.json"
    sl = ShoppingList(items=[Item(name="Бебефон", section="Сън")])
    storage.save(sl, path)
    assert storage.load(path).to_dict() == sl.to_dict()
    assert not (tmp_path / "data.json.tmp").exists()


def sample() -> ShoppingList:
    monitor = Item(name="Бебефон", section="Сън")
    monitor.add_option(Option(name="Philips | SCD", price=89, url="https://example.com"))
    chair = Item(name="Шезлонг", section="Игра", status="gift", gift_from="Мария")
    return ShoppingList(items=[monitor, chair, Item(name="Вана", section="Сън")])


def test_markdown_export():
    md = export.to_markdown(sample())
    assert "**Нужен бюджет: 89,00 €**" in md
    assert "[Philips \\| SCD](https://example.com)" in md
    assert "Ще бъде подарено от Мария" in md
    assert "— не е избран —" in md


def test_csv_export(tmp_path):
    path = tmp_path / "out.csv"
    export.write_csv(sample(), path)
    with path.open(encoding="utf-8-sig") as f:
        rows = list(csv.reader(f, delimiter=";"))
    assert rows[0] == export.csv_header()
    assert [r[1] for r in rows[1:]] == ["Бебефон", "Вана", "Шезлонг"]
    assert rows[1][5] == "89,00"


def test_target_is_saved_and_exported(tmp_path):
    sl = sample()
    sl.target = 50
    path = tmp_path / "t.json"
    storage.save(sl, path)
    assert storage.load(path).target == 50
    assert "Целеви бюджет: 50,00 € · над целта с 39,00 €" in export.to_markdown(sl)


def test_export_lists_every_chosen_product(tmp_path):
    item = Item(name="Шишета", section="Хранене")
    item.add_option(Option(name="Lansinoh", price=7, quantity=2))
    nuk = Option(name="NUK", price=10, shop="dm")
    item.add_option(nuk)
    item.toggle_choice(nuk.id)
    sl = ShoppingList(items=[item])

    md = export.to_markdown(sl)
    assert "| Шишета | Lansinoh | 7,00 € | 1 | 17,00 €" in md  # first option took qty 1
    assert "| NUK (dm) | 10,00 € | 1 |" in md

    path = tmp_path / "out.csv"
    export.write_csv(sl, path)
    rows = path.read_text(encoding="utf-8-sig").splitlines()[1:]
    assert len(rows) == 2 and rows[1].startswith("Хранене;Шишета;NUK;10,00;1;10,00")
