# 콘솔 가계부

Python 표준 라이브러리만 사용해 수입과 지출을 파일에 영구 저장하고 관리하는 콘솔 프로그램입니다. 거래 CRUD, 조건 검색, 월별 요약, 예산 및 카테고리 관리, CSV 가져오기/내보내기와 모든 보너스 기능을 제공합니다.

실행 명령과 예상 결과는 이 문서의 시연 예시에서 확인할 수 있습니다. 평가 항목별 발표 답변과 코드 설명 순서는 [DEMO_GUIDE.md](./DEMO_GUIDE.md)에 별도로 정리했습니다.

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

## 시연 예시

아래 명령은 VS Code 터미널에서 프로젝트 루트 폴더를 연 상태로 실행합니다. `--data-dir`을 생략하므로 데이터는 기본 경로인 `./data`에 저장됩니다. 같은 import를 반복하면 거래가 중복될 수 있으므로 비어 있는 `./data`에서 시연하는 것을 권장합니다.

### 1. 거래 추가

`add`는 날짜, 수입·지출 구분, 카테고리, 금액, 메모, 태그를 차례로 입력받아 거래 한 건을 등록합니다. 처음 실행하면 `food`, `transport`, `rent`, `salary`, `etc` 기본 카테고리와 데이터 파일이 자동으로 만들어집니다.

```console
python -m budget_app add
```

다음 값을 순서대로 입력합니다.

```text
날짜 (YYYY-MM-DD): 2026-10-15
타입 (income/expense): expense
카테고리: food
금액: 350000
메모 (선택): 팀 저녁 식사
태그 (쉼표 구분) (선택): team,food
```

날짜, 거래 타입, 카테고리, 금액은 입력 직후 검증됩니다. 올바르지 않으면 `오류:`와 `해결:`을 출력하고 해당 필드만 다시 입력받습니다. 출력된 거래 id는 수정과 삭제 시 대상을 정확히 식별하는 값이므로 복사해 두고, 아래 명령의 `<FOOD_ID>`를 실제 id로 바꿔 사용합니다.

### 2. 거래 목록 조회

`list`는 최근 등록한 거래부터 지정한 개수만큼 보여 줍니다. 거래 파일 전체를 메모리에 올리지 않고 파일 뒤쪽부터 블록 단위로 읽는 제너레이터를 사용하므로 필요한 개수만 읽고 멈춥니다.

```console
python -m budget_app list --limit 10
```

출력 표는 외부 라이브러리 없이 생성되며, 한글을 두 칸 너비로 계산해 열을 맞추고 긴 메모와 태그에는 말줄임표를 적용합니다.

### 3. CSV 거래 가져오기

`import`는 여러 거래를 CSV로 한 번에 등록하는 기능입니다. 급여·보너스 같은 수입과 식비·교통비·월세·생활비 지출 등 다양한 거래 12건이 들어 있는 예제 파일을 가져옵니다.

```console
python -m budget_app import --from ./examples/demo_import.csv
```

정상적으로 가져오면 다음과 같이 처리 건수가 출력됩니다.

```text
CSV 가져오기가 완료되었습니다. 처리 건수=12
```

CSV는 UTF-8과 헤더를 사용하며 스키마는 다음과 같습니다.

| 열 | 필수 | 형식/설명 |
| --- | --- | --- |
| `date` | Y | `YYYY-MM-DD` |
| `type` | Y | `income` 또는 `expense` |
| `category` | Y | 등록된 카테고리 |
| `amount` | Y | 0보다 큰 정수 |
| `memo` | N | 문자열 |
| `tags` | N | 쉼표로 구분한 문자열 |

모든 행을 검증한 후 임시 파일을 원본과 교체하므로, 중간에 잘못된 행이 있으면 일부 거래만 반영되지 않고 가져오기 전체가 취소됩니다. 가져온 거래에는 기존 id와 충돌하지 않도록 새로운 고유 id가 생성됩니다.

### 4. 거래 검색

`search`는 기간, 거래 타입, 카테고리, 메모 검색어, 태그 조건을 조합해 필요한 거래만 찾습니다. 여러 조건을 함께 전달하면 모두 만족하는 거래만 출력됩니다.

```console
python -m budget_app search --from 2026-10-01 --to 2026-10-31 --type expense
python -m budget_app search --category food --q 저녁 --tag team
```

첫 번째 명령으로 10월 지출 전체를 확인하고, 두 번째 명령으로 방금 추가한 거래가 카테고리·검색어·태그의 AND 조건에 맞게 조회되는지 확인합니다. 검색 결과도 한 건씩 `yield`하므로 결과 전체를 별도 리스트에 쌓지 않습니다.

### 5. 거래 수정

`update`는 고유 id로 거래를 찾고 지정한 필드만 변경합니다. 다음 예시는 추가 단계에서 등록한 거래의 금액과 메모만 수정하고, 목록을 다시 조회해 변경 결과를 확인합니다.

