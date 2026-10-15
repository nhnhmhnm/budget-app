# 콘솔 가계부

Python 표준 라이브러리만 사용해 수입과 지출을 파일에 영구 저장하고 관리하는 콘솔 프로그램입니다. 거래 CRUD, 조건 검색, 월별 요약, 예산 및 카테고리 관리, CSV 가져오기/내보내기와 모든 보너스 기능을 제공합니다.

프로젝트 발표를 준비한다면 [프로젝트 시연 및 평가 답변 가이드](./DEMO_GUIDE.md)의 순서대로 실행하면 됩니다. 정상·오류 CSV 예제와 평가 항목별 권장 답변도 함께 정리되어 있습니다.

## 과제 요약

- `python -m budget_app <command> [options]` 형태의 CLI와 명령별 `--help`
- 거래 추가·목록·검색·수정·삭제와 월별 수입·지출·잔액 집계
- 카테고리별 지출 TOP N, 월 예산 사용률 및 초과 경고
- 카테고리 추가·조회·삭제와 사용 중인 카테고리 삭제 방지
- CSV 일괄 가져오기 및 기간별 내보내기
- 거래·카테고리·예산·반복 규칙을 서로 다른 파일에 영구 저장
- 제너레이터 기반 스트리밍, 타입 힌트, 계층별 모듈 분리
- 데코레이터를 통한 공통 오류 처리와 실행 시간 로그 분리
- 잘못된 입력에는 스택 트레이스 대신 원인과 해결 힌트를 출력하고 0이 아닌 종료 코드 반환
- 타임스탬프 ZIP 백업, 반복 거래 생성, 한글 폭을 고려한 표 출력, 원자적 파일 교체

## 실행 환경과 시작

Python 3.10 이상이 필요하며 외부 패키지를 설치할 필요가 없습니다. 프로젝트 루트에서 실행합니다.

```console
python -m budget_app --help
python -m budget_app <command> --help
```

기본 데이터 폴더는 현재 경로의 `./data`입니다. 다른 위치를 쓰려면 최상위 명령 앞이나 바로 뒤에 `--data-dir`을 지정합니다.

```console
python -m budget_app --data-dir ./my-data list
python -m budget_app list --data-dir ./my-data --limit 10
```

`--verbose`를 지정하면 데코레이터가 기록한 명령 실행 시간을 볼 수 있습니다.

## 주요 명령

### 거래 추가와 조회

`add`는 날짜, 타입, 카테고리, 금액, 메모, 태그를 순서대로 묻는 대화형 명령입니다. 첫 실행에는 `food`, `transport`, `rent`, `salary`, `etc` 기본 카테고리가 자동 생성됩니다.

```console
python -m budget_app add
python -m budget_app list --limit 20
python -m budget_app search --from 2026-09-01 --to 2026-09-30 --type expense
python -m budget_app search --category food --q 점심 --tag work
```

목록과 검색 결과는 최신 등록순입니다. 거래 파일을 한꺼번에 메모리에 올리지 않고 뒤에서부터 블록 단위로 읽는 제너레이터를 사용합니다.

### 거래 수정과 삭제

수정은 옵션 기반 방식으로 고정했습니다. `--id` 외에 바꿀 필드를 하나 이상 지정합니다. 빈 `--memo ""` 또는 `--tags ""`를 넘기면 기존 내용을 지웁니다.

```console
python -m budget_app update --id <id> --amount 15000 --memo "저녁 식사"
python -m budget_app update --id <id> --category transport --tags "work,taxi"
python -m budget_app delete --id <id>
```

수정과 삭제는 임시 파일을 완성하고 같은 파일 시스템 안에서 원자적으로 교체해, 처리 도중 원본이 잘릴 위험을 줄였습니다.

### 월별 요약과 예산

```console
python -m budget_app budget set --month 2026-09 --amount 1000000
python -m budget_app budget show --month 2026-09
python -m budget_app summary --month 2026-09 --top 3
```

요약은 총 수입, 총 지출, 잔액, 지출 카테고리 TOP N을 보여 줍니다. 예산이 있으면 사용률과 초과 경고도 출력하며, 거래가 없는 달은 데이터가 없다고 안내합니다.

### 카테고리 관리

```console
python -m budget_app category list
python -m budget_app category add --name health
python -m budget_app category remove --name health
```

거래에서 사용 중인 카테고리는 먼저 해당 거래를 수정하거나 삭제하기 전까지 제거할 수 없습니다.

### CSV 가져오기와 내보내기

```console
python -m budget_app import --from ./transactions.csv
python -m budget_app export --out ./september.csv --month 2026-09
python -m budget_app export --out ./period.csv --from 2026-09-01 --to 2026-09-15
```

내보내기는 `--month`, `--from`, `--to` 중 하나 이상의 기간 조건이 필수입니다. 가져오기는 전체 CSV를 검증한 뒤 거래 저장 파일을 교체하므로, 중간 행이 잘못되어도 일부 행만 반영되지 않습니다. 가져온 거래에는 새로운 고유 id가 생성됩니다.

CSV는 UTF-8, 헤더 포함이며 다음 스키마를 사용합니다.

