import pytest

from nightreign_boss_timer.hotkeys import (
    KEYS,
    MODIFIERS,
    Hotkey,
    HotkeyManager,
    bindings,
    conflict,
    has_modifier,
    normalise,
    parse,
)
from nightreign_boss_timer.settings import DEFAULT_HOTKEYS, Settings, default_tables


@pytest.mark.parametrize(
    ("written", "standard"),
    [
        ("Ctrl+Alt+P", "Ctrl+Alt+P"),
        ("alt + ctrl + p", "Ctrl+Alt+P"),
        ("SHIFT+WIN+f5", "Shift+Win+F5"),
        ("Ctrl+Alt+1", "Ctrl+Alt+1"),
        ("F9", "F9"),
        ("ctrl+pagedown", "Ctrl+PageDown"),
        ("Ctrl+Alt+num7", "Ctrl+Alt+Num7"),
        ("Ctrl+Ctrl+K", "Ctrl+K"),
        ("Ctrl+[", "Ctrl+["),
    ],
)
def test_normalise_writes_shortcuts_one_way(written: str, standard: str) -> None:
    assert normalise(written) == standard


@pytest.mark.parametrize(
    "written",
    ["", "   ", "Ctrl", "Ctrl+Alt", "Ctrl+A+B", "Ctrl+Hyper+K", "Ctrl+F25", "Ctrl++", "+"],
)
def test_what_is_not_a_shortcut(written: str) -> None:
    assert normalise(written) == ""
    assert parse(written) is None


def test_parse_gives_the_numbers_windows_wants() -> None:
    assert parse("Ctrl+Alt+P") == Hotkey(modifiers=0x0003, key=0x50)
    assert parse("Shift+F5") == Hotkey(modifiers=0x0004, key=0x74)
    assert parse("Win+1") == Hotkey(modifiers=0x0008, key=0x31)
    assert parse("F24") == Hotkey(modifiers=0, key=0x87)
    assert parse("Ctrl+Space") == Hotkey(modifiers=0x0002, key=0x20)


def test_every_key_name_survives_a_round_trip() -> None:
    for name, code in KEYS.items():
        assert normalise(f"ctrl+{name.lower()}") == f"Ctrl+{name}"
        assert parse(name) == Hotkey(0, code)
    assert len(set(KEYS.values())) == len(KEYS)  # no two names for one key
    assert list(MODIFIERS) == ["Ctrl", "Alt", "Shift", "Win"]


def test_single_keys_are_told_apart() -> None:
    assert has_modifier("Ctrl+Alt+P")
    assert not has_modifier("F5")
    assert not has_modifier("not a shortcut")


def test_default_settings_are_all_valid_and_free_of_conflicts() -> None:
    settings = Settings()
    wanted = bindings(settings)
    assert wanted == {
        "toggle_tracking": "Ctrl+Alt+P",
        "next_table": "Ctrl+Alt+T",
        "toggle_overlay": "Ctrl+Alt+O",
        "calibrate": "Ctrl+Alt+C",
        "table:Arena": "Ctrl+Alt+1",
        "table:Normal": "Ctrl+Alt+2",
    }
    assert len(set(wanted.values())) == len(wanted)
    assert all(normalise(shortcut) == shortcut for shortcut in DEFAULT_HOTKEYS.values() if shortcut)
    assert all(normalise(table.hotkey) == table.hotkey for table in default_tables())


def test_bindings_skip_unset_and_unreadable_shortcuts() -> None:
    settings = Settings()
    settings.hotkeys["end_fight"] = "ctrl + alt + e"
    settings.hotkeys["discard_last"] = "banana"
    settings.add_table("Co-op")
    wanted = bindings(settings)
    assert wanted["end_fight"] == "Ctrl+Alt+E"
    assert "discard_last" not in wanted
    assert "open_window" not in wanted
    assert "table:Co-op" not in wanted


def test_conflict_names_the_other_action() -> None:
    settings = Settings()
    assert conflict(settings, "end_fight", "alt+ctrl+p") == "toggle_tracking"
    assert conflict(settings, "end_fight", "Ctrl+Alt+1") == "table:Arena"
    assert conflict(settings, "toggle_tracking", "Ctrl+Alt+P") == ""  # its own shortcut
    assert conflict(settings, "end_fight", "Ctrl+Alt+E") == ""
    assert conflict(settings, "end_fight", "") == ""


