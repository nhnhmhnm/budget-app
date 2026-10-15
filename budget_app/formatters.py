"""외부 라이브러리 없이 한글 표시 폭을 고려하는 콘솔 표 형식."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Iterator, Sequence

from budget_app.models import RecurringRule, Transaction


def format_money(amount: int) -> str:
    return f"{amount:,}원"


def display_width(value: str) -> int:
    """터미널에서 차지하는 셀 수를 계산한다."""

    width = 0
    for character in value:
        if unicodedata.combining(character):
            continue
        width += 2 if unicodedata.east_asian_width(character) in ("W", "F") else 1
    return width


def _truncate(value: str, width: int) -> str:
    if display_width(value) <= width:
        return value
    if width <= 1:
        return "…"[:width]
    result: list[str] = []
    used = 0
    for character in value:
        character_width = 0 if unicodedata.combining(character) else (
            2 if unicodedata.east_asian_width(character) in ("W", "F") else 1
        )
        if used + character_width > width - 1:
            break
        result.append(character)
        used += character_width
    return "".join(result) + "…"


def _pad(value: object, width: int, *, right: bool = False) -> str:
    text = _truncate(str(value), width)
    padding = " " * max(0, width - display_width(text))
    return padding + text if right else text + padding


def table_lines(
    headers: Sequence[str],
    rows: Iterable[Sequence[object]],
    widths: Sequence[int],
    *,
    right_aligned: frozenset[int] = frozenset(),
) -> Iterator[str]:
    """행을 미리 모으지 않고 헤더가 있는 고정 폭 표를 생성한다."""

    iterator = iter(rows)
    # 첫 행 하나만 미리 확인해 빈 결과에는 헤더조차 출력하지 않는다.
    # 이후 행은 계속 iterator에서 받아 표 형식도 스트리밍 특성을 유지한다.
    first = next(iterator, None)
    if first is None:
        return

    def render(row: Sequence[object]) -> str:
        return " | ".join(
            _pad(value, width, right=index in right_aligned)
            for index, (value, width) in enumerate(zip(row, widths))
        )

    yield render(headers)
    yield "-+-".join("-" * width for width in widths)
    yield render(first)
    for row in iterator:
        yield render(row)


def transaction_lines(items: Iterable[Transaction]) -> Iterator[str]:
    rows = (
        (
            item.date,
            item.type,
            item.category,
            format_money(item.amount),
            item.memo or "-",
            ",".join(item.tags) or "-",
            item.id,
        )
        for item in items
    )
    yield from table_lines(
        ("날짜", "타입", "카테고리", "금액", "메모", "태그", "ID"),
        rows,
        (10, 7, 12, 14, 20, 18, 32),
        right_aligned=frozenset({3}),
    )


def recurring_rule_lines(rules: Iterable[RecurringRule]) -> Iterator[str]:
    rows = (
        (
            f"{rule.day:02d}일",
            rule.type,
            rule.category,
            format_money(rule.amount),
            rule.memo or "-",
            ",".join(rule.tags) or "-",
            rule.id,
        )
        for rule in rules
    )
    yield from table_lines(
        ("매월", "타입", "카테고리", "금액", "메모", "태그", "ID"),
        rows,
        (6, 7, 12, 14, 20, 18, 32),
        right_aligned=frozenset({3}),
    )
