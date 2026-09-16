from __future__ import annotations

import unittest

from budget_app.formatters import display_width, recurring_rule_lines, transaction_lines
from budget_app.models import RecurringRule, Transaction


class FormatterTest(unittest.TestCase):
    def test_display_width_counts_korean_as_two_cells(self) -> None:
        self.assertEqual(4, display_width("가계"))
        self.assertEqual(4, display_width("AB12"))

    def test_transaction_table_has_aligned_rows_and_header(self) -> None:
        items = (
            Transaction("a" * 32, "2026-09-16", "expense", "food", 12000, "점심"),
            Transaction("b" * 32, "2026-09-17", "income", "salary", 3000000, "급여"),
        )
        lines = list(transaction_lines(items))

        self.assertEqual(4, len(lines))
        self.assertIn("날짜", lines[0])
        self.assertEqual(1, len({display_width(line) for line in lines}))

    def test_empty_table_does_not_emit_header(self) -> None:
        self.assertEqual([], list(transaction_lines(())))

    def test_recurring_rules_use_table_format(self) -> None:
        rule = RecurringRule("r" * 32, "expense", 31, "rent", 700000, "월세")
        lines = list(recurring_rule_lines((rule,)))
        self.assertEqual(3, len(lines))
        self.assertIn("매월", lines[0])
        self.assertIn("31일", lines[2])


if __name__ == "__main__":
    unittest.main()
