from dis_snek.models.discord.emoji import PartialEmoji

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

