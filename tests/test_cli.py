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

    def test_interactive_add_reprompts_each_invalid_required_field(self) -> None:
        answers = iter(
            (
                "2026",
                "2026-10-15",
                "v",
                "expense",
                "",
                "unknown",
                "food",
                "0",
                "350000",
                "팀 저녁 식사",
                "team,food",
            )
        )
        prompts: list[str] = []

        def answer(prompt: str) -> str:
            prompts.append(prompt)
            return next(answers)

        with patch("builtins.input", side_effect=answer):
            code, output, error = self.run_cli("add")

        self.assertEqual(0, code)
        self.assertIn("거래가 저장되었습니다.", output)
        self.assertIn("날짜 형식이 올바르지 않습니다: 2026", error)
        self.assertIn("허용되지 않는 거래 타입입니다: v", error)
        self.assertIn("카테고리 이름이 비어 있습니다.", error)
        self.assertIn("등록되지 않은 카테고리입니다: unknown", error)
        self.assertIn("금액은 0보다 큰 정수여야 합니다: 0", error)
        self.assertEqual(2, prompts.count("날짜 (YYYY-MM-DD): "))
        self.assertEqual(2, prompts.count("타입 (income/expense): "))
        self.assertEqual(3, prompts.count("카테고리: "))
        self.assertEqual(2, prompts.count("금액: "))

    def test_command_syntax_error_has_hint_and_nonzero_exit(self) -> None:
        error = io.StringIO()
        with redirect_stderr(error), self.assertRaises(SystemExit) as raised:
            main(["wrong-command"])

        self.assertEqual(2, raised.exception.code)
        self.assertIn("오류:", error.getvalue())
        self.assertIn("해결:", error.getvalue())
        self.assertNotIn("Traceback", error.getvalue())

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
