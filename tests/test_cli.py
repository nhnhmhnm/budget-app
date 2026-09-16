from __future__ import annotations

import io
import re
import shutil
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from budget_app.cli import main


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data_path = Path(__file__).parent / ".tmp" / uuid4().hex
        self.data_path.mkdir(parents=True)
        self.data_dir = str(self.data_path)

    def tearDown(self) -> None:
        shutil.rmtree(self.data_path, ignore_errors=True)

    def run_cli(self, *arguments: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["--data-dir", self.data_dir, *arguments])
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_interactive_add_list_and_summary(self) -> None:
        answers = iter(("2026-09-16", "expense", "food", "12000", "점심", "meal"))
        with patch("builtins.input", side_effect=lambda _: next(answers)):
            code, output, error = self.run_cli("add")
        self.assertEqual(0, code)
        self.assertIn("id=", output)
        self.assertEqual("", error)

        code, output, _ = self.run_cli("list", "--limit", "1")
        self.assertEqual(0, code)
        self.assertIn("점심", output)

        code, output, _ = self.run_cli("summary", "--month", "2026-09")
        self.assertEqual(0, code)
        self.assertIn("총 지출: 12,000원", output)

    def test_domain_error_has_hint_and_nonzero_exit(self) -> None:
        code, output, error = self.run_cli("delete", "--id", "missing")
        self.assertEqual(2, code)
        self.assertEqual("", output)
        self.assertIn("오류:", error)
        self.assertIn("해결:", error)
        self.assertNotIn("Traceback", error)

    def test_recurring_and_backup_commands(self) -> None:
        code, output, _ = self.run_cli(
            "recurring",
            "add",
            "--type",
            "expense",
            "--day",
            "31",
            "--category",
            "rent",
            "--amount",
            "700000",
            "--memo",
            "월세",
        )
        self.assertEqual(0, code)
        rule_id = re.search(r"id=([0-9a-f]{32})", output)
        self.assertIsNotNone(rule_id)

        code, output, _ = self.run_cli("recurring", "generate", "--month", "2026-02")
        self.assertEqual(0, code)
        self.assertIn("생성=1", output)
        code, output, _ = self.run_cli("recurring", "generate", "--month", "2026-02")
        self.assertEqual(0, code)
        self.assertIn("중복 건너뜀=1", output)

        backup_dir = self.data_path / "archives"
        code, output, _ = self.run_cli("backup", "--out-dir", str(backup_dir))
        self.assertEqual(0, code)
        self.assertIn("백업이 완료", output)
        self.assertEqual(1, len(list(backup_dir.glob("budget-backup-*.zip"))))


if __name__ == "__main__":
    unittest.main()
