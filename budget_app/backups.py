"""가계부 데이터의 복구 가능한 ZIP 백업 생성."""

from __future__ import annotations

import json
import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from budget_app.errors import StorageError

BACKUP_FILES = (
    "transactions.jsonl",
    "categories.jsonl",
    "budgets.jsonl",
    "recurring.jsonl",
)


class BackupManager:
    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)

    def create(self, output_dir: str | Path | None = None) -> Path:
        destination = Path(output_dir) if output_dir else self.data_dir / "backups"
        timestamp = datetime.now().astimezone()
        filename = f"budget-backup-{timestamp:%Y%m%d-%H%M%S-%f}.zip"
        output_path = destination / filename
        temp_path: Path | None = None
        try:
            destination.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=destination, suffix=".tmp", delete=False) as file:
                temp_path = Path(file.name)
            # 운영 데이터만 명시적으로 선택해 이전 백업이 다시 포함되는 일을 막는다.
            with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                included: list[str] = []
                for name in BACKUP_FILES:
                    source = self.data_dir / name
                    if not source.is_file():
                        raise StorageError(
                            f"백업할 데이터 파일이 없습니다: {source}",
                            "가계부 명령을 한 번 실행해 저장 파일을 초기화하세요.",
                        )
                    archive.write(source, arcname=name)
                    included.append(name)
                manifest = {
                    "created_at": timestamp.isoformat(),
                    "format_version": 1,
                    "files": included,
                }
                archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            with temp_path.open("r+b") as file:
                os.fsync(file.fileno())
            # ZIP 생성이 끝난 뒤에만 최종 파일명이 나타나므로 불완전한 백업을 피한다.
            os.replace(temp_path, output_path)
            return output_path
        except StorageError:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            raise
        except (OSError, zipfile.BadZipFile) as exc:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            raise StorageError(
                "백업 파일을 생성하지 못했습니다.",
                "출력 경로의 권한과 디스크 공간을 확인하세요.",
            ) from exc
