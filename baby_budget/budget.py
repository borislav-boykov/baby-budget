"""Budget totals computed from a list of items."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .model import PRIORITIES, Item, Shop


@dataclass(frozen=True)
class Summary:
    total: float
    """What we pay ourselves: chosen options (or the paid amount) plus delivery."""
    spent: float
    """Part of ``total`` already marked as bought."""
    shipping: float
    """Estimated delivery for orders not paid yet, included in ``total``."""
    by_priority: dict[str, float]
    gift_count: int
    gifts_received: int
    """Gifts already given to us (status ``gifted``)."""
    gift_value: float
    """Value of gifts: chosen option, or the cheapest one if none is chosen."""
    unchosen_count: int
    """Items we pay for that have no chosen option yet."""
    unchosen_min: float
    """Lower bound for those items, using their cheapest option."""

    @property
    def remaining(self) -> float:
        return self.total - self.spent


def summarize(items: Iterable[Item], shops: Mapping[str, Shop] | None = None) -> Summary:
    """Budget numbers. Delivery is only estimated when ``shops`` is given."""
    total = spent = gift_value = unchosen_min = 0.0
    order_values: dict[str, float] = defaultdict(float)
    gift_count = gifts_received = unchosen_count = 0
    by_priority = dict.fromkeys(PRIORITIES, 0.0)

    for item in items:
        if item.is_gift:
            cost = item.cost
            gift_count += 1
            gifts_received += item.status == "gifted"
            gift_value += cost if cost is not None else item.cheapest_cost() or 0.0
            continue
        cost = item.effective_cost
        if cost is None:
            unchosen_count += 1
            unchosen_min += item.cheapest_cost() or 0.0
            continue
        total += cost
        by_priority[item.priority] += cost
        if item.status == "bought":
            spent += cost
        if not item.is_paid:  # a paid amount already includes delivery
            for opt in item.chosen_options:
                if opt.shop:
                    order_values[opt.shop] += opt.cost

    shipping = 0.0
    if shops is not None:
        shipping = sum(
            shops.get(name, Shop()).shipping_for(value) for name, value in order_values.items()
        )

    return Summary(
        total=total + shipping,
        spent=spent,
        shipping=shipping,
        by_priority=by_priority,
        gift_count=gift_count,
        gifts_received=gifts_received,
        gift_value=gift_value,
        unchosen_count=unchosen_count,
        unchosen_min=unchosen_min,
    )
