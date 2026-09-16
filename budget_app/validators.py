"""CLI와 서비스 계층에서 공유하는 입력 검증 함수."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, cast

from budget_app.errors import InvalidInputError
from budget_app.models import TransactionType


def validate_date(value: str, field_name: str = "날짜") -> str:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise InvalidInputError(
            f"{field_name} 형식이 올바르지 않습니다: {value}",
            "YYYY-MM-DD 형식으로 입력하세요. 예: 2026-09-16",
        ) from exc
    if parsed.isoformat() != value:
        raise InvalidInputError(
            f"{field_name} 형식이 올바르지 않습니다: {value}",
            "연도와 월, 일을 각각 4자리-2자리-2자리로 입력하세요.",
        )
    return value


def validate_month(value: str) -> str:
    try:
        parsed = date.fromisoformat(f"{value}-01")
    except (TypeError, ValueError) as exc:
        raise InvalidInputError(
            f"월 형식이 올바르지 않습니다: {value}",
            "YYYY-MM 형식으로 입력하세요. 예: 2026-09",
        ) from exc
    if parsed.strftime("%Y-%m") != value:
        raise InvalidInputError(
            f"월 형식이 올바르지 않습니다: {value}",
            "연도와 월을 각각 4자리-2자리로 입력하세요.",
        )
    return value


def validate_type(value: str) -> TransactionType:
    if value not in ("income", "expense"):
        raise InvalidInputError(
            f"허용되지 않는 거래 타입입니다: {value}",
            "income 또는 expense 중 하나를 입력하세요.",
        )
    return cast(TransactionType, value)


def validate_positive_int(value: Any, field_name: str = "금액") -> int:
    try:
        if isinstance(value, bool):
            raise ValueError
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise InvalidInputError(
            f"{field_name}은 정수여야 합니다: {value}",
            "0보다 큰 정수를 입력하세요.",
        ) from exc
    if str(value).strip() != str(number) or number <= 0:
        raise InvalidInputError(
            f"{field_name}은 0보다 큰 정수여야 합니다: {value}",
            "소수점이나 쉼표 없이 양의 정수를 입력하세요.",
        )
    return number


def validate_non_negative_int(value: Any, field_name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise InvalidInputError(
            f"{field_name}은 정수여야 합니다: {value}",
            "0 이상의 정수를 입력하세요.",
        ) from exc
    if str(value).strip() != str(number) or number < 0:
        raise InvalidInputError(
            f"{field_name}은 0 이상의 정수여야 합니다: {value}",
            "0 이상의 정수를 입력하세요.",
        )
    return number


def validate_category_name(value: str) -> str:
    if not isinstance(value, str):
        raise InvalidInputError("카테고리 이름이 문자열이 아닙니다.", "카테고리 값을 확인하세요.")
    name = value.strip()
    if not name:
        raise InvalidInputError("카테고리 이름이 비어 있습니다.", "한 글자 이상 입력하세요.")
    if "\n" in name or "\r" in name:
        raise InvalidInputError("카테고리 이름에 줄바꿈을 사용할 수 없습니다.")
    return name


def parse_tags(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    raw_tags = value if isinstance(value, list) else value.split(",")
    result: list[str] = []
    seen: set[str] = set()
    for raw_tag in raw_tags:
        tag = str(raw_tag).strip()
        if tag and tag not in seen:
            seen.add(tag)
            result.append(tag)
    return result


def validate_readable_file(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_file():
        raise InvalidInputError(
            f"가져올 파일을 찾을 수 없습니다: {path}",
            "--from 경로와 파일 이름을 확인하세요.",
        )
    return path
