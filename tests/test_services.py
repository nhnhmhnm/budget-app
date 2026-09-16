from __future__ import annotations

import csv
import shutil
import unittest
import zipfile
from pathlib import Path
from uuid import uuid4

from budget_app.backups import BACKUP_FILES, BackupManager
from budget_app.errors import ConflictError, InvalidInputError, NotFoundError
from budget_app.services import LedgerService


class LedgerServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data_dir = Path(__file__).parent / ".tmp" / uuid4().hex
        self.data_dir.mkdir(parents=True)
        self.service = LedgerService(self.data_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.data_dir, ignore_errors=True)

    def add_expense(self, **overrides: object):
        fields: dict[str, object] = {
            "date": "2026-09-16",
            "type": "expense",
            "category": "food",
            "amount": "12000",
            "memo": "점심",
            "tags": "work, meal,work",
        }
        fields.update(overrides)
        return self.service.add_transaction(**fields)

    def test_initializes_storage_files_and_default_categories(self) -> None:
        self.assertTrue((self.data_dir / "transactions.jsonl").is_file())
        self.assertTrue((self.data_dir / "categories.jsonl").is_file())
        self.assertTrue((self.data_dir / "budgets.jsonl").is_file())
        self.assertTrue((self.data_dir / "recurring.jsonl").is_file())
        self.assertIn("food", self.service.list_categories())

    def test_crud_and_latest_registration_order(self) -> None:
        first = self.add_expense(date="2026-09-20")
        second = self.add_expense(date="2026-09-01", amount=5000)

        items = list(self.service.list_transactions(10))
        self.assertEqual([second.id, first.id], [item.id for item in items])
        self.assertEqual(["work", "meal"], first.tags)

        updated = self.service.update_transaction(first.id, {"amount": "15000", "memo": "저녁"})
        self.assertEqual(15000, updated.amount)
        self.assertEqual("저녁", self.service.transactions.find(first.id).memo)

        self.service.delete_transaction(second.id)
        self.assertEqual([first.id], [item.id for item in self.service.list_transactions(10)])
        with self.assertRaises(NotFoundError):
            self.service.delete_transaction("missing")

    def test_validates_transaction_fields(self) -> None:
        invalid_cases = (
            {"date": "2026-02-30"},
            {"type": "transfer"},
            {"amount": 0},
            {"amount": -1},
            {"category": "unknown"},
        )
        for changes in invalid_cases:
            with self.subTest(changes=changes), self.assertRaises(InvalidInputError):
                self.add_expense(**changes)

    def test_search_combines_all_filters(self) -> None:
        matching = self.add_expense(memo="팀 점심", tags="company,meal")
        self.add_expense(date="2026-08-31", memo="팀 점심", tags="company")
        self.service.add_transaction(
            date="2026-09-16",
            type="income",
            category="salary",
            amount=3000000,
            memo="급여",
            tags="company",
        )

        result = list(
            self.service.search_transactions(
                date_from="2026-09-01",
                date_to="2026-09-30",
                category="food",
                type="expense",
                query="점심",
                tag="meal",
            )
        )
        self.assertEqual([matching.id], [item.id for item in result])

    def test_summary_and_budget_warning(self) -> None:
        self.add_expense(amount=700000, category="rent")
        self.add_expense(amount=100000, category="food")
        self.service.add_transaction(
            date="2026-09-01", type="income", category="salary", amount=3000000
        )
        self.service.set_budget("2026-09", 750000)

        summary = self.service.monthly_summary("2026-09", top=1)
        self.assertEqual(3000000, summary.income)
        self.assertEqual(800000, summary.expense)
        self.assertEqual(2200000, summary.balance)
        self.assertEqual([("rent", 700000)], summary.category_expenses)
        self.assertTrue(summary.is_over_budget)
        self.assertAlmostEqual(106.666, summary.budget_usage, places=2)

    def test_category_rules(self) -> None:
        self.service.add_category("health")
        self.assertIn("health", self.service.list_categories())
        with self.assertRaises(ConflictError):
            self.service.add_category("health")

        self.add_expense(category="health")
        with self.assertRaises(ConflictError):
            self.service.remove_category("health")
        self.service.remove_category("etc")
        self.assertNotIn("etc", self.service.list_categories())

    def test_csv_round_trip_and_invalid_import_is_atomic(self) -> None:
        first = self.add_expense()
        export_path = self.data_dir / "out.csv"
        self.assertEqual(1, self.service.export_csv(export_path, month="2026-09"))

        imported_dir = self.data_dir / "imported"
        imported = LedgerService(imported_dir)
        self.assertEqual(1, imported.import_csv(export_path))
        copied = list(imported.list_transactions(10))[0]
        self.assertNotEqual(first.id, copied.id)
        self.assertEqual(first.memo, copied.memo)
        self.assertEqual(first.tags, copied.tags)

        invalid_path = self.data_dir / "invalid.csv"
        with invalid_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(("date", "type", "category", "amount", "memo", "tags"))
            writer.writerow(("2026-09-17", "expense", "food", "1000", "정상 행", ""))
            writer.writerow(("bad-date", "expense", "food", "1000", "오류 행", ""))
        before = len(list(imported.list_transactions(100)))
        with self.assertRaises(InvalidInputError):
            imported.import_csv(invalid_path)
        self.assertEqual(before, len(list(imported.list_transactions(100))))

    def test_export_requires_date_condition(self) -> None:
        with self.assertRaises(InvalidInputError):
            self.service.export_csv(self.data_dir / "out.csv")

    def test_recurring_rule_generation_is_idempotent(self) -> None:
        rule = self.service.add_recurring_rule(
            type="expense",
            day=31,
            category="rent",
            amount=700000,
            memo="월세",
            tags="fixed,home",
        )
        self.assertEqual([rule.id], [item.id for item in self.service.list_recurring_rules()])

        self.assertEqual((1, 0), self.service.generate_recurring("2026-02"))
        generated = list(self.service.list_transactions(10))
        self.assertEqual(1, len(generated))
        self.assertEqual("2026-02-28", generated[0].date)
        self.assertEqual(rule.id, generated[0].recurring_id)
        self.assertEqual((0, 1), self.service.generate_recurring("2026-02"))

        self.service.remove_recurring_rule(rule.id)
        self.assertEqual([], list(self.service.list_recurring_rules()))

    def test_category_used_by_recurring_rule_cannot_be_removed(self) -> None:
        self.service.add_category("subscription")
        self.service.add_recurring_rule(
            type="expense", day=1, category="subscription", amount=9900
        )
        with self.assertRaises(ConflictError):
            self.service.remove_category("subscription")

    def test_backup_contains_all_data_files_and_manifest(self) -> None:
        self.add_expense()
        self.service.set_budget("2026-09", 100000)
        self.service.add_recurring_rule(
            type="income", day=25, category="salary", amount=3000000
        )

        backup_path = BackupManager(self.data_dir).create()

        self.assertTrue(backup_path.name.startswith("budget-backup-"))
        with zipfile.ZipFile(backup_path) as archive:
            names = set(archive.namelist())
            self.assertTrue(set(BACKUP_FILES).issubset(names))
            self.assertIn("manifest.json", names)
            self.assertIn("created_at", archive.read("manifest.json").decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
