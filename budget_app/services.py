"""가계부 업무 규칙과 유스케이스."""

from __future__ import annotations

import calendar
import csv
from dataclasses import replace
from itertools import islice
from pathlib import Path
from typing import Iterator, Mapping
from uuid import uuid4

from budget_app.errors import ConflictError, InvalidInputError, NotFoundError
from budget_app.models import Budget, MonthlySummary, RecurringRule, Transaction
from budget_app.repositories import BudgetStore, CategoryStore, RecurringStore, TransactionRepository
from budget_app.validators import (
    parse_tags,
    validate_category_name,
    validate_date,
    validate_month,
    validate_positive_int,
    validate_readable_file,
    validate_type,
)

CSV_COLUMNS = ("date", "type", "category", "amount", "memo", "tags")


class LedgerService:
    def __init__(self, data_dir: str | Path) -> None:
        self.transactions = TransactionRepository(data_dir)
        self.categories = CategoryStore(data_dir)
        self.budgets = BudgetStore(data_dir)
        self.recurring = RecurringStore(data_dir)

    def _validate_category_exists(self, category: str) -> str:
        name = validate_category_name(category)
        if not self.categories.contains(name):
            raise InvalidInputError(
                f"등록되지 않은 카테고리입니다: {name}",
                "category list로 확인하거나 category add로 먼저 등록하세요.",
            )
        return name

    def _new_transaction(
        self,
        *,
        date: str,
        type: str,
        category: str,
        amount: int | str,
        memo: str = "",
        tags: str | list[str] | None = None,
        recurring_id: str | None = None,
    ) -> Transaction:
        return Transaction(
            id=uuid4().hex,
            date=validate_date(date),
            type=validate_type(type),
            category=self._validate_category_exists(category),
            amount=validate_positive_int(amount),
            memo=str(memo or "").strip(),
            tags=parse_tags(tags),
            recurring_id=recurring_id,
        )

    def add_transaction(self, **fields: object) -> Transaction:
        transaction = self._new_transaction(
            date=str(fields["date"]),
            type=str(fields["type"]),
            category=str(fields["category"]),
            amount=fields["amount"],
            memo=str(fields.get("memo", "")),
            tags=fields.get("tags"),
        )
        self.transactions.add(transaction)
        return transaction

    def list_transactions(self, limit: int) -> Iterator[Transaction]:
        if limit <= 0:
            raise InvalidInputError("--limit은 1 이상이어야 합니다.", "양의 정수를 입력하세요.")
        yield from islice(self.transactions.iter_latest(), limit)

    def search_transactions(
        self,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        category: str | None = None,
        type: str | None = None,
        query: str | None = None,
        tag: str | None = None,
    ) -> Iterator[Transaction]:
        if date_from:
            validate_date(date_from, "시작 날짜")
        if date_to:
            validate_date(date_to, "종료 날짜")
        if date_from and date_to and date_from > date_to:
            raise InvalidInputError("시작 날짜가 종료 날짜보다 늦습니다.", "--from과 --to 값을 확인하세요.")
        if category:
            self._validate_category_exists(category)
        if type:
            validate_type(type)
        normalized_query = query.casefold() if query else None
        for item in self.transactions.iter_latest():
            if date_from and item.date < date_from:
                continue
            if date_to and item.date > date_to:
                continue
            if category and item.category != category:
                continue
            if type and item.type != type:
                continue
            if normalized_query and normalized_query not in item.memo.casefold():
                continue
            if tag and tag not in item.tags:
                continue
            yield item

    def update_transaction(self, transaction_id: str, changes: Mapping[str, object]) -> Transaction:
        current = self.transactions.find(transaction_id)
        if current is None:
            raise NotFoundError(f"거래를 찾을 수 없습니다: {transaction_id}", "list 명령으로 id를 확인하세요.")
        if not changes:
            raise InvalidInputError("수정할 필드가 없습니다.", "--date, --type 등의 옵션을 하나 이상 지정하세요.")
        validated: dict[str, object] = {}
        if "date" in changes:
            validated["date"] = validate_date(str(changes["date"]))
        if "type" in changes:
            validated["type"] = validate_type(str(changes["type"]))
        if "category" in changes:
            validated["category"] = self._validate_category_exists(str(changes["category"]))
        if "amount" in changes:
            validated["amount"] = validate_positive_int(changes["amount"])
        if "memo" in changes:
            validated["memo"] = str(changes["memo"]).strip()
        if "tags" in changes:
            validated["tags"] = parse_tags(changes["tags"])
        updated = replace(current, **validated)
        if not self.transactions.update(updated):
            raise NotFoundError(f"거래를 갱신하는 동안 id가 사라졌습니다: {transaction_id}")
        return updated

    def delete_transaction(self, transaction_id: str) -> None:
        if not self.transactions.delete(transaction_id):
            raise NotFoundError(f"거래를 찾을 수 없습니다: {transaction_id}", "list 명령으로 id를 확인하세요.")

    def monthly_summary(self, month: str, top: int) -> MonthlySummary:
        validate_month(month)
        if top <= 0:
            raise InvalidInputError("--top은 1 이상이어야 합니다.")
        income = expense = count = 0
        category_expenses: dict[str, int] = {}
        for item in self.transactions.iter_all():
            if not item.date.startswith(f"{month}-"):
                continue
            count += 1
            if item.type == "income":
                income += item.amount
            else:
                expense += item.amount
                category_expenses[item.category] = category_expenses.get(item.category, 0) + item.amount
        ranking = sorted(category_expenses.items(), key=lambda pair: (-pair[1], pair[0]))[:top]
        budget = self.budgets.get(month)
        return MonthlySummary(month, income, expense, ranking, count, budget.amount if budget else None)

    def set_budget(self, month: str, amount: int | str) -> Budget:
        budget = Budget(validate_month(month), validate_positive_int(amount, "예산"))
        self.budgets.set(budget)
        return budget

    def get_budget(self, month: str) -> Budget | None:
        return self.budgets.get(validate_month(month))

    def list_categories(self) -> list[str]:
        return self.categories.list()

    def add_category(self, name: str) -> str:
        normalized = validate_category_name(name)
        if self.categories.contains(normalized):
            raise ConflictError(f"이미 등록된 카테고리입니다: {normalized}", "다른 이름을 사용하세요.")
        self.categories.add(normalized)
        return normalized

    def remove_category(self, name: str) -> None:
        normalized = validate_category_name(name)
        if not self.categories.contains(normalized):
            raise NotFoundError(f"카테고리를 찾을 수 없습니다: {normalized}", "category list로 확인하세요.")
        if self.transactions.uses_category(normalized):
            raise ConflictError(
                f"사용 중인 카테고리는 삭제할 수 없습니다: {normalized}",
                "해당 거래의 카테고리를 먼저 수정하거나 삭제하세요.",
            )
        if self.recurring.uses_category(normalized):
            raise ConflictError(
                f"반복 규칙에서 사용 중인 카테고리는 삭제할 수 없습니다: {normalized}",
                "해당 반복 규칙을 먼저 삭제하세요.",
            )
        self.categories.remove(normalized)

    def add_recurring_rule(
        self,
        *,
        type: str,
        day: int | str,
        category: str,
        amount: int | str,
        memo: str = "",
        tags: str | list[str] | None = None,
    ) -> RecurringRule:
        validated_day = validate_positive_int(day, "반복 일자")
        if validated_day > 31:
            raise InvalidInputError("반복 일자는 1부터 31 사이여야 합니다.")
        rule = RecurringRule(
            id=uuid4().hex,
            type=validate_type(type),
            day=validated_day,
            category=self._validate_category_exists(category),
            amount=validate_positive_int(amount),
            memo=memo.strip(),
            tags=parse_tags(tags),
        )
        self.recurring.add(rule)
        return rule

    def list_recurring_rules(self) -> Iterator[RecurringRule]:
        yield from self.recurring.iter_all()

    def remove_recurring_rule(self, rule_id: str) -> None:
        if not self.recurring.remove(rule_id):
            raise NotFoundError(
                f"반복 규칙을 찾을 수 없습니다: {rule_id}",
                "recurring list 명령으로 id를 확인하세요.",
            )

    def generate_recurring(self, month: str) -> tuple[int, int]:
        """대상 월의 반복 거래를 생성하고 (생성, 건너뜀) 건수를 반환한다."""

        validate_month(month)
        year, month_number = (int(part) for part in month.split("-"))
        last_day = calendar.monthrange(year, month_number)[1]
        generated_sources = {
            item.recurring_id
            for item in self.transactions.iter_all()
            if item.recurring_id and item.date.startswith(f"{month}-")
        }
        skipped = 0

        def new_transactions() -> Iterator[Transaction]:
            nonlocal skipped
            for rule in self.recurring.iter_all():
                if rule.id in generated_sources:
                    skipped += 1
                    continue
                if not self.categories.contains(rule.category):
                    raise ConflictError(
                        f"반복 규칙의 카테고리가 존재하지 않습니다: {rule.category}",
                        f"규칙 id={rule.id}를 삭제하거나 카테고리를 다시 추가하세요.",
                    )
                day = min(rule.day, last_day)
                yield self._new_transaction(
                    date=f"{month}-{day:02d}",
                    type=rule.type,
                    category=rule.category,
                    amount=rule.amount,
                    memo=rule.memo,
                    tags=rule.tags,
                    recurring_id=rule.id,
                )

        generated = self.transactions.add_many(new_transactions())
        return generated, skipped

    def import_csv(self, source: str | Path) -> int:
        path = validate_readable_file(source)

        def transactions() -> Iterator[Transaction]:
            try:
                with path.open("r", encoding="utf-8-sig", newline="") as file:
                    reader = csv.DictReader(file)
                    if reader.fieldnames is None or any(column not in reader.fieldnames for column in CSV_COLUMNS):
                        raise InvalidInputError(
                            "CSV 헤더가 올바르지 않습니다.",
                            f"필수 헤더: {', '.join(CSV_COLUMNS)}",
                        )
                    for row_number, row in enumerate(reader, start=2):
                        try:
                            yield self._new_transaction(
                                date=row["date"],
                                type=row["type"],
                                category=row["category"],
                                amount=row["amount"],
                                memo=row.get("memo", ""),
                                tags=row.get("tags", ""),
                            )
                        except InvalidInputError as exc:
                            raise InvalidInputError(
                                f"CSV {row_number}행이 올바르지 않습니다: {exc.message}", exc.hint
                            ) from exc
            except UnicodeDecodeError as exc:
                raise InvalidInputError("CSV 파일이 UTF-8이 아닙니다.", "UTF-8로 저장한 뒤 다시 시도하세요.") from exc
            except csv.Error as exc:
                raise InvalidInputError(f"CSV 파일을 읽을 수 없습니다: {exc}") from exc

        return self.transactions.add_many(transactions())

    def export_csv(
        self,
        destination: str | Path,
        *,
        month: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> int:
        if not month and not date_from and not date_to:
            raise InvalidInputError(
                "내보내기에는 기간 조건이 필요합니다.",
                "--month 또는 --from/--to를 하나 이상 지정하세요.",
            )
        if month:
            validate_month(month)
        if date_from:
            validate_date(date_from, "시작 날짜")
        if date_to:
            validate_date(date_to, "종료 날짜")
        if date_from and date_to and date_from > date_to:
            raise InvalidInputError("내보내기 시작 날짜가 종료 날짜보다 늦습니다.")
        path = Path(destination)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            count = 0
            with path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
                writer.writeheader()
                for item in self.transactions.iter_all():
                    if month and not item.date.startswith(f"{month}-"):
                        continue
                    if date_from and item.date < date_from:
                        continue
                    if date_to and item.date > date_to:
                        continue
                    writer.writerow(
                        {
                            "date": item.date,
                            "type": item.type,
                            "category": item.category,
                            "amount": item.amount,
                            "memo": item.memo,
                            "tags": ",".join(item.tags),
                        }
                    )
                    count += 1
            return count
        except OSError as exc:
            raise InvalidInputError(f"CSV 파일을 저장하지 못했습니다: {path}", "경로와 파일 권한을 확인하세요.") from exc
