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


def test_ensure_file_writes_the_header_once(tmp_path: Path) -> None:
    store = RecordStore(tmp_path / "new folder" / "records.csv")
    store.ensure_file()
    store.ensure_file()
    assert store.path.read_text(encoding="utf-8-sig").splitlines() == [",".join(records.COLUMNS)]
    assert store.read_all() == []


def test_remove_last_takes_the_newest_row_and_keeps_the_rest(tmp_path: Path) -> None:
    store = RecordStore(tmp_path / "records.csv")
    first, second = make_record(boss="first"), make_record(boss="黄金河马")
    store.append(first)
    store.append(second)

    assert store.remove_last() == second
    assert store.read_all() == [first]
    assert store.path.read_bytes().startswith(b"\xef\xbb\xbf")  # still opens right in Excel
    assert not store.path.with_name("records.csv.tmp").exists()
    assert store.remove_last() == first
    assert store.read_all() == []
    assert store.remove_last() is None
    store.append(second)  # the emptied file still takes new rows
    assert store.read_all() == [second]


def test_remove_last_prefers_rows_still_waiting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = RecordStore(tmp_path / "records.csv")
    saved = make_record(boss="saved")
    store.append(saved)
    with monkeypatch.context() as locked:
        lock_main_file(locked, store)
        store.append(make_record(boss="held 1"))
        store.append(make_record(boss="held 2"))
        assert store.remove_last().boss == "held 2"
        assert store.pending_count() == 1
        assert store.remove_last().boss == "held 1"
        assert not store.pending_path.exists()
    assert store.read_all() == [saved]


def test_remove_last_changes_nothing_when_the_file_is_locked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = RecordStore(tmp_path / "records.csv")
    store.append(make_record())

    def refuse(self: Path, target: Path) -> None:
        raise PermissionError("open in Excel")

    monkeypatch.setattr(Path, "replace", refuse)
    with pytest.raises(PermissionError):
        store.remove_last()
    monkeypatch.undo()
    assert len(store.read_all()) == 1
    assert not store.path.with_name("records.csv.tmp").exists()


def test_remove_takes_out_the_given_records_and_keeps_the_rest(tmp_path: Path) -> None:
    store = RecordStore(tmp_path / "records.csv")
    first, second, third = make_record(), make_record(boss="Second"), make_record(boss="Third")
    for record in (first, second, third, second):
        store.append(record)

    assert store.remove([second, make_record(boss="Never saved")]) == 1
    assert store.read_all() == [first, third, second]  # of two identical rows one stays
    assert store.remove([first, third, second]) == 3
    assert store.read_all() == []
    assert store.remove([first]) == 0


def test_level_is_saved_and_read_back(tmp_path: Path) -> None:
    store = RecordStore(tmp_path / "records.csv")
    with_level, without = make_record(level=15), make_record(boss="Second")
    store.append(with_level)
    store.append(without)
    lines = store.path.read_text(encoding="utf-8-sig").splitlines()
    assert ",end_hp_pct,level," in lines[0]
    assert ",62,15," in lines[1]
    assert ",62,," in lines[2]
    assert store.read_all() == [with_level, without]


def test_second_and_third_names_are_saved_and_read_back(tmp_path: Path) -> None:
    store = RecordStore(tmp_path / "records.csv")
    record = make_record(
        boss="Golden Hippopotamus",
        language="en",
        boss_2="黄金河马",
        language_2="zh_CN",
        boss_3="黃金河馬",
        language_3="zh_TW",
    )
    store.append(record)
    lines = store.path.read_text(encoding="utf-8-sig").splitlines()
    assert lines[0].endswith(",level,boss_2,language_2,boss_3,language_3,character")
    assert lines[1].endswith(",黄金河马,zh_CN,黃金河馬,zh_TW,")
    assert store.read_all() == [record]


def test_columns_of_an_earlier_layout_are_dropped_on_the_next_save(tmp_path: Path) -> None:
    # For a short while the file had one column per language instead.
    path = tmp_path / "records.csv"
    level = records.COLUMNS.index("level")
    header = [*records.COLUMNS[: level + 1], "boss_en", "boss_zh_cn", "boss_zh_tw"]
    row = [
        *make_record(boss="大树守卫").to_row()[: level + 1],
        "Tree Sentinel",
        "大树守卫",
        "大樹守衛",
    ]
    path.write_text(",".join(header) + "\n" + ",".join(row) + "\n", encoding="utf-8-sig")
    store = RecordStore(path)
    assert store.read_all() == [make_record(boss="大树守卫")]

    store.append(make_record(boss="New"))

    lines = path.read_text(encoding="utf-8-sig").splitlines()
    assert lines[0] == ",".join(records.COLUMNS)
    assert store.read_all() == [make_record(boss="大树守卫"), make_record(boss="New")]


def test_file_from_before_the_newer_columns_gets_them_on_the_next_save(tmp_path: Path) -> None:
    path = tmp_path / "records.csv"
    old = records.COLUMNS.index("level")  # the first column an old file does not have
    old_header = ",".join(records.COLUMNS[:old])
    old_row = ",".join(make_record().to_row()[:old])
    path.write_text(f"{old_header}\n{old_row}\n", encoding="utf-8-sig")
    store = RecordStore(path)
    assert store.read_all() == [make_record()]  # readable as it is, with no level

    store.append(make_record(boss="New", level=7))

    lines = path.read_text(encoding="utf-8-sig").splitlines()
    assert lines[0] == ",".join(records.COLUMNS)
    assert all(line.count(",") == len(records.COLUMNS) - 1 for line in lines)
    assert store.read_all() == [make_record(), make_record(boss="New", level=7)]
    assert store.remove([make_record()]) == 1


def test_character_is_saved_and_read_back(tmp_path: Path) -> None:
    store = RecordStore(tmp_path / "records.csv")
    played, unset = make_record(character="追踪者"), make_record(boss="Second")
    store.append(played)
    store.append(unset)
    lines = store.path.read_text(encoding="utf-8-sig").splitlines()
    assert lines[0].endswith(",language_3,character")
    assert lines[1].endswith(",追踪者")
    assert lines[2].endswith(",")
    assert store.read_all() == [played, unset]


def test_file_from_before_the_character_column_gets_it_left_empty(tmp_path: Path) -> None:
    path = tmp_path / "records.csv"
    old_header = ",".join(records.COLUMNS[:-1])  # release 0.1.0 had every column but the last
    old_row = ",".join(make_record(level=7).to_row()[:-1])
    path.write_text(f"{old_header}\n{old_row}\n", encoding="utf-8-sig")
    store = RecordStore(path)
    assert store.read_all() == [make_record(level=7)]  # readable as it is, with no character
    assert store.read_all()[0].character == ""

    store.append(make_record(boss="New", character="Wylder"))

    lines = path.read_text(encoding="utf-8-sig").splitlines()
    assert lines[0] == ",".join(records.COLUMNS)
    assert all(line.count(",") == len(records.COLUMNS) - 1 for line in lines)
    assert store.read_all() == [make_record(level=7), make_record(boss="New", character="Wylder")]
    assert store.remove([make_record(level=7)]) == 1
