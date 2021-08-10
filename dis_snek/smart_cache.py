from collections import defaultdict
from functools import partial
from typing import Dict
from typing import TYPE_CHECKING

import attr

from dis_snek.models.discord_objects.channel import BaseChannel
from dis_snek.models.discord_objects.guild import Guild
from dis_snek.models.discord_objects.message import Message
from dis_snek.models.discord_objects.role import Role
from dis_snek.models.discord_objects.user import Member
from dis_snek.models.discord_objects.user import User
from dis_snek.models.snowflake import Snowflake_Type
from dis_snek.utils.cache import TTLCache


if TYPE_CHECKING:
    from dis_snek.client import Snake


@attr.define()
class GlobalCache:
    _client: "Snake" = attr.field()

    user_cache: TTLCache = attr.field(factory=TTLCache)  # key: user_id
    member_cache: TTLCache = attr.field(factory=TTLCache)  # key: (guild_id, user_id)
    message_cache: TTLCache = attr.field(factory=TTLCache)  # key: (channel_id, message_id)
    channel_cache: TTLCache = attr.field(factory=TTLCache)  # key: channel_id
    guild_cache: TTLCache = attr.field(factory=TTLCache)  # key: guild_id
    role_cache: TTLCache = attr.field(factory=TTLCache)  # key: role_id

    async def get_user(self, user_id: Snowflake_Type, request_fallback=True) -> User:
        user = self.user_cache.get(user_id)
        if request_fallback and user is None:
            data = await self._client.http.get_user(user_id)
            user = self.place_user_data(user_id, data)
        return user

    def place_user_data(self, user_id, data):
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
            member = self.place_member_data(guild_id, user_id, data)
        return member

    def place_member_data(self, guild_id, user_id, data):
        member = self.member_cache.get((guild_id, user_id))
        if member is None:
            if "user" in data:
                member = Member.from_dict({**data, **data["user"]}, self._client)
                self.place_user_data(user_id, data["user"])
            else:
                member = Member.from_dict({**data["member"], **data}, self._client)
                member_data = data.pop("member")
                self.place_user_data(user_id, **data)
                data["member"] = member_data
            self.member_cache[(guild_id, user_id)] = member
        else:
            member.update_from_dict(data)
        return member

    async def get_message(self, channel_id: Snowflake_Type, message_id: Snowflake_Type, request_fallback=True):
        message = self.message_cache.get((channel_id, message_id))
        if request_fallback and message is None:
            data = await self._client.http.get_message(channel_id, message_id)
            message = self.place_message_data(channel_id, message_id, data)
        return message

    async def place_message_data(self, channel_id, message_id, data):
        message = self.message_cache.get((channel_id, message_id))
        if message is None:
            # TODO: Evaluate if from_dict is enough
            message = Message.from_dict(data, self._client)
            self.message_cache[(channel_id, message_id)] = message
        else:
            message.update_from_dict(data)
        return message

    async def get_channel(self, channel_id: Snowflake_Type, request_fallback=True):
        channel = self.channel_cache.get(channel_id)
        if request_fallback and channel is None:
            data = await self._client.http.get_channel(channel_id)
            channel = self.place_channel_data(channel_id, data)
        return channel

    def place_channel_data(self, channel_id, data):
        channel = self.channel_cache.get(channel_id)
        if channel is None:
            channel = BaseChannel.from_dict(data, self._client)
            self.channel_cache[channel_id] = channel
        else:
            channel.update_from_dict(data)
        return channel

    async def get_guild(self, guild_id: Snowflake_Type, request_fallback=True):
        guild = self.guild_cache.get(guild_id)
        if request_fallback and guild is None:
            data = await self._client.http.get_guild(guild_id)
            guild = self.place_guild_data(guild_id, data)
        return guild

    def place_guild_data(self, guild_id, data):
        guild = self.guild_cache.get(guild_id)
        if guild is None:
            guild = Guild.from_dict(data, self._client)
            self.guild_cache[guild_id] = guild
        else:
            guild.update_from_dict(data)
        return guild

    async def get_role(self, guild_id: Snowflake_Type, role_id: Snowflake_Type, request_fallback=True):
        role = self.role_cache.get(role_id)
        if request_fallback and role is None:
            data = await self._client.http.get_roles(guild_id)
            role = self.place_role_data(guild_id, role_id, data)
        return role

    def place_role_data(self, guild_id, role_id, data):
        role = None
        for role_data in data:
            role_data.update({"guild_id": guild_id})
            role_data_id = role_data["id"]

            cached_role = self.role_cache.get(role_data_id)
            if cached_role is None:
                cached_role = Role.from_dict(role_data, self._client)
                self.role_cache[role_data_id] = cached_role
            else:
                cached_role.update_from_dict(role_data)

            if role_data_id == role_id:
                role = cached_role

        return role
