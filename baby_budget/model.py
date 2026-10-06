"""Data model: a shopping list of items, each with candidate product options.

An *item* is something you need (e.g. "bottles"). Each item holds any number of
*options* (e.g. Philips, NUK). One or more options can be chosen, each with its
own quantity; only chosen options count towards the budget.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

PRIORITIES = ("must", "nice", "later")
STATUSES = ("todo", "bought", "gift", "gifted")
GIFT_STATUSES = ("gift", "gifted")  # promised gift / gift already received
DEFAULT_SECTION = "Други"
SCHEMA_VERSION = 2  # 2: several chosen options per item, quantity per option


def new_id() -> str:
    return uuid.uuid4().hex[:8]


@dataclass
class Shop:
    """Delivery terms of a shop; delivery is charged once per shop we order from."""

    shipping: float = 0.0
    free_over: float = 0.0
    """Order value from which delivery is free; 0 means never free."""

    def shipping_for(self, order_value: float) -> float:
        if order_value <= 0 or (self.free_over and order_value >= self.free_over):
            return 0.0
        return self.shipping

    def to_dict(self) -> dict:
        return {"shipping": self.shipping, "free_over": self.free_over}

    @classmethod
    def from_dict(cls, d: dict) -> Shop:
        return cls(
            shipping=max(0.0, float(d.get("shipping") or 0)),
            free_over=max(0.0, float(d.get("free_over") or 0)),
        )


@dataclass
class Option:
    name: str
    price: float = 0.0
    url: str = ""
    description: str = ""
    shop: str = ""
    quantity: int = 1
    """How many of this product we buy if it is chosen."""
    id: str = field(default_factory=new_id)

    @property
    def cost(self) -> float:
        return self.price * self.quantity

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "quantity": self.quantity,
            "shop": self.shop,
            "url": self.url,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, d: dict, default_quantity: int = 1) -> Option:
        return cls(
            name=d.get("name", ""),
            price=float(d.get("price") or 0),
            url=d.get("url", ""),
            description=d.get("description", ""),
            shop=d.get("shop", ""),
            quantity=max(1, int(d.get("quantity") or default_quantity)),
            id=d.get("id") or new_id(),
        )


@dataclass
class Item:
    name: str
    section: str = DEFAULT_SECTION
    quantity: int = 1
    """How many we need; used for estimates before anything is chosen."""
    priority: str = "must"
    status: str = "todo"
    gift_from: str = ""
    notes: str = ""
    paid: float | None = None
    """What we actually paid for a bought item (all pieces, delivery included)."""
    options: list[Option] = field(default_factory=list)
    chosen_ids: list[str] = field(default_factory=list)
    id: str = field(default_factory=new_id)

    @property
    def is_gift(self) -> bool:
        return self.status in GIFT_STATUSES

    @property
    def is_paid(self) -> bool:
        return self.status == "bought" and self.paid is not None

    @property
    def chosen_options(self) -> list[Option]:
        return [o for o in self.options if o.id in self.chosen_ids]

    @property
    def cost(self) -> float | None:
        """Sum of chosen options (price × their quantity), or None if nothing is chosen."""
        chosen = self.chosen_options
        return sum(o.cost for o in chosen) if chosen else None

    @property
    def effective_cost(self) -> float | None:
        """The real amount if we entered what we paid, else the planned cost."""
        return self.paid if self.is_paid else self.cost

    @property
    def chosen_quantity(self) -> int:
        return sum(o.quantity for o in self.chosen_options)

    def cheapest_cost(self) -> float | None:
        if not self.options:
            return None
        return min(o.price for o in self.options) * self.quantity

    def find_option(self, option_id: str) -> Option | None:
        return next((o for o in self.options if o.id == option_id), None)

    def is_chosen(self, option_id: str) -> bool:
        return option_id in self.chosen_ids

    def set_quantity(self, quantity: int) -> None:
        """Change how many we need; with exactly one chosen option it follows along."""
        self.quantity = quantity
        chosen = self.chosen_options
        if len(chosen) == 1:
            chosen[0].quantity = quantity

    def add_option(self, option: Option) -> None:
        """Add an option; the very first option of an item is chosen automatically."""
        self.options.append(option)
        if len(self.options) == 1 and not self.chosen_ids:
            self.toggle_choice(option.id)

    def remove_option(self, option_id: str) -> None:
        self.options = [o for o in self.options if o.id != option_id]
        if option_id in self.chosen_ids:
            self.chosen_ids.remove(option_id)

    def toggle_choice(self, option_id: str) -> None:
        """Choose or un-choose an option. Several options may be chosen at once.

        An option chosen on its own takes the item's needed quantity.
        """
        option = self.find_option(option_id)
        if option is None:
            raise KeyError(option_id)
        if option_id in self.chosen_ids:
            self.chosen_ids.remove(option_id)
            return
        if not self.chosen_ids:
            option.quantity = self.quantity
        self.chosen_ids.append(option_id)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "section": self.section,
            "quantity": self.quantity,
            "priority": self.priority,
            "status": self.status,
            "gift_from": self.gift_from,
            "notes": self.notes,
            "paid": self.paid,
            "chosen_ids": list(self.chosen_ids),
            "options": [o.to_dict() for o in self.options],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Item:
        quantity = max(1, int(d.get("quantity") or 1))
        item = cls(
            name=d.get("name", ""),
            section=d.get("section") or DEFAULT_SECTION,
            quantity=quantity,
            priority=d.get("priority") if d.get("priority") in PRIORITIES else "must",
            status=d.get("status") if d.get("status") in STATUSES else "todo",
            gift_from=d.get("gift_from", ""),
            notes=d.get("notes", ""),
            paid=None if d.get("paid") is None else max(0.0, float(d["paid"])),
            # version 1 files have no per-option quantity: the item's quantity applied
            options=[Option.from_dict(o, quantity) for o in d.get("options", [])],
            id=d.get("id") or new_id(),
        )
        wanted = d.get("chosen_ids")
        if wanted is None:  # version 1: a single "chosen_id"
            wanted = [d["chosen_id"]] if d.get("chosen_id") else []
        item.chosen_ids = [i for i in dict.fromkeys(wanted) if item.find_option(i)]
        return item


@dataclass
class ShoppingList:
    items: list[Item] = field(default_factory=list)
    currency: str = "€"
    target: float = 0.0
    """Budget we aim to stay within; 0 means not set."""
    language: str = "bg"
    shops: dict[str, Shop] = field(default_factory=dict)

    def shop_names(self) -> list[str]:
        """Shops with delivery terms plus every shop used by an option."""
        used = {o.shop for i in self.items for o in i.options if o.shop}
        return sorted(used | set(self.shops), key=str.casefold)

    def get(self, item_id: str) -> Item:
        for item in self.items:
            if item.id == item_id:
                return item
        raise KeyError(item_id)

    def add(self, item: Item, after_id: str | None = None) -> None:
        if after_id is None:
            self.items.append(item)
        else:
            self.items.insert(self.items.index(self.get(after_id)) + 1, item)

    def remove(self, item_id: str) -> None:
        self.items.remove(self.get(item_id))

    def sections(self) -> list[str]:
        """Section names in order of first appearance."""
        return list(dict.fromkeys(i.section for i in self.items))

    def items_in(self, section: str) -> list[Item]:
        return [i for i in self.items if i.section == section]

    def move(self, item_id: str, delta: int) -> bool:
        """Swap an item with its previous (-1) or next (+1) neighbour in the same section."""
        item = self.get(item_id)
        siblings = self.items_in(item.section)
        pos = siblings.index(item) + delta
        if not 0 <= pos < len(siblings):
            return False
        a, b = self.items.index(item), self.items.index(siblings[pos])
        self.items[a], self.items[b] = self.items[b], self.items[a]
        return True

    def move_section(self, section: str, delta: int) -> bool:
        """Move a whole section up (-1) or down (+1) among the sections."""
        order = self.sections()
        pos = order.index(section)
        new = pos + delta
        if not 0 <= new < len(order):
            return False
        order[pos], order[new] = order[new], order[pos]
        self.items = [item for name in order for item in self.items_in(name)]
        return True

    def rename_section(self, old: str, new: str) -> None:
        for item in self.items_in(old):
            item.section = new

    def remove_section(self, section: str) -> None:
        self.items = [i for i in self.items if i.section != section]

    def to_dict(self) -> dict:
        return {
            "version": SCHEMA_VERSION,
            "currency": self.currency,
            "target": self.target,
            "language": self.language,
            "shops": {name: shop.to_dict() for name, shop in self.shops.items()},
            "items": [i.to_dict() for i in self.items],
        }

    @classmethod
    def from_dict(cls, d: dict) -> ShoppingList:
        return cls(
            items=[Item.from_dict(i) for i in d.get("items", [])],
            currency=d.get("currency") or "€",
            target=max(0.0, float(d.get("target") or 0)),
            language=d.get("language") if d.get("language") in ("bg", "en") else "bg",
            shops={name: Shop.from_dict(s) for name, s in (d.get("shops") or {}).items()},
        )
