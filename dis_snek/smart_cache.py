from typing import Dict
from typing import TYPE_CHECKING
from collections import defaultdict
from functools import partial
import attr


from dis_snek.utils.cache import TTLCache
from dis_snek.models.snowflake import Snowflake_Type

from dis_snek.models.discord_objects.user import User
from dis_snek.models.discord_objects.user import Member
from dis_snek.models.discord_objects.message import Message
from dis_snek.models.discord_objects.channel import BaseChannel
from dis_snek.models.discord_objects.guild import Guild



if TYPE_CHECKING:
    from dis_snek.client import Snake


@attr.define()
class GlobalCache:
    _client: "Snake" = attr.field()

    user_cache: TTLCache = attr.field(factory=TTLCache)  # key: user_id
    member_cache: TTLCache = attr.field(factory=TTLCache)  # key: (guild_id, user_id)
    message_cache: TTLCache = attr.field(factory=TTLCache)  # key: (channel_id, message_id)
    channel_cache: TTLCache = attr.field(factory=TTLCache)  # key: channel_id
    guid_cache: TTLCache = attr.field(factory=TTLCache)  # key: guild_id

    async def get_user(self, user_id: Snowflake_Type, request_fallback=True) -> User:
        user = self.user_cache.get(user_id)
        if request_fallback and user is None:
            data = await self._client.http.get_user(user_id)
            user = User.from_dict(data, self._client)
        return user

    async def place_user_data(self, user_id, data):
        user = self.user_cache.get(user_id)
        if user is None:
            user = User.from_dict(data, self._client)
            self.user_cache[user_id] = user
        else:
            user.update_from_dict(data)
        return user

    async def get_member(self, guild_id: Snowflake_Type, user_id: Snowflake_Type, request_fallback=True) -> Member:
        member = self.member_cache.get((guild_id, user_id))
        if request_fallback and member is None:
            data = await self._client.http.get_member(guild_id, user_id)
            member = Member.from_dict(data, self._client)
        return member

    async def place_member_data(self, guild_id, user_id, data):
        member = self.member_cache.get((guild_id, user_id))
        if member is None:
            member = Member.from_dict(data, self._client)
            self.member_cache[(guild_id, user_id)] = member
        else:
            member.update_from_dict(data)
        return member

    async def get_message(self, channel_id: Snowflake_Type, message_id: Snowflake_Type, request_fallback=True):
        message = self.message_cache.get((channel_id, message_id))
        if request_fallback and message is None:
            data = await self._client.http.get_message(channel_id, message_id)
            message = Message(data)  # todo refactor with from_dict
        return message

    # todo place message

    async def get_channel(self, channel_id: Snowflake_Type, request_fallback=True):
        channel = self.channel_cache.get(channel_id)
        if request_fallback and channel is None:
            data = await self._client.http.get_channel(channel_id)
            channel = BaseChannel.from_dict(data, self._client)
        return channel

    async def place_channel_data(self, channel_id, data):
        channel = self.channel_cache.get(channel_id)
        if channel is None:
            channel = BaseChannel.from_dict(data, self._client)
            self.channel_cache[channel_id] = channel
        else:
            channel.update_from_dict(data)
        return channel

    async def get_guild(self, guild_id: Snowflake_Type, request_fallback=True):
        guild = self.guid_cache.get(guild_id)
        if request_fallback and guild is None:
            data = await self._client.http.get_guild(guild_id)
            guild = Guild(data, self._client)  # todo refactor with from_dict
        return guild

    # todo place guild