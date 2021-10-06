import asyncio
import traceback
from typing import TYPE_CHECKING, Any, Dict, List

import attr

from dis_snek.utils.serializer import no_export_meta

from dis_snek.mixins.serialization import DictSerializationMixin
from dis_snek.models.snowflake import SnowflakeObject
from dis_snek.utils.attr_utils import define, field

if TYPE_CHECKING:
    from dis_snek.client import Snake


@attr.s()
class ClientObject(DictSerializationMixin):
    _client: "Snake" = field(metadata=no_export_meta)

    def __attrs_post_init__(self):
        # This automatically populates the object with data from the cache

        if hasattr(self, "channel") and self.channel is None and self._channel_id:
            self.channel = self._client.cache.channel_cache.get(int(self._channel_id))
            if self.channel._guild_id and not self._guild_id:
                self._guild_id = self.channel._guild_id

        if hasattr(self, "guild") and self.guild is None and self._guild_id:
            self.guild = self._client.cache.guild_cache.get(int(self._guild_id))

        if hasattr(self, "author") and self.author is None and self._author_id:
            if self.guild:
                self.author = self._client.cache.member_cache.get((int(self._guild_id), int(self._author_id)))
            if not self.author:
                # unfortunately its very common for the member cache to lack the user, so we give a user object by default
                self.author = self._client.cache.user_cache.get(int(self._author_id))

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        return super()._process_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], client: "Snake"):
        data = cls._process_dict(data, client)
        return cls(client=client, **cls._filter_kwargs(data, cls._get_init_keys()))

    @classmethod
    def from_list(cls, datas: List[Dict[str, Any]], client: "Snake"):
        return [cls.from_dict(data, client) for data in datas]

    def update_from_dict(self, data):
        data = self._process_dict(data, self._client)
        for key, value in self._filter_kwargs(data, self._get_keys()).items():
            # todo improve
            setattr(self, key, value)


@attr.s()
class DiscordObject(SnowflakeObject, ClientObject):
    pass
