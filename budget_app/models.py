"""데이터 모델: Transaction, Category, Budget.

JSONL 저장소와 서비스 계층 사이에서 오가는 데이터 계약을 정의한다.
CSV import/export 경계에서만 tags를 쉼표 구분 문자열로 변환한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# 단순한 str 대신 Literal을 써서 잘못된 타입 값을 IDE/정적 분석 단계에서도 찾는다.
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
    # default_factory는 Transaction 인스턴스끼리 같은 가변 리스트를 공유하지 않게 한다.
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
        # 출력 계층이 계산식을 중복하지 않도록 요약 모델이 파생 값을 책임진다.
        return self.income - self.expense

    @property
    def budget_usage(self) -> float | None:
        if self.budget is None:
            return None
        return self.expense / self.budget * 100

    @property
    def is_over_budget(self) -> bool:
        return self.budget is not None and self.expense > self.budget
