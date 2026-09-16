"""데이터 모델: Transaction, Category, Budget.

저장소(CSV I/O)와 서비스 계층 사이의 계약을 정의한다.
tags는 메모리상 list[str], CSV 저장 시 쉼표 구분 문자열로 인코딩된다
(인코딩은 저장소 계층에서 담당).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

TransactionType = Literal["income", "expense"]


@dataclass
class Transaction:
    """단일 수입/지출 거래."""

    id: str
    date: str  # YYYY-MM-DD
    type: TransactionType
    category: str
    amount: int  # 양수 정수 (원 단위)
    memo: str = ""
    tags: list[str] = field(default_factory=list)
    recurring_id: str | None = None


@dataclass
class Category:
    """거래 분류."""

    name: str


@dataclass
class Budget:
    """월 단위 예산."""

    month: str  # YYYY-MM
    amount: int  # 양수 정수


@dataclass
class RecurringRule:
    """매월 같은 날짜에 생성할 반복 거래 규칙."""

    id: str
    type: TransactionType
    day: int
    category: str
    amount: int
    memo: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class MonthlySummary:
    """월별 집계 결과."""

    month: str
    income: int
    expense: int
    category_expenses: list[tuple[str, int]]
    transaction_count: int
    budget: int | None = None

    @property
    def balance(self) -> int:
        return self.income - self.expense

    @property
    def budget_usage(self) -> float | None:
        if self.budget is None:
            return None
        return self.expense / self.budget * 100

    @property
    def is_over_budget(self) -> bool:
        return self.budget is not None and self.expense > self.budget