```console
python -m budget_app update --id <FOOD_ID> --amount 320000 --memo "팀 저녁 식사(수정)"
python -m budget_app list --limit 10
```

수정할 때 원본 파일을 직접 덮어쓰지 않습니다. 기존 거래를 읽어 임시 JSONL 파일에 수정 결과를 모두 기록하고 `flush`와 `fsync`를 수행한 뒤 `os.replace`로 교체해, 처리 도중 오류가 나도 원본 파일이 잘릴 위험을 줄였습니다. 빈 `--memo ""` 또는 `--tags ""`를 전달하면 기존 값을 지울 수 있습니다.

### 6. 예산 설정과 월별 요약

`budget set`은 월별 지출 한도를 저장하고, `summary`는 해당 월의 총 수입·총 지출·잔액과 지출 카테고리 TOP N을 집계합니다. 예산이 설정된 달에는 사용률과 초과 여부도 함께 계산합니다.

```console
python -m budget_app budget set --month 2026-10 --amount 1000000
python -m budget_app summary --month 2026-10 --top 3
```

예제 데이터가 정상적으로 반영되었다면 총 수입 `3,350,000원`, 총 지출 `1,350,000원`, 잔액 `2,000,000원`, 예산 사용률 `135.0%`와 `350,000원` 초과 경고가 출력됩니다. 이를 통해 거래 데이터와 별도로 저장한 예산이 요약 계산에 결합되는 것을 확인할 수 있습니다.

### 7. CSV 내보내기

`export`는 다른 프로그램에서 활용하거나 백업할 수 있도록 지정한 기간의 거래를 CSV로 저장합니다. 기간 없는 전체 데이터의 실수 내보내기를 막기 위해 `--month`, `--from`, `--to` 중 하나 이상의 조건이 필요합니다.

```console
python -m budget_app export --out ./demo-export.csv --month 2026-10
```

생성된 파일은 가져오기와 동일한 UTF-8·헤더·컬럼 스키마를 사용합니다. 따라서 별도 데이터 폴더에서 다음과 같이 다시 가져와 호환성을 확인할 수 있습니다.

```console
python -m budget_app --data-dir ./demo-import-data import --from ./demo-export.csv
python -m budget_app --data-dir ./demo-import-data list --limit 10
```

내보낸 파일에는 헤더와 거래 13건이 들어 있습니다. 새 데이터 폴더에서도 같은 거래가 조회되며, 다시 가져온 거래에는 원본과 충돌하지 않는 새로운 UUID가 부여됩니다.

### 8. 잘못된 CSV의 원자적 실패 확인

`demo_import_invalid.csv`는 첫 번째 데이터 행은 정상이지만 다음 행의 날짜가 존재하지 않는 `2026-02-30`입니다. 별도 데이터 폴더에 가져오기를 시도해 일부 행만 저장되지 않는지 확인합니다.

```console
python -m budget_app --data-dir ./demo-invalid-data import --from ./examples/demo_import_invalid.csv
python -m budget_app --data-dir ./demo-invalid-data list --limit 10
```

예상 핵심 출력은 다음과 같습니다.

```text
오류: CSV 3행이 올바르지 않습니다: 날짜 형식이 올바르지 않습니다: 2026-02-30
해결: YYYY-MM-DD 형식으로 입력하세요. 예: 2026-09-16
거래 내역이 없습니다.
```

첫 번째 정상 행도 저장되지 않는 것이 핵심입니다. 가져오기 도중 검증에 실패하면 임시 파일만 삭제하고 원본은 교체하지 않기 때문에 부분 성공으로 인한 데이터 불일치를 막습니다.

### 9. 카테고리 관리

카테고리는 거래 입력값을 일관되게 유지하기 위한 별도 데이터입니다. 새 카테고리를 추가하고 목록에서 확인한 다음, 사용하지 않는 카테고리를 삭제할 수 있습니다.

```console
python -m budget_app category add --name health
python -m budget_app category list
python -m budget_app category remove --name health
python -m budget_app category remove --name rent
```

마지막 명령은 가져온 월세 거래가 `rent`를 사용하고 있으므로 다음 오류와 해결 방법을 출력하고 종료 코드 `2`로 실패합니다.

```text
오류: 사용 중인 카테고리는 삭제할 수 없습니다: rent
해결: 해당 거래의 카테고리를 먼저 수정하거나 삭제하세요.
```

VS Code PowerShell 터미널에서 `$LASTEXITCODE`를 입력하면 종료 코드를 확인할 수 있습니다. 사용 중인 카테고리를 먼저 제거하지 못하게 해 거래가 존재하지 않는 카테고리를 참조하는 상황을 방지하는 것이 이 규칙의 목적입니다.

### 10. 거래 삭제와 영속성 확인

