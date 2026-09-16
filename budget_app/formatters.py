"""콘솔 출력 형식."""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from budget_app.models import Transaction


def format_money(amount: int) -> str:
    return f"{amount:,}원"


def transaction_lines(items: Iterable[Transaction]) -> Iterator[str]:
    for item in items:
        tags = ",".join(item.tags) or "-"
        memo = item.memo or "-"
        yield (
            f"{item.date} | {item.type:<7} | {item.category:<12} | "
            f"{format_money(item.amount):>14} | {memo} | tags={tags} | id={item.id}"
        )
