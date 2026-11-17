import re

import pytest

from nightreign_boss_timer.i18n import FALLBACK, LANGUAGES, Translator, load_catalogue
from nightreign_boss_timer.settings import DEFAULT_HOTKEYS, UI_LANGUAGES

PLACEHOLDER = re.compile(r"\{(\w+)\}")
OTHERS = [language for language in LANGUAGES if language != FALLBACK]


def test_languages_match_the_settings() -> None:
    assert LANGUAGES == UI_LANGUAGES


@pytest.mark.parametrize("language", OTHERS)
def test_every_language_has_exactly_the_english_keys(language: str) -> None:
    english = set(load_catalogue(FALLBACK))
    other = set(load_catalogue(language))
    assert other - english == set(), "keys that English does not have"
    assert english - other == set(), "keys still to be translated"


@pytest.mark.parametrize("language", OTHERS)
def test_placeholders_match_english(language: str) -> None:
    english = load_catalogue(FALLBACK)
    other = load_catalogue(language)
    for key, text in english.items():
        assert sorted(PLACEHOLDER.findall(other[key])) == sorted(PLACEHOLDER.findall(text)), key


@pytest.mark.parametrize("language", LANGUAGES)
def test_no_text_is_empty(language: str) -> None:
    assert [key for key, text in load_catalogue(language).items() if not text.strip()] == []


def test_chinese_files_are_actually_translated() -> None:
    # Names of languages and the word "Boss" are the same everywhere. Little else should be.
    english = load_catalogue(FALLBACK)
    for language in OTHERS:
        same = [key for key, text in load_catalogue(language).items() if text == english[key]]
        assert all(key.startswith("language.") or key == "records.column.boss" for key in same)


def test_simplified_and_traditional_differ() -> None:
    simplified, traditional = load_catalogue("zh_CN"), load_catalogue("zh_TW")
    different = [key for key in simplified if simplified[key] != traditional[key]]
    assert len(different) > len(simplified) / 2


def test_every_hotkey_action_has_a_label() -> None:
    english = load_catalogue(FALLBACK)
    assert [action for action in DEFAULT_HOTKEYS if f"hotkey.{action}" not in english] == []


def test_translator_fills_placeholders() -> None:
    assert Translator("en")("tray.table", table="Arena") == "Table: Arena"
    assert Translator("zh_CN")("tray.table", table="Arena") == "表格：Arena"
    assert Translator("zh_TW")("overlay.hp", percent=62) == "血量 62%"


def test_translator_survives_mistakes() -> None:
    translate = Translator("zh_CN")
    assert translate("no.such.key") == "no.such.key"
    assert translate("tray.table") == "表格：{table}"  # value forgotten: shown as is, no crash
    assert Translator("klingon").language == "en"


def test_language_can_be_switched() -> None:
    translate = Translator("en")
    assert translate("tray.quit") == "Quit"
    translate.language = "zh_TW"
    assert translate("tray.quit") == "結束"


def test_unsupported_catalogue_is_an_error() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        load_catalogue("klingon")
