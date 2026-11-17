from nightreign_boss_timer.names import AGREE, MAX_READS, NameVote, language_of


def test_no_readings_is_unknown() -> None:
    vote = NameVote()
    assert vote.name == "unknown"
    assert not vote.settled


def test_settles_once_one_answer_repeats() -> None:
    vote = NameVote()
    for _ in range(AGREE - 1):
        vote.add("黄金河马", 0.99)
    assert not vote.settled
    vote.add("黄金河马", 0.99)
    assert vote.settled
    assert vote.name == "黄金河马"


def test_majority_wins_over_a_misread() -> None:
    vote = NameVote()
    vote.add("黄金河乌", 0.8)  # something was in front of the last character
    vote.add("黄金河马", 0.99)
    vote.add("黄金河马", 0.98)
    assert vote.name == "黄金河马"


def test_uncertain_and_empty_readings_are_ignored() -> None:
    vote = NameVote()
    vote.add("黄金", 0.3)
    vote.add("", 0.0)
    vote.add("   ", 0.9)
    assert vote.name == "unknown"


def test_gives_up_after_enough_attempts() -> None:
    vote = NameVote()
    for _ in range(MAX_READS):
        vote.add("", 0.0)
    assert vote.settled
    assert vote.name == "unknown"


def test_language_of_names() -> None:
    assert language_of("Tree Sentinel") == "en"
    assert language_of("大树守卫") == "zh"
    assert language_of("大樹守衛") == "zh"
    assert language_of("unknown") == ""
    assert language_of("") == ""
