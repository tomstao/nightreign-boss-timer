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
    "level",
    "boss_en",
    "boss_zh_cn",
    "boss_zh_tw",
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
    # The player's level when the fight began. None if it could not be read.
    level: int | None = None
    # The same boss in each language, when the name is in the list of known names. Empty
    # otherwise, and ``boss`` is then all there is: the text as it was read.
    boss_en: str = ""
    boss_zh_cn: str = ""
    boss_zh_tw: str = ""

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
            "" if self.level is None else str(self.level),
            self.boss_en,
            self.boss_zh_cn,
            self.boss_zh_tw,
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
            # Files written before the level was recorded have no such column.
            level=int(level) if (level := row.get("level") or "").isdecimal() else None,
            boss_en=row.get("boss_en") or "",
            boss_zh_cn=row.get("boss_zh_cn") or "",
            boss_zh_tw=row.get("boss_zh_tw") or "",
        )


def _values(row: dict[str, str]) -> list[str]:
    """A row read from a file as a list in column order. A column the file lacks is empty."""
    return [row.get(column) or "" for column in COLUMNS]


def _add_missing_columns(path: Path) -> None:
    """Rewrite a file made by an older version so that its header has every column."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        header = next(csv.reader(handle), None)
    if header is not None and tuple(header) != COLUMNS:
        _write_rows(path, _read_rows(path))


def _append_rows(path: Path, rows: list[list[str]]) -> None:
    """Append rows, writing the byte order mark and header first if the file is new."""
    is_new = not path.exists() or path.stat().st_size == 0
    if not is_new:
        _add_missing_columns(path)
    # "utf-8-sig" writes a byte order mark at the start of every write session, so it is only
    # used for the first write. Later appends use plain UTF-8.
    encoding = "utf-8-sig" if is_new else "utf-8"
    with path.open("a", newline="", encoding=encoding) as handle:
        writer = csv.writer(handle)
        if is_new:
            writer.writerow(COLUMNS)
        writer.writerows(rows)


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    """Replace the whole file with these rows. The swap is one step, so no half file is left."""
    partial = path.with_name(path.name + ".tmp")
    with partial.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        writer.writerows(_values(row) for row in rows)
    try:
        partial.replace(path)
    except PermissionError:
        partial.unlink()
        raise


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
        rows = [_values(row) for row in waiting]
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

    def remove_last(self) -> FightRecord | None:
        """Take the most recent record out of the store and return it. None if there is none.

        Raises PermissionError if the file is open in another program. Nothing is changed then.
        """
        waiting = _read_rows(self.pending_path)
        if waiting:
            last = waiting.pop()
            if waiting:
                _write_rows(self.pending_path, waiting)
            else:
                self.pending_path.unlink()
            return FightRecord.from_row(last)
        rows = _read_rows(self.path)
        if not rows:
            return None
        last = rows.pop()
        _write_rows(self.path, rows)
        return FightRecord.from_row(last)

    def remove(self, records: list[FightRecord]) -> int:
        """Take these records out of the file. Returns how many were found and removed.

        Each record removes one row that matches it in every column, so of two identical rows
        one stays. Rows still pending are not looked at. Raises PermissionError if the file is
        open in another program. Nothing is changed then.
        """
        rows = _read_rows(self.path)
        unwanted = [record.to_row() for record in records]
        kept = []
        for row in rows:
            values = _values(row)
            if values in unwanted:
                unwanted.remove(values)
            else:
                kept.append(row)
        removed = len(rows) - len(kept)
        if removed:
            _write_rows(self.path, kept)
        return removed

    def pending_count(self) -> int:
        return len(_read_rows(self.pending_path))

    def read_all(self) -> list[FightRecord]:
        """All saved records, oldest first. Rows still pending are not included."""
        return [FightRecord.from_row(row) for row in _read_rows(self.path)]
