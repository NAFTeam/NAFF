from typing import TYPE_CHECKING

from dis_snek.models.enums import ChannelTypes as ct
from dis_snek.models.snowflake import Snowflake

if TYPE_CHECKING:
    from dis_snek.client import Snake


class Channel:
    def __init__(self, data: dict, client):
        self._client: Snake = client

        self.id: Snowflake = data["id"]
        self._type: int = data["type"]

    @classmethod
    def create(cls, data, client):
        """
        Creates a channel object of the appropriate type
        :param data:
        :param client:
        :return:
        """
        t = data["type"]
        if t == ct.GUILD_TEXT:
            return GuildText(data, client)

        elif t == ct.GUILD_VOICE:
            return GuildVoice(data, client)

        elif t == ct.GUILD_NEWS:
            return GuildNews(data, client)

        elif t == ct.GUILD_STAGE_VOICE:
            return Thread(data, client)

        elif t == ct.GUILD_CATEGORY:
            return Category(data, client)

        elif t == ct.GUILD_STORE:
            return Store(data, client)

        elif t in [ct.GUILD_PUBLIC_THREAD, ct.GUILD_PRIVATE_THREAD, ct.GUILD_NEWS_THREAD]:
            return Thread(data, client)

        elif t in (ct.DM, ct.GROUP_DM):
            return DM(data, client)


class Category(Channel):
    def __init__(self, data: dict, client):
        super().__init__(data, client)


class Store(Channel):
    def __init__(self, data: dict, client):
        super().__init__(data, client)


class TextChannel(Channel):
    def __init__(self, data: dict, client):
        super().__init__(data, client)


class VoiceChannel(Channel):
    def __init__(self, data: dict, client):
        super().__init__(data, client)


class DM(TextChannel):
    def __init__(self, data: dict, client):
        super().__init__(data, client)


class GuildText(TextChannel):
    def __init__(self, data: dict, client):
        super().__init__(data, client)

        self.guild_id: Snowflake


class Thread(GuildText):
    def __init__(self, data: dict, client):
        super().__init__(data, client)


class GuildNews(GuildText):
    def __init__(self, data: dict, client):
        super().__init__(data, client)


class GuildVoice(VoiceChannel):
    def __init__(self, data: dict, client):
        super().__init__(data, client)


class GuildStageVoice(GuildVoice):
    def __init__(self, data: dict, client):
        super().__init__(data, client)
