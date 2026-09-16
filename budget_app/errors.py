"""budget-app 커스텀 예외 계층.

사용자에게 보여줄 모든 예외는 BudgetAppError를 상속한다.
`@handle_errors` 데코레이터가 이들을 잡아 스택트레이스 대신
"원인 + 해결 힌트" 형태로 출력하고 프로세스를 비정상 종료(exit != 0)시킨다.
"""

from __future__ import annotations


class BudgetAppError(Exception):
    """사용자용 애플리케이션 오류의 기반 클래스."""

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


class InvalidInputError(BudgetAppError):
    """입력 형식/규칙 위반 (날짜, 금액, type 등)."""


class NotFoundError(BudgetAppError):
    """리소스(거래 id, 카테고리 등)를 찾을 수 없음."""


class ConflictError(BudgetAppError):
    """상태 규칙 위반 (사용 중 카테고리 삭제, 중복 등)."""


class StorageError(BudgetAppError):
    """저장소 계층 오류 (I/O 실패, 파일 포맷 손상 등)."""