class FakeWindows:
    def __init__(self) -> None:
        self.registered: dict[int, Hotkey] = {}
        self.taken: set[Hotkey] = set()  # held by "another program"
        self.calls: list[str] = []

    def register(self, hotkey_id: int, hotkey: Hotkey) -> bool:
        self.calls.append(f"register {hotkey_id}")
        if hotkey in self.taken or hotkey in self.registered.values():
            return False
        self.registered[hotkey_id] = hotkey
        return True

    def unregister(self, hotkey_id: int) -> None:
        self.calls.append(f"unregister {hotkey_id}")
        del self.registered[hotkey_id]

    def press(self, manager: HotkeyManager, shortcut: str) -> str:
        hotkey = parse(shortcut)
        for hotkey_id, registered in self.registered.items():
            if registered == hotkey:
                return manager.action_for(hotkey_id)
        return ""


def test_manager_registers_and_reports_presses() -> None:
    windows = FakeWindows()
    manager = HotkeyManager(windows.register, windows.unregister)
    manager.apply(bindings(Settings()))
    assert len(windows.registered) == 6
    assert manager.failed == set()
    assert windows.press(manager, "Ctrl+Alt+P") == "toggle_tracking"
    assert windows.press(manager, "Ctrl+Alt+2") == "table:Normal"
    assert manager.action_for(999) == ""


def test_manager_only_touches_what_changed() -> None:
    windows = FakeWindows()
    manager = HotkeyManager(windows.register, windows.unregister)
    settings = Settings()
    manager.apply(bindings(settings))
    windows.calls.clear()

    manager.apply(bindings(settings))
    assert windows.calls == []  # nothing changed, nothing asked of Windows

    settings.hotkeys["toggle_tracking"] = "Ctrl+Alt+F1"
    settings.hotkeys["next_table"] = ""
    settings.hotkeys["end_fight"] = "Ctrl+Alt+E"
    manager.apply(bindings(settings))
    assert sorted(call.split()[0] for call in windows.calls) == [
        "register",
        "register",
        "unregister",
        "unregister",
    ]
    assert windows.press(manager, "Ctrl+Alt+P") == ""
    assert windows.press(manager, "Ctrl+Alt+F1") == "toggle_tracking"
    assert windows.press(manager, "Ctrl+Alt+T") == ""
    assert windows.press(manager, "Ctrl+Alt+E") == "end_fight"


def test_a_freed_shortcut_can_go_to_another_action_in_one_step() -> None:
    windows = FakeWindows()
    manager = HotkeyManager(windows.register, windows.unregister)
    settings = Settings()
    manager.apply(bindings(settings))
    settings.hotkeys["toggle_tracking"] = ""
    settings.hotkeys["end_fight"] = "Ctrl+Alt+P"
    manager.apply(bindings(settings))
    assert manager.failed == set()
    assert windows.press(manager, "Ctrl+Alt+P") == "end_fight"


def test_refused_shortcuts_are_remembered_and_retried() -> None:
    windows = FakeWindows()
    windows.taken.add(parse("Ctrl+Alt+P"))
    manager = HotkeyManager(windows.register, windows.unregister)
    settings = Settings()
    manager.apply(bindings(settings))
    assert manager.failed == {"toggle_tracking"}
    assert len(windows.registered) == 5

    windows.taken.clear()  # the other program let go of it
    manager.apply(bindings(settings))
    assert manager.failed == set()
    assert windows.press(manager, "Ctrl+Alt+P") == "toggle_tracking"

    windows.taken.add(parse("Ctrl+Alt+E"))
    settings.hotkeys["end_fight"] = "Ctrl+Alt+E"
    manager.apply(bindings(settings))
    assert manager.failed == {"end_fight"}
    settings.hotkeys["end_fight"] = ""  # clearing it also clears the failure
    manager.apply(bindings(settings))
    assert manager.failed == set()


def test_release_all() -> None:
    windows = FakeWindows()
    manager = HotkeyManager(windows.register, windows.unregister)
    manager.apply(bindings(Settings()))
    manager.release_all()
    assert windows.registered == {}
