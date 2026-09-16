"""argparse 기반 콘솔 인터페이스."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Iterator

from budget_app.decorators import command_boundary, measure_execution
from budget_app.errors import InvalidInputError
from budget_app.formatters import format_money, transaction_lines
from budget_app.services import LedgerService


def _add_runtime_options(parser: argparse.ArgumentParser, *, root: bool = False) -> None:
    default = "./data" if root else argparse.SUPPRESS
    parser.add_argument("--data-dir", default=default, help="데이터 저장 폴더 (기본: ./data)")
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False if root else argparse.SUPPRESS,
        help="명령 실행 로그 출력",
    )


def _command_parser(subparsers: argparse._SubParsersAction, name: str, help: str) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(name, help=help, description=help)
    _add_runtime_options(parser)
    return parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="budget_app",
        description="콘솔 가계부: 수입/지출 CRUD, 검색, 예산, 카테고리, CSV 입출력",
    )
    _add_runtime_options(parser, root=True)
    commands = parser.add_subparsers(dest="command", metavar="<command>")

    _command_parser(commands, "add", "대화형으로 거래를 추가합니다.")

    list_parser = _command_parser(commands, "list", "최신 등록순으로 거래를 조회합니다.")
    list_parser.add_argument("--limit", type=int, default=20, help="최대 출력 건수 (기본: 20)")

    search = _command_parser(commands, "search", "조건에 맞는 거래를 검색합니다.")
    search.add_argument("--from", dest="date_from", help="시작 날짜 (YYYY-MM-DD)")
    search.add_argument("--to", dest="date_to", help="종료 날짜 (YYYY-MM-DD)")
    search.add_argument("--category", help="카테고리")
    search.add_argument("--type", choices=("income", "expense"), help="거래 타입")
    search.add_argument("--q", help="메모 검색어")
    search.add_argument("--tag", help="태그")

    update = _command_parser(commands, "update", "옵션으로 지정한 거래 필드를 수정합니다.")
    update.add_argument("--id", required=True, help="거래 id")
    update.add_argument("--date", help="날짜 (YYYY-MM-DD)")
    update.add_argument("--type", choices=("income", "expense"), help="거래 타입")
    update.add_argument("--category", help="카테고리")
    update.add_argument("--amount", help="양의 정수 금액")
    update.add_argument("--memo", help="메모 (빈 문자열로 내용 삭제)")
    update.add_argument("--tags", help="쉼표 구분 태그 (빈 문자열로 내용 삭제)")

    delete = _command_parser(commands, "delete", "id로 거래를 삭제합니다.")
    delete.add_argument("--id", required=True, help="거래 id")

    category = _command_parser(commands, "category", "카테고리를 관리합니다.")
    category_commands = category.add_subparsers(dest="category_command", metavar="<action>")
    category_add = category_commands.add_parser("add", help="카테고리 추가")
    category_add.add_argument("--name", required=True, help="새 카테고리 이름")
    category_commands.add_parser("list", help="카테고리 목록")
    category_remove = category_commands.add_parser("remove", help="카테고리 삭제")
    category_remove.add_argument("--name", required=True, help="삭제할 카테고리 이름")

    budget = _command_parser(commands, "budget", "월 예산을 설정하거나 조회합니다.")
    budget_commands = budget.add_subparsers(dest="budget_command", metavar="<action>")
    budget_set = budget_commands.add_parser("set", help="월 예산 설정")
    budget_set.add_argument("--month", required=True, help="대상 월 (YYYY-MM)")
    budget_set.add_argument("--amount", required=True, help="양의 정수 금액")
    budget_show = budget_commands.add_parser("show", help="월 예산 조회")
    budget_show.add_argument("--month", required=True, help="대상 월 (YYYY-MM)")

    return parser


def _prompt(label: str, *, optional: bool = False) -> str:
    suffix = " (선택)" if optional else ""
    try:
        value = input(f"{label}{suffix}: ").strip()
    except EOFError as exc:
        raise InvalidInputError("입력이 중단되었습니다.", "값을 입력하거나 Ctrl+C로 종료하세요.") from exc
    if not optional and not value:
        raise InvalidInputError(f"{label} 값은 필수입니다.", "값을 입력한 뒤 다시 실행하세요.")
    return value


def _print_transactions(items: Iterator) -> None:
    found = False
    for line in transaction_lines(items):
        found = True
        print(line)
    if not found:
        print("거래 내역이 없습니다.")


def _handle_add(service: LedgerService) -> None:
    print("등록된 카테고리: " + ", ".join(service.list_categories()))
    transaction = service.add_transaction(
        date=_prompt("날짜 (YYYY-MM-DD)"),
        type=_prompt("타입 (income/expense)"),
        category=_prompt("카테고리"),
        amount=_prompt("금액"),
        memo=_prompt("메모", optional=True),
        tags=_prompt("태그 (쉼표 구분)", optional=True),
    )
    print(f"거래가 저장되었습니다. id={transaction.id}")


def _changes_from_args(args: argparse.Namespace) -> dict[str, object]:
    fields = ("date", "type", "category", "amount", "memo", "tags")
    return {field: getattr(args, field) for field in fields if getattr(args, field) is not None}


@measure_execution
def _dispatch(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    service = LedgerService(args.data_dir)
    if args.command == "add":
        _handle_add(service)
    elif args.command == "list":
        _print_transactions(service.list_transactions(args.limit))
    elif args.command == "search":
        _print_transactions(
            service.search_transactions(
                date_from=args.date_from,
                date_to=args.date_to,
                category=args.category,
                type=args.type,
                query=args.q,
                tag=args.tag,
            )
        )
    elif args.command == "update":
        transaction = service.update_transaction(args.id, _changes_from_args(args))
        print(f"거래가 수정되었습니다. id={transaction.id}")
    elif args.command == "delete":
        service.delete_transaction(args.id)
        print(f"거래가 삭제되었습니다. id={args.id}")
    elif args.command == "category":
        if args.category_command == "add":
            name = service.add_category(args.name)
            print(f"카테고리가 추가되었습니다: {name}")
        elif args.category_command == "list":
            for name in service.list_categories():
                print(name)
        elif args.category_command == "remove":
            service.remove_category(args.name)
            print(f"카테고리가 삭제되었습니다: {args.name}")
        else:
            parser.parse_args(["category", "--help"])
    elif args.command == "budget":
        if args.budget_command == "set":
            saved = service.set_budget(args.month, args.amount)
            print(f"예산이 저장되었습니다: {saved.month} {format_money(saved.amount)}")
        elif args.budget_command == "show":
            budget = service.get_budget(args.month)
            print(
                f"{args.month} 예산: {format_money(budget.amount)}"
                if budget
                else f"{args.month}에 설정된 예산이 없습니다."
            )
        else:
            parser.parse_args(["budget", "--help"])
    else:
        parser.print_help()
    return 0


@command_boundary
def _run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    return _dispatch(args, parser)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="[%(levelname)s] %(message)s",
    )
    return _run(args, parser)


if __name__ == "__main__":
    sys.exit(main())
