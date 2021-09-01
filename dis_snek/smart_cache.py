from typing import TYPE_CHECKING, Any, Dict, List

import attr

from dis_snek.models.discord_objects.channel import BaseChannel
from dis_snek.models.discord_objects.guild import Guild
from dis_snek.models.discord_objects.message import Message
from dis_snek.models.discord_objects.role import Role
from dis_snek.models.discord_objects.user import Member, User
from dis_snek.models.snowflake import to_snowflake
from dis_snek.utils.cache import TTLCache

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.channel import DM
    from dis_snek.models.snowflake import Snowflake_Type


@attr.define()
class GlobalCache:
    _client: "Snake" = attr.field()

    user_cache: TTLCache = attr.field(factory=TTLCache)  # key: user_id
    member_cache: TTLCache = attr.field(factory=TTLCache)  # key: (guild_id, user_id)
    message_cache: TTLCache = attr.field(factory=TTLCache)  # key: (channel_id, message_id)
    channel_cache: TTLCache = attr.field(factory=TTLCache)  # key: channel_id
    guild_cache: TTLCache = attr.field(factory=TTLCache)  # key: guild_id
    role_cache: TTLCache = attr.field(factory=TTLCache)  # key: role_id

    dm_channels: dict = attr.field(factory=dict)

    # User cache methods

    async def get_user(self, user_id: "Snowflake_Type", request_fallback=True) -> User:
        user_id = to_snowflake(user_id)
        if user_id == self._client.user.id:
            return self._client.user

        user = self.user_cache.get(user_id)
        if request_fallback and user is None:
            data = await self._client.http.get_user(user_id)
            user = self.place_user_data(data)
        return user

    def place_user_data(self, data) -> User:
        user_id = to_snowflake(data["id"])

        if user_id == self._client.user.id:
            user = self._client.user
        else:
            user = self.user_cache.get(user_id)

        if user is None:
            user = User.from_dict(data, self._client)
            self.user_cache[user_id] = user
        else:
            user.update_from_dict(data)
        return user

    # Member cache methods

    async def get_member(self, guild_id: "Snowflake_Type", user_id: "Snowflake_Type", request_fallback=True) -> Member:
        guild_id = to_snowflake(guild_id)
        user_id = to_snowflake(user_id)
        member = self.member_cache.get((guild_id, user_id))
        if request_fallback and member is None:
            data = await self._client.http.get_member(guild_id, user_id)
            member = self.place_member_data(guild_id, data)
        return member

    def place_member_data(self, guild_id, data) -> Member:
        guild_id = to_snowflake(guild_id)
        user_id = to_snowflake(data["user"]["id"] if "user" in data else data["id"])
        member = self.member_cache.get((guild_id, user_id))
        if member is None:
            data.update({"guild_id": guild_id})
            member = Member.from_dict(data, self._client)
            self.member_cache[(guild_id, user_id)] = member
        else:
            member.update_from_dict(data)
        return member

    # Message cache methods

    async def get_message(
        self, channel_id: "Snowflake_Type", message_id: "Snowflake_Type", request_fallback=True
    ) -> Message:
        channel_id = to_snowflake(channel_id)
        message_id = to_snowflake(message_id)
        message = self.message_cache.get((channel_id, message_id))
        if request_fallback and message is None:
            data = await self._client.http.get_message(channel_id, message_id)
            message = self.place_message_data(data)
        return message

    def place_message_data(self, data) -> Message:
        channel_id = to_snowflake(data["channel_id"])
        message_id = to_snowflake(data["id"])
        message = self.message_cache.get((channel_id, message_id))
        if message is None:
            message = Message.from_dict(data, self._client)
            self.message_cache[(channel_id, message_id)] = message
        else:
            message.update_from_dict(data)
        return message

    # Channel cache methods

    async def get_channel(self, channel_id: "Snowflake_Type", request_fallback=True) -> BaseChannel:
        channel_id = to_snowflake(channel_id)
        channel = self.channel_cache.get(channel_id)
        if request_fallback and channel is None:
            data = await self._client.http.get_channel(channel_id)
            channel = self.place_channel_data(data)
        return channel

    def place_channel_data(self, data) -> BaseChannel:
        channel_id = to_snowflake(data["id"])
        channel = self.channel_cache.get(channel_id)
        if channel is None:
            channel = BaseChannel.from_dict_factory(data, self._client)
            self.channel_cache[channel_id] = channel
        else:
            channel.update_from_dict(data)
        return channel

    def place_dm_channel_id(self, user_id, channel_id):
        self.dm_channels[to_snowflake(user_id)] = to_snowflake(channel_id)

    async def get_dm_channel(self, user_id) -> "DM":
        user_id = to_snowflake(user_id)
        channel_id = self.dm_channels.get(user_id)
        if channel_id is None:
            data = await self._client.http.create_dm(user_id)
            return self.place_channel_data(data)
        else:
            return await self.get_channel(channel_id)

    # Guild cache methods

    async def get_guild(self, guild_id: "Snowflake_Type", request_fallback=True) -> Guild:
        guild_id = to_snowflake(guild_id)
        guild = self.guild_cache.get(guild_id)
        if request_fallback and guild is None:
            data = await self._client.http.get_guild(guild_id)
            guild = self.place_guild_data(data)
        return guild

    def place_guild_data(self, data) -> Guild:
        guild_id = to_snowflake(data["id"])
        guild = self.guild_cache.get(guild_id)
        if guild is None:
            guild = Guild.from_dict(data, self._client)
            self.guild_cache[guild_id] = guild
        else:
            guild.update_from_dict(data)
        return guild

    # Roles cache methods

    async def get_role(self, guild_id: "Snowflake_Type", role_id: "Snowflake_Type", request_fallback=True) -> Role:
        guild_id = to_snowflake(guild_id)
        role_id = to_snowflake(role_id)
        role = self.role_cache.get(role_id)
        if request_fallback and role is None:
            data = await self._client.http.get_roles(guild_id)
            role = self.place_role_data(guild_id, data)[role_id]
        return role

    def place_role_data(
        self, guild_id: "Snowflake_Type", data: List[Dict["Snowflake_Type", Any]]
    ) -> Dict["Snowflake_Type", Role]:
        guild_id = to_snowflake(guild_id)

        roles = {}
        for role_data in data:  # todo not update cache expiration order for roles
            role_data.update({"guild_id": guild_id})
            role_id = to_snowflake(role_data["id"])

            role = self.role_cache.get(role_id)
            if role is None:
                role = Role.from_dict(role_data, self._client)
                self.role_cache[role_id] = role
            else:
                role.update_from_dict(role_data)

            roles[role_id] = role

        return roles
