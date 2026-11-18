"""Command-line version of the timer: watch the game, print fights, append them to the CSV.

    uv run python -m nightreign_boss_timer

It reads the settings file if there is one, uses default regions for a 16:9 game image until
regions are calibrated, and is stopped with Ctrl+C.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from nightreign_boss_timer import settings as settings_file
from nightreign_boss_timer.engine import GAME_TITLE, Engine, State, records_path
from nightreign_boss_timer.names import UNKNOWN
from nightreign_boss_timer.records import FightRecord, RecordStore, format_duration


def describe(record: FightRecord) -> str:
    return (
        f"{record.started_at:%H:%M:%S}  {record.status.value:<10}  "
        f"{format_duration(record.duration_s)}  HP {record.start_hp_pct}% -> {record.end_hp_pct}%"
        f"  {record.boss}" + ("" if record.level is None else f"  level {record.level}")
    )


def run(title: str, table: str | None, records: Path | None) -> None:
    # Imported here so the rest of this module can be used and tested without Windows.
    from nightreign_boss_timer.capture import WindowsScreen, enable_dpi_awareness
    from nightreign_boss_timer.ocr import NameReader

    enable_dpi_awareness()
    settings = settings_file.load()
    if table:
        if table not in settings.table_names():
            settings.add_table(table)
        settings.set_active_table(table)
    path = records or records_path(settings)

    try:
        reader = NameReader()
    except FileNotFoundError as error:
        reader = None
        print(f"Boss names will not be read. {error}")

    print(f"Table: {settings.active_table}    Records: {path}")
    print("Waiting for the game window. Press Ctrl+C to stop.")
    state = boss = None
    with WindowsScreen() as screen:
        engine = Engine(settings, screen, RecordStore(path), reader, title=title)
        try:
            while True:
                result = engine.step()
                snapshot = result.snapshot
                if snapshot.state is not state:
                    if snapshot.state is State.FIGHT:
                        print("Boss bar seen, timing.")
                    elif snapshot.state is State.NO_GAME and state is not None:
                        print("Game window lost.")
                    elif snapshot.state is State.IDLE and state in (None, State.NO_GAME):
                        print("Watching the game.")
                    state, boss = snapshot.state, None
                if snapshot.state is State.FIGHT and snapshot.boss != UNKNOWN and not boss:
                    boss = snapshot.boss
                    print(f"Boss: {boss}")
                if result.record:
                    note = "" if result.saved else "  (file is open elsewhere, held for later)"
                    print(describe(result.record) + note)
                time.sleep(result.delay_s)
        except KeyboardInterrupt:
            print("Stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="nightreign-boss-timer", description="Record boss fight times from the screen."
    )
    parser.add_argument("--table", default=None, help="table to save fights under")
    parser.add_argument("--records", type=Path, default=None, help="path of the records CSV")
    parser.add_argument("--title", default=GAME_TITLE, help="title of the game window")
    args = parser.parse_args()
    run(args.title, args.table, args.records)


if __name__ == "__main__":
    main()
