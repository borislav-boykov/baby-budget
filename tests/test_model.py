import pytest

from baby_budget.model import Item, Option, ShoppingList


def make_list() -> ShoppingList:
    return ShoppingList(
        items=[
            Item(name="Креватче", section="Сън", id="a"),
            Item(name="Количка", section="Разходка", id="b"),
            Item(name="Бебефон", section="Сън", id="c"),
        ]
    )


def test_first_option_is_chosen_automatically():
    item = Item(name="Бебефон")
    item.add_option(Option(name="Philips", price=80, id="p"))
    item.add_option(Option(name="Motorola", price=60, id="m"))
    assert item.chosen_ids == ["p"]


def test_cost_uses_chosen_option_and_quantity():
    item = Item(name="Шишета", quantity=3)
    assert item.cost is None
    item.add_option(Option(name="NUK", price=7.5, id="n"))
    assert item.cost == pytest.approx(22.5)


def test_several_options_can_be_chosen_each_with_quantity():
    item = Item(name="Шишета", quantity=3)
    item.add_option(Option(name="Lansinoh", price=7, id="l"))  # auto-chosen, takes qty 3
    item.add_option(Option(name="NUK", price=10, id="n", quantity=2))
    item.toggle_choice("n")
    assert [o.name for o in item.chosen_options] == ["Lansinoh", "NUK"]
    assert item.cost == pytest.approx(3 * 7 + 2 * 10)
    assert item.chosen_quantity == 5

    item.toggle_choice("l")
    assert item.cost == pytest.approx(20)
    item.remove_option("n")
    assert item.chosen_ids == [] and item.cost is None
    with pytest.raises(KeyError):
        item.toggle_choice("missing")


def test_option_chosen_alone_takes_needed_quantity_and_follows_it():
    item = Item(name="Кърпички", quantity=10)
    item.options = [Option(name="A", price=2, id="a"), Option(name="B", price=3, id="b")]
    item.toggle_choice("b")
    assert item.find_option("b").quantity == 10
    item.set_quantity(12)
    assert item.find_option("b").quantity == 12
    item.toggle_choice("a")  # second choice keeps its own quantity
    item.set_quantity(20)     # with two chosen, quantities stay as they are
    assert (item.find_option("a").quantity, item.find_option("b").quantity) == (1, 12)


def test_move_section():
    sl = make_list()
    assert sl.move_section("Разходка", -1)
    assert sl.sections() == ["Разходка", "Сън"]
    assert [i.id for i in sl.items] == ["b", "a", "c"]
    assert not sl.move_section("Разходка", -1)


def test_version_1_file_is_migrated():
    old = {"name": "Шишета", "quantity": 3, "chosen_id": "x",
           "options": [{"id": "x", "name": "NUK", "price": 7}, {"id": "y", "name": "Avent", "price": 9}]}
    item = Item.from_dict(old)
    assert item.chosen_ids == ["x"]
    assert item.cost == pytest.approx(21)
    assert item.find_option("y").quantity == 3


def test_sections_keep_first_appearance_order():
    assert make_list().sections() == ["Сън", "Разходка"]


def test_move_swaps_only_within_section():
    sl = make_list()
    assert sl.move("c", -1)
    assert [i.id for i in sl.items_in("Сън")] == ["c", "a"]
    assert not sl.move("c", -1)
    assert not sl.move("b", 1)


def test_add_after_and_remove_section():
    sl = make_list()
    sl.add(Item(name="Матрак", section="Сън", id="d"), after_id="a")
    assert [i.id for i in sl.items] == ["a", "d", "b", "c"]
    sl.remove_section("Сън")
    assert [i.id for i in sl.items] == ["b"]


def test_rename_section():
    sl = make_list()
    sl.rename_section("Сън", "Детска стая")
    assert sl.sections() == ["Детска стая", "Разходка"]


def test_roundtrip_and_tolerant_loading():
    sl = make_list()
    sl.items[0].add_option(Option(name="Lorelli", price=77, url="https://x", id="o"))
    restored = ShoppingList.from_dict(sl.to_dict())
    assert restored.to_dict() == sl.to_dict()

    broken = Item.from_dict({"name": "X", "priority": "??", "quantity": 0, "chosen_ids": ["nope"]})
    assert (broken.priority, broken.quantity, broken.chosen_ids) == ("must", 1, [])
