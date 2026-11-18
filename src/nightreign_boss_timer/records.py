"""Fight records and the CSV file they are stored in.

The store is one CSV file that opens directly in Excel. It is written as UTF-8 with a byte
order mark so Excel shows Chinese boss names correctly. Excel locks a file while it is open,
so a row that cannot be appended is kept in a pending file next to it and written later.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path

COLUMNS = (
    "started_at",
    "table",
    "boss",
    "language",
    "status",
    "duration",
    "duration_s",
    "start_hp_pct",
    "end_hp_pct",
)

_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class Status(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


def format_duration(seconds: float) -> str:
    """Format seconds as ``mm:ss.s``. Minutes keep counting past 59."""
    if seconds < 0:
        raise ValueError("duration cannot be negative")
    tenths = round(seconds * 10)
    minutes, rest = divmod(tenths, 600)
    return f"{minutes:02d}:{rest // 10:02d}.{rest % 10}"


@dataclass(frozen=True, slots=True)
class FightRecord:
    """One boss fight, from the bar appearing to the bar going away."""

    started_at: datetime
    table: str
    boss: str
    language: str
    status: Status
    duration_s: float
    start_hp_pct: int
    end_hp_pct: int

    def to_row(self) -> list[str]:
        return [
            self.started_at.strftime(_TIME_FORMAT),
            self.table,
            self.boss,
            self.language,
            self.status.value,
            format_duration(self.duration_s),
            f"{self.duration_s:.1f}",
            str(self.start_hp_pct),
            str(self.end_hp_pct),
        ]

    @classmethod
    def from_row(cls, row: dict[str, str]) -> FightRecord:
        return cls(
            started_at=datetime.strptime(row["started_at"], _TIME_FORMAT),
            table=row["table"],
            boss=row["boss"],
            language=row["language"],
            status=Status(row["status"]),
            duration_s=float(row["duration_s"]),
            start_hp_pct=int(row["start_hp_pct"]),
            end_hp_pct=int(row["end_hp_pct"]),
        )


def _append_rows(path: Path, rows: list[list[str]]) -> None:
    """Append rows, writing the byte order mark and header first if the file is new."""
    is_new = not path.exists() or path.stat().st_size == 0
    # "utf-8-sig" writes a byte order mark at the start of every write session, so it is only
    # used for the first write. Later appends use plain UTF-8.
    encoding = "utf-8-sig" if is_new else "utf-8"
    with path.open("a", newline="", encoding=encoding) as handle:
        writer = csv.writer(handle)
        if is_new:
            writer.writerow(COLUMNS)
        writer.writerows(rows)


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


class RecordStore:
    """Appends fight records to a CSV file and reads them back."""

    def __init__(self, path: Path) -> None:
        self.set_path(path)

    def append(self, record: FightRecord) -> bool:
        """Save a record. Returns False if it had to be held in the pending file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.flush_pending():
            try:
                _append_rows(self.path, [record.to_row()])
            except PermissionError:
                pass
            else:
                return True
        # Earlier rows are still waiting, or the file is locked. Queue behind them to keep order.
        _append_rows(self.pending_path, [record.to_row()])
        return False

    def flush_pending(self) -> bool:
        """Move held rows into the main file. Returns True if nothing is left waiting."""
        waiting = _read_rows(self.pending_path)
        if not waiting:
            return True
        rows = [[row[column] for column in COLUMNS] for row in waiting]
        try:
            _append_rows(self.path, rows)
        except PermissionError:
            return False
        self.pending_path.unlink()
        return True

    def set_path(self, path: Path) -> None:
        """Save to another file from now on. Rows already written stay where they are."""
        self.path = path
        self.pending_path = path.with_name(f"{path.stem}.pending{path.suffix}")

    def ensure_file(self) -> None:
        """Create the file with its header row if it is not there yet, so it can be opened."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            _append_rows(self.path, [])

    def pending_count(self) -> int:
        return len(_read_rows(self.pending_path))

    def read_all(self) -> list[FightRecord]:
        """All saved records, oldest first. Rows still pending are not included."""
        return [FightRecord.from_row(row) for row in _read_rows(self.path)]
