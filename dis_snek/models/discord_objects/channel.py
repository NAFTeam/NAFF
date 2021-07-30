from datetime import datetime
from typing import TYPE_CHECKING, Optional, List, Union

from dis_snek.models.enums import ChannelTypes as ct
from dis_snek.models.snowflake import Snowflake

if TYPE_CHECKING:
    from dis_snek.client import Snake


class Channel:
    def __init__(self, data: dict, client):
        self._client: Snake = client

        self.id: Snowflake = data["id"]
        self._type: int = data["type"]
        self.name: Optional[str] = data.get("name")
        self.topic: Optional[str] = data.get("topic")

        self.position: Optional[int] = data.get("position", 0)
        self.parent_id: Optional[Snowflake] = data.get("parent_id")
        self.permission_overwrites: list[dict] = data.get("permission_overwrites", [])
        self.slsh_permissions: Optional[str] = data.get("permissions")
        self._raw = data

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
        self.nsfw: bool = data.get("nsfw", False)
        self.slow_mode_time: int = data.get("rate_limit_per_user", 0)

        self.last_message_id: Snowflake = data.get("last_message_id")
        self.last_pin_timestamp: Optional[datetime] = (
            datetime.fromisoformat(data["last_pin_timestamp"]) if data.get("last_pin_timestamp") else None
        )
        self.default_auto_archive_duration: int = data.get("default_auto_archive_duration", 60)


class VoiceChannel(Channel):
    def __init__(self, data: dict, client):
        super().__init__(data, client)
        self.bitrate: int = data.get("bitrate")
        self.user_limit: int = data.get("user_limit")

        self.rtc_region: str = data.get("rtc_region", "auto")
        self.video_quality_mode: int = data.get("video_quality_mode", 1)


class DM(TextChannel):
    def __init__(self, data: dict, client):
        super().__init__(data, client)

        self.owner_id = data.get("owner_id")
        self.application_id: Optional[Snowflake] = data.get("application_id")
        self.recipients: List[dict] = data.get("recipients")


class GuildText(TextChannel):
    def __init__(self, data: dict, client):
        super().__init__(data, client)

        self.guild_id: Snowflake


class Thread(GuildText):
    def __init__(self, data: dict, client):
        super().__init__(data, client)
        self.message_count: int = data.get("message_count", 0)
        self.member_count: int = data.get("member_count", 0)

        thread_data = data.get("thread_metadata", {})
        self.archived = thread_data.get("archived", False)
        self.auto_archive_duration: int = thread_data.get("auto_archive_duration", self.default_auto_archive_duration)
        self.archive_timestamp: Optional[datetime] = (
            datetime.fromisoformat(thread_data.get("archive_timestamp"))
            if thread_data.get("archive_timestamp")
            else None
        )
        self.locked: bool = thread_data.get("locked", False)


class GuildNews(GuildText):
    def __init__(self, data: dict, client):
        super().__init__(data, client)


class GuildVoice(VoiceChannel):
    def __init__(self, data: dict, client):
        super().__init__(data, client)
        self.guild_id: Snowflake = data.get("guild_id", None)


class GuildStageVoice(GuildVoice):
    def __init__(self, data: dict, client):
        super().__init__(data, client)


TYPE_ALL_CHANNEL = Union[
    Channel, Category, Store, TextChannel, VoiceChannel, DM, GuildText, Thread, GuildNews, GuildVoice, GuildStageVoice
]
