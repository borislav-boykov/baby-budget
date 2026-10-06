import pytest

from baby_budget.budget import summarize
from baby_budget.model import Item, Option


def item(name, prices, chosen=0, **kw) -> Item:
    it = Item(name=name, **kw)
    for i, price in enumerate(prices):
        it.options.append(Option(name=f"{name}{i}", price=price, id=f"{name}{i}"))
    if chosen is not None and prices:
        it.toggle_choice(f"{name}{chosen}")
    return it


def test_totals_by_priority_and_spent():
    s = summarize([
        item("a", [100], priority="must", status="bought"),
        item("b", [20], priority="nice", quantity=2),
        item("c", [50], priority="later"),
    ])
    assert s.total == pytest.approx(190)
    assert s.spent == pytest.approx(100)
    assert s.remaining == pytest.approx(90)
    assert s.by_priority == {"must": 100, "nice": 40, "later": 50}


def test_gifts_are_excluded_from_budget():
    s = summarize([
        item("a", [30], status="gift"),
        item("b", [10, 25], chosen=None, status="gift"),
        item("c", [5]),
    ])
    assert s.total == pytest.approx(5)
    assert s.gift_count == 2
    assert s.gift_value == pytest.approx(40)  # 30 chosen + 10 cheapest


def test_unchosen_items_report_minimum():
    s = summarize([
        item("a", [80, 60], chosen=None, quantity=2),
        item("b", []),
    ])
    assert s.total == 0
    assert s.unchosen_count == 2
    assert s.unchosen_min == pytest.approx(120)




def test_received_gifts_are_counted_and_excluded():
    s = summarize([
        item("a", [30], status="gift"),
        item("b", [20], status="gifted"),
        item("c", [5]),
    ])
    assert s.total == pytest.approx(5)
    assert (s.gift_count, s.gifts_received) == (2, 1)
    assert s.gift_value == pytest.approx(50)
