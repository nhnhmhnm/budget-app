"""CLI 공통 관심사를 분리한 데코레이터."""

from __future__ import annotations

import functools
import logging
import sys
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar, cast

from budget_app.errors import BudgetAppError

P = ParamSpec("P")
R = TypeVar("R")
logger = logging.getLogger("budget_app")


def measure_execution(func: Callable[P, R]) -> Callable[P, R]:
    """명령 실행 시간을 로그에 기록한다."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        started = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            logger.info("%s 실행 시간: %.3f초", func.__name__, time.perf_counter() - started)

    return wrapper


def command_boundary(func: Callable[P, int]) -> Callable[P, int]:
    """사용자용 오류를 스택 트레이스 없이 일관된 형식으로 출력한다."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> int:
        try:
            return func(*args, **kwargs)
        except BudgetAppError as exc:
            print(f"오류: {exc.message}", file=sys.stderr)
            if exc.hint:
                print(f"해결: {exc.hint}", file=sys.stderr)
            return 2
        except KeyboardInterrupt:
            print("\n작업이 취소되었습니다.", file=sys.stderr)
            return 130
        except Exception as exc:
            logger.error("처리하지 못한 예외: %s", type(exc).__name__)
            print(f"오류: 명령을 처리하지 못했습니다 ({type(exc).__name__}).", file=sys.stderr)
            print("해결: 입력과 데이터 파일 상태를 확인한 뒤 다시 시도하세요.", file=sys.stderr)
            return 1

    return cast(Callable[P, int], wrapper)