| 열 | 필수 | 형식/설명 |
| --- | --- | --- |
| `date` | Y | `YYYY-MM-DD` |
| `type` | Y | `income` 또는 `expense` |
| `category` | Y | 등록된 카테고리 |
| `amount` | Y | 0보다 큰 정수 |
| `memo` | N | 문자열 |
| `tags` | N | 쉼표로 구분한 문자열 |

### 반복 거래

월급, 월세, 구독료처럼 매월 반복되는 거래는 규칙으로 등록한 뒤 원하는 월에 생성합니다.

```console
python -m budget_app recurring add --type income --day 25 --category salary --amount 3000000 --memo "월급"
python -m budget_app recurring add --type expense --day 31 --category rent --amount 700000 --tags "fixed,home"
python -m budget_app recurring list
python -m budget_app recurring generate --month 2026-02
python -m budget_app recurring remove --id <rule-id>
```

대상 월에 없는 일자(예: 2월 31일)는 그달의 마지막 날로 조정합니다. 규칙 id와 월을 기준으로 이미 생성된 거래를 확인하므로 같은 명령을 다시 실행해도 중복 생성되지 않습니다. 반복 규칙이 참조하는 카테고리는 규칙을 삭제하기 전까지 제거할 수 없습니다.

### 데이터 백업

```console
python -m budget_app backup
python -m budget_app backup --out-dir ./archives
```

기본 출력 폴더는 `<data-dir>/backups`입니다. `budget-backup-YYYYMMDD-HHMMSS-ffffff.zip` 파일에 모든 JSONL 데이터와 생성 시각·포맷 버전을 기록한 `manifest.json`을 포함합니다. ZIP도 임시 파일을 완성한 뒤 최종 이름으로 원자적으로 교체합니다.

복구할 때는 실행 중인 프로그램을 종료하고 ZIP의 JSONL 파일을 새 폴더에 푼 다음, `python -m budget_app --data-dir <복구 폴더> list`로 먼저 내용을 확인합니다. 확인 전에는 기존 운영 데이터 폴더를 덮어쓰지 않는 것이 안전합니다.

### 표 형식 출력

`list`, `search`, `recurring list`는 외부 라이브러리 없이 헤더와 구분선을 갖춘 표로 출력됩니다. 한글 문자의 터미널 표시 폭을 두 칸으로 계산해 열을 맞추고, 긴 메모나 태그는 말줄임표로 제한합니다. 입력 행은 미리 모으지 않고 계속 스트리밍합니다.

## 저장 파일

데이터 폴더에 다음 UTF-8 JSONL 파일을 자동 생성합니다. JSONL은 한 줄에 JSON 객체 하나를 저장하므로 거래를 `yield`로 한 건씩 읽을 수 있습니다.

| 파일 | 내용 | 예시 |
| --- | --- | --- |
| `transactions.jsonl` | 거래 | `{"id":"...","date":"2026-09-16","type":"expense","category":"food","amount":12000,"memo":"점심","tags":["work"],"recurring_id":null}` |
| `categories.jsonl` | 카테고리 | `{"name":"food"}` |
| `budgets.jsonl` | 월 예산 | `{"month":"2026-09","amount":1000000}` |
| `recurring.jsonl` | 반복 거래 규칙 | `{"id":"...","type":"expense","day":31,"category":"rent","amount":700000,"memo":"월세","tags":["fixed"]}` |

거래 필드의 의미는 다음과 같습니다.

- `id`: UUID 기반 고유 문자열
- `date`: `YYYY-MM-DD`
- `type`: `income` 또는 `expense`
- `amount`: 0보다 큰 원 단위 정수
- `category`: 등록된 카테고리
- `memo`: 선택 문자열
- `tags`: 선택 문자열 배열
- `recurring_id`: 반복 규칙에서 생성된 경우 원본 규칙 id, 일반 거래는 `null`

## 구조

```text
budget_app/
├── cli.py           # 인자 해석과 사용자 입출력
├── services.py      # 검증 조합과 업무 규칙
├── repositories.py  # JSONL 스트리밍과 원자적 파일 교체
├── models.py        # dataclass 데이터 계약
├── validators.py    # 입력 검증
├── decorators.py    # 오류 경계와 실행 시간 측정
├── formatters.py    # 한글 폭을 고려한 스트리밍 표 형식
└── backups.py       # 원자적 ZIP 백업과 manifest 생성
```

CLI, 서비스, 저장소를 분리해 출력 방식이나 저장 포맷의 변경이 다른 계층에 번지는 범위를 줄였습니다. 타입 힌트는 계층 사이에 전달되는 값의 계약을 드러내며, `Transaction`, `Budget`, `MonthlySummary` 데이터 클래스는 관련 필드를 명시적으로 묶습니다.

## 오류와 종료 코드

유효하지 않은 날짜·금액·타입·카테고리, 없는 id, 잘못된 CSV에는 `오류:`와 가능한 경우 `해결:` 문구를 출력합니다. 정상 종료 코드는 `0`, 업무 규칙 또는 입력 오류는 `2`, 취소는 `130`입니다.

## 테스트

표준 라이브러리 테스트 러너로 전체 테스트를 실행합니다.

```console
python -m unittest discover -s tests -v
```
