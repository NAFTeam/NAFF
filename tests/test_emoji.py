import string

import emoji

from naff.models.discord.emoji import PartialEmoji, process_emoji, process_emoji_req_format

__all__ = ()


def test_emoji_comparisons() -> None:
    thumbs_emoji = "👍"
    custom_emoji = "<:sparklesnek:910496037708374016>"

    e = PartialEmoji.from_str(thumbs_emoji)
    assert not e == thumbs_emoji
    assert e.name == thumbs_emoji

    e = PartialEmoji.from_str(custom_emoji)
    assert not e == custom_emoji
    assert e.name == "sparklesnek"
    assert e.id == 910496037708374016


def test_emoji_formatting() -> None:
    sample = "<:sparklesnek:910496037708374016>"
    target = "sparklesnek:910496037708374016"

    emoji = PartialEmoji.from_str(sample)

    assert emoji.req_format == target
    assert process_emoji_req_format(sample) == target
    assert process_emoji_req_format({"id": 910496037708374016, "name": "sparklesnek", "animated": True}) == target


def test_emoji_processing() -> None:
    raw_sample = "<:sparklesnek:910496037708374016>"
    dict_sample = {"id": 910496037708374016, "name": "sparklesnek", "animated": False}
    unicode_sample = "👍"
    target = "sparklesnek:910496037708374016"

    assert process_emoji_req_format(raw_sample) == target
    assert process_emoji_req_format(dict_sample) == target
    assert process_emoji_req_format(unicode_sample) == unicode_sample

    raw_emoji = process_emoji(raw_sample)
    dict_emoji = process_emoji(dict_sample)
    unicode_emoji = process_emoji(unicode_sample)

    assert isinstance(raw_emoji, dict) and raw_emoji == dict_sample
    assert isinstance(dict_emoji, dict) and dict_emoji == dict_sample
    assert isinstance(unicode_emoji, dict) and unicode_emoji == {"name": "👍", "animated": False}

    from_str = PartialEmoji.from_str(raw_sample)
    assert from_str.req_format == target
    assert from_str.id == 910496037708374016
    assert from_str.name == "sparklesnek"
    assert from_str.animated is False
    assert str(from_str) == raw_sample

    assert PartialEmoji.from_str("<a:sparklesnek:910496037708374016>").animated is True


def test_unicode_recognition() -> None:
    for _e in emoji.EMOJI_DATA:
        assert PartialEmoji.from_str(_e) is not None


def test_regional_indicators() -> None:
    regional_indicators = [
        "🇦",
        "🇧",
        "🇨",
        "🇩",
        "🇪",
        "🇫",
        "🇬",
        "🇭",
        "🇮",
        "🇯",
        "🇰",
        "🇱",
        "🇲",
        "🇳",
        "🇴",
        "🇵",
        "🇶",
        "🇷",
        "🇸",
        "🇹",
        "🇺",
        "🇻",
        "🇼",
        "🇽",
        "🇾",
        "🇿",
    ]
    for _e in regional_indicators:
        assert PartialEmoji.from_str(_e) is not None


def test_numerical_emoji() -> None:
    numerical_emoji = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    for _e in numerical_emoji:
        assert PartialEmoji.from_str(_e) is not None


def test_false_positives() -> None:
    for _e in string.printable:
        assert PartialEmoji.from_str(_e) is None
