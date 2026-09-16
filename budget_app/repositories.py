"""JSONL 기반 영구 저장소.

거래 조회는 한 행씩 역순으로 읽어 최신 등록순을 유지한다. 수정과 삭제는
같은 디렉터리의 임시 파일을 완성한 뒤 os.replace로 원자적으로 교체한다.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator

from budget_app.errors import StorageError
from budget_app.models import Budget, Category, Transaction

DEFAULT_CATEGORIES = ("food", "transport", "rent", "salary", "etc")


def _read_json_lines(path: Path) -> Iterator[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except (json.JSONDecodeError, TypeError) as exc:
                    raise StorageError(
                        f"저장 파일의 {line_number}번째 행이 손상되었습니다: {path}",
                        "파일을 복구하거나 백업본으로 교체하세요.",
                    ) from exc
                if not isinstance(value, dict):
                    raise StorageError(f"저장 파일의 {line_number}번째 행이 객체가 아닙니다: {path}")
                yield value
    except OSError as exc:
        raise StorageError(f"저장 파일을 읽지 못했습니다: {path}", "파일 권한을 확인하세요.") from exc


def _read_lines_reversed(path: Path, block_size: int = 8192) -> Iterator[str]:
    """파일 전체를 메모리에 올리지 않고 UTF-8 행을 뒤에서부터 반환한다."""

    try:
        with path.open("rb") as file:
            file.seek(0, os.SEEK_END)
            position = file.tell()
            buffer = b""
            while position > 0:
                read_size = min(block_size, position)
                position -= read_size
                file.seek(position)
                buffer = file.read(read_size) + buffer
                lines = buffer.split(b"\n")
                buffer = lines[0]
                for line in reversed(lines[1:]):
                    if line.strip():
                        yield line.decode("utf-8")
            if buffer.strip():
                yield buffer.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise StorageError(
            f"저장 파일을 역순으로 읽지 못했습니다: {path}",
            "파일이 UTF-8 JSONL 형식인지 확인하세요.",
        ) from exc


def _atomic_write(path: Path, values: Iterable[dict[str, Any]]) -> int:
    temp_path: Path | None = None
    count = 0
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
        ) as file:
            temp_path = Path(file.name)
            for value in values:
                file.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
                count += 1
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, path)
        return count
    except OSError as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise StorageError(f"저장 파일을 안전하게 갱신하지 못했습니다: {path}", "디스크 공간과 권한을 확인하세요.") from exc
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


class TransactionRepository:
    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / "transactions.jsonl"
        self._ensure_file()

    def _ensure_file(self) -> None:
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.path.touch(exist_ok=True)
        except OSError as exc:
            raise StorageError(f"거래 저장 파일을 준비하지 못했습니다: {self.path}") from exc

    @staticmethod
    def _from_dict(value: dict[str, Any]) -> Transaction:
        try:
            return Transaction(
                id=str(value["id"]),
                date=str(value["date"]),
                type=value["type"],
                category=str(value["category"]),
                amount=int(value["amount"]),
                memo=str(value.get("memo", "")),
                tags=[str(tag) for tag in value.get("tags", [])],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise StorageError("거래 저장 데이터의 필드가 올바르지 않습니다.", "transactions.jsonl을 확인하세요.") from exc

    def iter_all(self) -> Iterator[Transaction]:
        for value in _read_json_lines(self.path):
            yield self._from_dict(value)

    def iter_latest(self) -> Iterator[Transaction]:
        for line in _read_lines_reversed(self.path):
            try:
                value = json.loads(line)
            except (json.JSONDecodeError, TypeError) as exc:
                raise StorageError("거래 저장 데이터가 손상되었습니다.", "transactions.jsonl을 확인하세요.") from exc
            if not isinstance(value, dict):
                raise StorageError("거래 저장 데이터가 JSON 객체가 아닙니다.")
            yield self._from_dict(value)

    def add(self, transaction: Transaction) -> None:
        try:
            with self.path.open("a", encoding="utf-8", newline="\n") as file:
                file.write(json.dumps(asdict(transaction), ensure_ascii=False, separators=(",", ":")) + "\n")
        except OSError as exc:
            raise StorageError("거래를 저장하지 못했습니다.", "파일 권한과 디스크 공간을 확인하세요.") from exc

    def add_many(self, transactions: Iterable[Transaction]) -> int:
        existing = (asdict(transaction) for transaction in self.iter_all())
        additions = (asdict(transaction) for transaction in transactions)
        original_count = sum(1 for _ in self.iter_all())
        total_count = _atomic_write(self.path, _chain(existing, additions))
        return total_count - original_count

    def find(self, transaction_id: str) -> Transaction | None:
        return next((item for item in self.iter_all() if item.id == transaction_id), None)

    def update(self, transaction: Transaction) -> bool:
        found = False

        def values() -> Iterator[dict[str, Any]]:
            nonlocal found
            for current in self.iter_all():
                if current.id == transaction.id:
                    found = True
                    yield asdict(transaction)
                else:
                    yield asdict(current)

        _atomic_write(self.path, values())
        return found

    def delete(self, transaction_id: str) -> bool:
        found = False

        def values() -> Iterator[dict[str, Any]]:
            nonlocal found
            for current in self.iter_all():
                if current.id == transaction_id:
                    found = True
                    continue
                yield asdict(current)

        _atomic_write(self.path, values())
        return found

    def uses_category(self, category: str) -> bool:
        return any(item.category == category for item in self.iter_all())


def _chain(*iterables: Iterable[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    for iterable in iterables:
        yield from iterable


class CategoryStore:
    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / "categories.jsonl"
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            if not self.path.exists() or self.path.stat().st_size == 0:
                _atomic_write(self.path, (asdict(Category(name)) for name in DEFAULT_CATEGORIES))
        except OSError as exc:
            raise StorageError(f"카테고리 저장 파일을 준비하지 못했습니다: {self.path}") from exc

    def list(self) -> list[str]:
        names: list[str] = []
        for value in _read_json_lines(self.path):
            try:
                names.append(str(value["name"]))
            except KeyError as exc:
                raise StorageError("카테고리 저장 데이터에 name 필드가 없습니다.") from exc
        return names

    def contains(self, name: str) -> bool:
        return name in self.list()

    def add(self, name: str) -> None:
        try:
            with self.path.open("a", encoding="utf-8", newline="\n") as file:
                file.write(json.dumps(asdict(Category(name)), ensure_ascii=False, separators=(",", ":")) + "\n")
        except OSError as exc:
            raise StorageError("카테고리를 저장하지 못했습니다.") from exc

    def remove(self, name: str) -> bool:
        found = False

        def values() -> Iterator[dict[str, str]]:
            nonlocal found
            for current in self.list():
                if current == name:
                    found = True
                    continue
                yield asdict(Category(current))

        _atomic_write(self.path, values())
        return found


class BudgetStore:
    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / "budgets.jsonl"
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.path.touch(exist_ok=True)
        except OSError as exc:
            raise StorageError(f"예산 저장 파일을 준비하지 못했습니다: {self.path}") from exc

    def iter_all(self) -> Iterator[Budget]:
        for value in _read_json_lines(self.path):
            try:
                yield Budget(month=str(value["month"]), amount=int(value["amount"]))
            except (KeyError, TypeError, ValueError) as exc:
                raise StorageError("예산 저장 데이터의 필드가 올바르지 않습니다.") from exc

    def get(self, month: str) -> Budget | None:
        return next((budget for budget in self.iter_all() if budget.month == month), None)

    def set(self, budget: Budget) -> None:
        replaced = False

        def values() -> Iterator[dict[str, Any]]:
            nonlocal replaced
            for current in self.iter_all():
                if current.month == budget.month:
                    replaced = True
                    yield asdict(budget)
                else:
                    yield asdict(current)
            if not replaced:
                yield asdict(budget)

        _atomic_write(self.path, values())
