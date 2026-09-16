"""CLI 진입점: argparse subparser 라우팅 골격.

각 명령(add/list/search/summary/budget/category/update/delete/import/export)은
후속 커밋에서 서브파서로 추가된다. 이 커밋에서는 --help가 동작하는 최소 골격만 둔다.
"""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="budget_app",
        description="콘솔 가계부: 수입/지출 관리, 검색, 월별 요약, 예산, 카테고리, import/export",
    )
    parser.add_argument(
        "--data-dir",
        default="./data",
        help="데이터 저장 폴더 (기본: ./data)",
    )
    parser.add_subparsers(dest="command", metavar="<command>")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    # 명령 구현은 후속 커밋에서 추가.
    parser.error(f"알 수 없는 명령: {args.command}")
    return 2
