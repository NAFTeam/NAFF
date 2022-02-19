import discord_typings
import pytest

from dis_snek.client.client import Snake
from dis_snek.models.discord.channel import DM, GuildText
from dis_snek.models.discord.snowflake import to_snowflake
from tests.consts import SAMPLE_DM_DATA, SAMPLE_GUILD_DATA, SAMPLE_USER_DATA


@pytest.fixture()
def bot() -> Snake:
    return Snake()


def test_dm_channel(bot: Snake) -> None:

    channel = bot.cache.place_channel_data(SAMPLE_DM_DATA())
    assert isinstance(channel, DM)
    assert channel.recipient.id == to_snowflake(SAMPLE_USER_DATA()["id"])
    channel2 = bot.cache.get_channel(channel.id)
    assert channel2 is channel


def test_get_user_from_dm(bot: Snake) -> None:
    bot.cache.place_channel_data(SAMPLE_DM_DATA())
    user = bot.cache.get_user(to_snowflake(SAMPLE_USER_DATA()["id"]))
    assert user is not None
    assert user.username == SAMPLE_USER_DATA()["username"]


def test_guild_channel(bot: Snake) -> None:
    bot.cache.place_guild_data(SAMPLE_GUILD_DATA())
    data: discord_typings.TextChannelData = {
        "id": "12345",
        "type": 0,
        "guild_id": SAMPLE_GUILD_DATA()["id"],
        "position": 0,
        "last_message_id": None,
        "permission_overwrites": [],
        "name": "general",
        "topic": None,
        "nsfw": False,
        "parent_id": None,
        "rate_limit_per_user": 0,
    }
    channel = bot.cache.place_channel_data(data)
    assert isinstance(channel, GuildText)
    assert channel.guild.id == to_snowflake(SAMPLE_GUILD_DATA()["id"])


def test_update_guild(bot: Snake) -> None:
    guild = bot.cache.place_guild_data(SAMPLE_GUILD_DATA())
    assert guild.mfa_level == 0
    data = SAMPLE_GUILD_DATA()
    data["mfa_level"] = 1
    bot.cache.place_guild_data(data)
    assert guild.mfa_level == 1