`delete`는 고유 id로 선택한 거래 한 건을 삭제합니다. 수정과 마찬가지로 임시 파일을 완성한 뒤 원자적으로 교체해 원본 파일을 안전하게 갱신합니다.

```console
python -m budget_app delete --id <FOOD_ID>
python -m budget_app list --limit 10
python -m budget_app budget show --month 2026-10
python -m budget_app category list
```

각 명령은 별도의 프로세스로 실행되지만 거래·예산·카테고리가 `./data`의 서로 다른 JSONL 파일에 저장되므로 다시 실행해도 상태가 유지됩니다. 삭제 결과와 함께 예산 및 카테고리까지 남아 있는 것으로 세 종류 이상의 데이터가 영구 저장되는 것을 확인합니다.

### 11. 반복 거래

월급, 월세, 구독료처럼 매월 반복되는 항목은 규칙으로 등록한 뒤 원하는 월의 실제 거래로 생성합니다. 다음 예시는 31일 월세 규칙을 2월에 적용해 존재하지 않는 날짜를 그달의 마지막 날로 자동 조정하는 기능을 보여 줍니다.

```console
python -m budget_app recurring add --type expense --day 31 --category rent --amount 700000 --tags "fixed,home"
python -m budget_app recurring list
python -m budget_app recurring generate --month 2026-02
python -m budget_app recurring generate --month 2026-02
python -m budget_app search --from 2026-02-01 --to 2026-02-28
python -m budget_app recurring remove --id <rule-id>
```

두 번째 `generate`에서는 같은 규칙과 월로 이미 만들어진 거래를 찾아 중복 생성을 건너뜁니다. 반복 규칙이 참조하는 카테고리도 규칙을 삭제하기 전에는 제거할 수 없어 참조 관계를 보호합니다.

첫 번째 생성에서는 2월에 31일이 없으므로 28일 거래가 만들어집니다. 두 번째 실행 결과가 `생성=0, 중복 건너뜀=1`인지 확인하면 같은 규칙을 반복 실행해도 거래가 중복되지 않는다는 것을 보여 줄 수 있습니다.

### 12. 데이터 백업과 실행 시간 확인

`backup`은 거래·카테고리·예산·반복 규칙 파일과 생성 정보가 담긴 `manifest.json`을 타임스탬프 ZIP으로 보관합니다. ZIP 역시 임시 파일을 완성한 후 최종 이름으로 교체해 불완전한 백업 파일이 남을 가능성을 줄였습니다.

```console
python -m budget_app backup
python -m budget_app --verbose list --limit 3
```

기본 백업 위치는 `./data/backups`이며 파일명은 `budget-backup-YYYYMMDD-HHMMSS-ffffff.zip` 형식입니다. `--verbose`는 공통 데코레이터가 측정한 명령 실행 시간을 추가로 출력해, 각 명령의 본래 로직에 시간 측정 코드를 반복하지 않았음을 보여 줍니다.

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

“`cli.py`는 명령 해석과 출력, `services.py`는 검증·집계·참조 무결성 같은 업무 규칙, `repositories.py`는 JSONL 파일 I/O와 원자적 교체를 담당합니다. `models.py`는 데이터 계약, `validators.py`는 입력 규칙, `formatters.py`는 표현, `decorators.py`는 공통 오류·시간 처리로 분리했습니다. `Transaction` 같은 데이터 클래스와 `TransactionRepository`, `CategoryStore`, `BudgetStore`, `LedgerService` 같은 동작 클래스를 나눠 한 클래스가 여러 계층의 책임을 갖지 않게 했습니다.”

“update/delete는 원본을 열어 직접 수정하지 않습니다. 원본을 제너레이터로 읽어 같은 디렉터리의 임시 파일에 새 내용을 쓰고, flush와 `fsync` 후 `os.replace`합니다. 쓰기나 검증이 실패하면 임시 파일만 삭제하므로 원본이 보존됩니다.”

## 클래스
```
Transaction, Budget, MonthlySummary, RecurringRule : 가계부 데이터
TransactionRepository : 거래 파일의 영속성
CategoryStore, BudgetStore, RecurringStore : 각 종류의 데이터를 별도 파일에 저장
CategoryStore, BudgetStore, RecurringStore : 각 종류의 데이터를 별도 파일에 저장
LedgerService : 검증 및 흐름 제어
BackupManager : 백업
```

## 오류와 종료 코드

유효하지 않은 날짜·금액·타입·카테고리, 없는 id, 잘못된 CSV에는 `오류:`와 가능한 경우 `해결:` 문구를 출력합니다. 정상 종료 코드는 `0`, 업무 규칙 또는 입력 오류는 `2`, 취소는 `130`입니다.

## 테스트

표준 라이브러리 테스트 러너로 전체 테스트를 실행합니다.

```console
python -m unittest discover -s tests -v
```
