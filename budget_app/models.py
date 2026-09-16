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


@dataclass
class Category:
    """거래 분류."""

    name: str


@dataclass
class Budget:
    """월 단위 예산."""

    month: str  # YYYY-MM
    amount: int  # 양수 정수
