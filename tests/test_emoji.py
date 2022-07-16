from naff.models.discord.emoji import PartialEmoji, process_emoji_req_format, process_emoji

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
    dict_sample = {"id": 910496037708374016, "name": "sparklesnek", "animated": True}
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
