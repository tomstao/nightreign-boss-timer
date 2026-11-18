import json
from importlib import resources

import pytest

from nightreign_boss_timer import boss_names
from nightreign_boss_timer.boss_names import BossMatch, BossNames

NAMES = boss_names.load()


def rows() -> list[list[str]]:
    text = resources.files("nightreign_boss_timer").joinpath("boss_names.json").read_text("utf-8")
    return json.loads(text)


def test_list_is_complete_rows_without_repeats() -> None:
    listed = rows()
    assert len(listed) == len(NAMES) > 200
    assert all(
        len(row) == 3 and all(name.strip() == name and name for name in row) for row in listed
    )
    assert len({tuple(row) for row in listed}) == len(listed)
    # English is in Latin letters, Chinese is not.
    assert all(row[0].isascii() for row in listed)
    assert all(not row[1].isascii() and not row[2].isascii() for row in listed)


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("Tree Sentinel", "en"),
        ("大树守卫", "zh_CN"),
        ("大樹守衛", "zh_TW"),
    ],
)
def test_a_name_is_found_in_each_language(text: str, language: str) -> None:
    assert NAMES.lookup(text) == BossMatch(text, language, "Tree Sentinel", "大树守卫", "大樹守衛")


@pytest.mark.parametrize(
    ("simplified", "english"),
    [
        ("黄金河马", "Golden Hippopotamus"),
        ("铃珠猎人", "Bell Bearing Hunter"),
        ("卡利亚禁卫骑士", "Royal Carian Knight"),
        ("老狮子", "Elder Lion"),
        ("黄金树的化身", "Erdtree Avatar"),
        ("神谕众使者", "Oracle Envoys"),
        ("龙装大树守卫", "Draconic Tree Sentinel"),
    ],
)
def test_names_seen_in_footage_are_in_the_list(simplified: str, english: str) -> None:
    match = NAMES.lookup(simplified)
    assert match is not None
    assert (match.language, match.en) == ("zh_CN", english)


def test_case_spaces_and_punctuation_do_not_matter() -> None:
    assert NAMES.lookup("  tree  sentinel ").name == "Tree Sentinel"
    # The model often drops the quote marks around a Nightlord's title.
    match = NAMES.lookup("黑夜野兽格拉狄乌斯")
    assert match.name == "“黑夜野兽”格拉狄乌斯"
    assert match.en == "Gladius, Beast of Night"
    assert NAMES.lookup("「黑夜野獸」格拉狄烏斯").language == "zh_TW"


def test_a_reading_one_character_off_is_repaired() -> None:
    assert NAMES.lookup("大树守卩").name == "大树守卫"  # not 大树守卫们, which is two changes away
    assert NAMES.lookup("Tree Sentine1").name == "Tree Sentinel"
    assert NAMES.lookup("Golden Hipopotamus").name == "Golden Hippopotamus"
    assert NAMES.lookup("卡利亚禁卫骑土").en == "Royal Carian Knight"


def test_short_names_must_match_exactly() -> None:
    assert NAMES.lookup("白角").en == "White Horn"
    assert NAMES.lookup("白用") is None
    assert NAMES.lookup("老狮于") is None  # three characters: too short to repair safely


def test_text_that_is_no_boss_is_not_matched() -> None:
    for text in ("", "   ", "unknown", "Arena", "血刃", "Tree", "完全不是名字的文字"):
        assert NAMES.lookup(text) is None


def test_name_written_the_same_in_both_kinds_of_chinese() -> None:
    match = NAMES.lookup("王室幽魂")
    assert match == BossMatch("王室幽魂", "zh", "Royal Revenant", "王室幽魂", "王室幽魂")


def test_a_name_with_two_translations_leaves_that_translation_empty() -> None:
    names = BossNames([["Omen", "恶兆之子", "惡兆之子"], ["Omen", "恶兆之子们", "惡兆之子們"]])
    assert names.lookup("Omen") == BossMatch("Omen", "en", "Omen", "", "")
    assert names.lookup("恶兆之子们") == BossMatch(
        "恶兆之子们", "zh_CN", "Omen", "恶兆之子们", "惡兆之子們"
    )


def test_two_names_equally_close_give_no_match() -> None:
    names = BossNames(
        [["Night Hunter A", "夜猎人甲", "夜獵人甲"], ["Night Hunter B", "夜猎人乙", "夜獵人乙"]]
    )
    assert names.lookup("Night Hunter C") is None
    assert names.lookup("夜猎人丙") is None
