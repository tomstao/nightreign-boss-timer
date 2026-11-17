"""Command-line version of the timer: watch the game, print fights, append them to the CSV.

    uv run python -m nightreign_boss_timer

This is the first runnable form, before the overlay and settings window exist. It uses the
default regions for a 16:9 game image and is stopped with Ctrl+C.
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta
from pathlib import Path

from nightreign_boss_timer.names import UNKNOWN, NameVote, language_of
from nightreign_boss_timer.records import FightRecord, RecordStore, format_duration
from nightreign_boss_timer.regions import Box, bar_region, defeat_text_region, name_region
from nightreign_boss_timer.tracker import FightOutcome, FightTracker

GAME_TITLE = "ELDEN RING NIGHTREIGN"
IDLE_RATE = 2.0  # samples per second while no bar is on screen
FIGHT_RATE = 10.0  # samples per second during a fight
WINDOW_RETRY_S = 2.0


def default_records_path() -> Path:
    return Path.home() / "Documents" / "nightreign-boss-timer" / "records.csv"


def to_record(
    outcome: FightOutcome, table: str, now: float, wall_now: datetime, boss: str = UNKNOWN
) -> FightRecord:
    """Turn a tracker outcome into a row. ``now`` is the tracker's clock at ``wall_now``."""
    started = wall_now - timedelta(seconds=now - outcome.started_at)
    return FightRecord(
        started_at=started.replace(microsecond=0),
        table=table,
        boss=boss,
        language=language_of(boss),
        status=outcome.status,
        duration_s=round(outcome.duration_s, 1),
        start_hp_pct=outcome.start_hp_pct,
        end_hp_pct=outcome.end_hp_pct,
    )


def describe(record: FightRecord) -> str:
    return (
        f"{record.started_at:%H:%M:%S}  {record.status.value:<10}  "
        f"{format_duration(record.duration_s)}  HP {record.start_hp_pct}% -> {record.end_hp_pct}%"
        f"  {record.boss}"
    )


def run(title: str, table: str, records: Path) -> None:
    # Imported here so the rest of this module can be used and tested without Windows.
    from nightreign_boss_timer.capture import ScreenGrabber, enable_dpi_awareness, find_window
    from nightreign_boss_timer.defeat_text import measure_defeat_text
    from nightreign_boss_timer.detector import measure_bar
    from nightreign_boss_timer.ocr import NameReader

    enable_dpi_awareness()
    try:
        reader = NameReader()
    except FileNotFoundError as error:
        reader = None
        print(f"Boss names will not be read. {error}")
    store = RecordStore(records)
    tracker = FightTracker()
    print(f"Table: {table}    Records: {records}")
    print("Waiting for the game window. Press Ctrl+C to stop.")

    window: Box | None = None
    bar_box = defeat_box = name_box = None
    bar_grabber = defeat_grabber = name_grabber = None
    was_in_fight = False
    vote = NameVote()
    try:
        while True:
            found = find_window(title)
            current = Box(found.left, found.top, found.width, found.height) if found else None
            if current is None or current.width < 100 or current.height < 100:
                if window is not None:
                    print("Game window lost.")
                window = None
                time.sleep(WINDOW_RETRY_S)
                continue
            if current != window:
                window = current
                bar_box, defeat_box = bar_region(window), defeat_text_region(window)
                name_box = name_region(window)
                for grabber in (bar_grabber, defeat_grabber, name_grabber):
                    if grabber:
                        grabber.close()
                bar_grabber = ScreenGrabber(bar_box.width, bar_box.height)
                defeat_grabber = ScreenGrabber(defeat_box.width, defeat_box.height)
                name_grabber = ScreenGrabber(name_box.width, name_box.height)
                print(f"Watching the game at {window.width}x{window.height}.")

            now = time.monotonic()
            bar = measure_bar(bar_grabber.grab(bar_box.left, bar_box.top))
            defeat = tracker.watching_for_defeat and (
                measure_defeat_text(defeat_grabber.grab(defeat_box.left, defeat_box.top)).visible
            )
            outcome = tracker.update(now, bar, defeat)

            if tracker.in_fight and not was_in_fight:
                print("Boss bar seen, timing.")
                vote = NameVote()
            # Read the name on a few samples early in the fight, then leave the model alone.
            if reader and tracker.in_fight and bar.present and not vote.settled:
                reading = reader.read(name_grabber.grab(name_box.left, name_box.top))
                vote.add(reading.text, reading.confidence)
                if vote.settled:
                    print(f"Boss: {vote.name}")
            was_in_fight = tracker.in_fight
            if outcome:
                record = to_record(outcome, table, now, datetime.now(), vote.name)
                saved = store.append(record)
                note = "" if saved else "  (file is open elsewhere, held for later)"
                print(describe(record) + note)

            rate = FIGHT_RATE if tracker.in_fight or bar.present else IDLE_RATE
            time.sleep(max(0.0, 1.0 / rate - (time.monotonic() - now)))
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        for grabber in (bar_grabber, defeat_grabber, name_grabber):
            if grabber:
                grabber.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="nightreign-boss-timer", description="Record boss fight times from the screen."
    )
    parser.add_argument("--table", default="Arena", help="table to save fights under")
    parser.add_argument("--records", type=Path, default=None, help="path of the records CSV")
    parser.add_argument("--title", default=GAME_TITLE, help="title of the game window")
    args = parser.parse_args()
    run(args.title, args.table, args.records or default_records_path())


if __name__ == "__main__":
    main()
