from datetime import datetime
from pathlib import Path

import pytest

from nightreign_boss_timer import records
from nightreign_boss_timer.records import FightRecord, RecordStore, Status, format_duration


def make_record(**changes: object) -> FightRecord:
    values: dict[str, object] = {
        "started_at": datetime(2026, 11, 17, 21, 4, 33),
        "table": "Arena",
        "boss": "Tree Sentinel",
        "language": "en",
        "status": Status.INCOMPLETE,
        "duration_s": 161.3,
        "start_hp_pct": 100,
        "end_hp_pct": 62,
    }
    values.update(changes)
    return FightRecord(**values)  # type: ignore[arg-type]


def lock_main_file(monkeypatch: pytest.MonkeyPatch, store: RecordStore) -> None:
    """Make writes to the main file fail the way they do while Excel has it open."""
    real_append = records._append_rows

    def locked(path: Path, rows: list[list[str]]) -> None:
        if path == store.path:
            raise PermissionError("file is open in another program")
        real_append(path, rows)

    monkeypatch.setattr(records, "_append_rows", locked)


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "00:00.0"),
        (75.84, "01:15.8"),
        (59.96, "01:00.0"),
        (161.3, "02:41.3"),
        (4503.2, "75:03.2"),
    ],
)
def test_format_duration(seconds: float, expected: str) -> None:
    assert format_duration(seconds) == expected


def test_format_duration_rejects_negative() -> None:
    with pytest.raises(ValueError, match="negative"):
        format_duration(-1)


def test_append_then_read_round_trips(tmp_path: Path) -> None:
    store = RecordStore(tmp_path / "records.csv")
    first = make_record()
    second = make_record(
        started_at=datetime(2026, 11, 17, 21, 12, 5),
        status=Status.COMPLETE,
        duration_s=75.8,
        start_hp_pct=62,
        end_hp_pct=0,
    )

    assert store.append(first) is True
    assert store.append(second) is True

    assert store.read_all() == [first, second]


def test_file_has_one_byte_order_mark_and_one_header(tmp_path: Path) -> None:
    store = RecordStore(tmp_path / "records.csv")
    store.append(make_record())
    store.append(make_record())

    raw = store.path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    assert raw.count(b"\xef\xbb\xbf") == 1
    assert raw.count(b"started_at") == 1


def test_chinese_and_comma_names_survive(tmp_path: Path) -> None:
    store = RecordStore(tmp_path / "records.csv")
    simplified = make_record(boss="大树守卫", language="zh_CN", table="练习, 无伤")
    traditional = make_record(boss="大樹守衛", language="zh_TW")

    store.append(simplified)
    store.append(traditional)

    assert store.read_all() == [simplified, traditional]


def test_creates_missing_folder(tmp_path: Path) -> None:
    store = RecordStore(tmp_path / "new" / "folder" / "records.csv")
    store.append(make_record())
    assert store.path.exists()


def test_locked_file_holds_record_as_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = RecordStore(tmp_path / "records.csv")
    lock_main_file(monkeypatch, store)

    assert store.append(make_record()) is False

    assert store.pending_count() == 1
    assert store.read_all() == []


def test_pending_records_are_written_first_once_unlocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = RecordStore(tmp_path / "records.csv")
    saved = make_record(boss="saved before the lock")
    held_1 = make_record(boss="held 1")
    held_2 = make_record(boss="held 2")
    after = make_record(boss="after the lock")
    store.append(saved)

    with monkeypatch.context() as locked:
        lock_main_file(locked, store)
        store.append(held_1)
        store.append(held_2)
        assert store.pending_count() == 2

    assert store.append(after) is True

    assert store.read_all() == [saved, held_1, held_2, after]
    assert store.pending_count() == 0
    assert not store.pending_path.exists()


def test_read_all_on_missing_file_is_empty(tmp_path: Path) -> None:
    assert RecordStore(tmp_path / "records.csv").read_all() == []
