import json
from importlib import resources

import pytest

from nightreign_boss_timer import characters


def rows() -> list[list[str]]:
    text = resources.files("nightreign_boss_timer").joinpath("characters.json").read_text("utf-8")
    return json.loads(text)


def test_list_is_complete_rows_without_repeats() -> None:
    listed = rows()
    assert len(listed) == len(characters.all_keys()) == 10
    assert all(
        len(row) == 3 and all(name.strip() == name and name for name in row) for row in listed
    )
    # English is in Latin letters, Chinese is not.
    assert all(row[0].isascii() for row in listed)
    assert all(not row[1].isascii() and not row[2].isascii() for row in listed)
    # No name stands for two characters, in any language.
    for column in range(3):
        assert len({row[column] for row in listed}) == len(listed)


def test_keys_are_the_english_names_in_the_order_of_the_file() -> None:
    assert characters.all_keys() == tuple(row[0] for row in rows())
    assert characters.all_keys()[0] == "Wylder"
    assert characters.all_keys()[-2:] == ("Scholar", "Undertaker")


@pytest.mark.parametrize("name", ["Wylder", "追踪者", "追蹤者", " wylder ", "WYLDER"])
def test_a_character_is_known_by_its_name_in_each_language(name: str) -> None:
    assert characters.key_of(name) == "Wylder"


@pytest.mark.parametrize("name", ["", "Priestess", "Tree Sentinel", "女巫"])
def test_other_names_are_no_character(name: str) -> None:
    assert characters.key_of(name) == ""


@pytest.mark.parametrize(
    ("language", "expected"),
    [("en", "Raider"), ("zh_CN", "无赖"), ("zh_TW", "無賴")],
)
def test_label_is_the_name_in_the_language_asked_for(language: str, expected: str) -> None:
    assert characters.label_of("无赖", language) == expected
    assert characters.label_of("Raider", language) == expected


def test_label_keeps_what_it_does_not_know() -> None:
    assert characters.label_of("", "zh_CN") == ""
    assert characters.label_of("My own build", "zh_CN") == "My own build"
    assert characters.label_of("Wylder", "fr") == "Wylder"


def test_every_character_has_a_name_in_every_language() -> None:
    for key in characters.all_keys():
        names = {characters.label_of(key, language) for language in characters.LANGUAGES}
        assert all(characters.key_of(name) == key for name in names)
