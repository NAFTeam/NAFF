import logging
from typing import TYPE_CHECKING, List, Dict, Any, Optional, Union

import attr

from dis_snek.const import MISSING, logger_name
from dis_snek.errors import NotFound, Forbidden
from dis_snek.models import VoiceState
from dis_snek.models.discord_objects.channel import BaseChannel
from dis_snek.models.discord_objects.guild import Guild
from dis_snek.models.discord_objects.message import Message
from dis_snek.models.discord_objects.role import Role
from dis_snek.models.discord_objects.user import Member, User
from dis_snek.models.snowflake import to_snowflake
from dis_snek.utils.attr_utils import field
from dis_snek.utils.cache import TTLCache

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.channel import DM, TYPE_ALL_CHANNEL
    from dis_snek.models.snowflake import Snowflake_Type

log = logging.getLogger(logger_name)


def create_cache(
    ttl: Optional[int] = 60, hard_limit: Optional[int] = 250, soft_limit: Optional[int] = MISSING
) -> Union[dict, TTLCache]:
    """
    Create a cache object based on the parameters passed.
    
    If `ttl` and `max_values` are set to None, the cache will just be a regular dict, with no culling.
    Args:
        ttl: The time to live of an object in the cache
        hard_limit: The hard limit of values allowed to be within the cache
        soft_limit: The amount of values allowed before objects expire due to ttl

    Returns:
        dict or TTLCache based on parameters passed
    """ ""
    if ttl is None and hard_limit is None:
        return dict()
    else:
        if not soft_limit:
            soft_limit = int(hard_limit / 4) if hard_limit else 50
        return TTLCache(hard_limit=hard_limit or float("inf"), soft_limit=soft_limit or 0, ttl=ttl or float("inf"))


@attr.define()
class GlobalCache:
    _client: "Snake" = field()

    # Non expiring discord objects cache
    user_cache: dict = field(factory=dict)  # key: user_id
    member_cache: dict = field(factory=dict)  # key: (guild_id, user_id)
    channel_cache: dict = field(factory=dict)  # key: channel_id
    guild_cache: dict = field(factory=dict)  # key: guild_id

    # Expiring discord objects cache
    message_cache: TTLCache = field(factory=TTLCache)  # key: (channel_id, message_id)
    role_cache: TTLCache = field(factory=dict)  # key: role_id
    voice_state_cache: TTLCache = field(factory=dict)  # key: user_id

    # Expiring id reference cache
    dm_channels: TTLCache = field(factory=TTLCache)  # key: user_id
    user_guilds: TTLCache = field(factory=dict)  # key: user_id; value: set[guild_id]

    def __attrs_post_init__(self):
        if not isinstance(self.message_cache, TTLCache):
            log.warning(
                "Disabling cache limits for message_cache is not recommended! This can result in very high memory usage"
            )

    async def get_user(self, user_id: "Snowflake_Type", request_fallback: bool = True) -> Optional[User]:
        """
        Get a user by their ID

        Args:
            user_id: The user's ID
            request_fallback: Should data be requested from Discord if not cached?

        Returns:
            User object if found
        """
        user_id = to_snowflake(user_id)

        user = self.user_cache.get(user_id)
        if request_fallback and user is None:
            data = await self._client.http.get_user(user_id)
            user = self.place_user_data(data)
        return user

    def place_user_data(self, data: dict) -> User:
        """
        Take json data representing a User, process it, and cache it
        Args:
            data: json representation of user

        Returns:
            The processed User data
        """
        user_id = to_snowflake(data["id"])

        user = self.user_cache.get(user_id)

        if user is None:
            user = User.from_dict(data, self._client)
            self.user_cache[user_id] = user
        else:
            user.update_from_dict(data)
        return user

    # Member cache methods

    async def get_member(
        self, guild_id: "Snowflake_Type", user_id: "Snowflake_Type", request_fallback: bool = True
    ) -> Optional[Member]:
        """
        Get a member by their guild and user IDs.

        Args:
            guild_id: The ID of the guild this user belongs to
            user_id: The ID of the user
            request_fallback: Should data be requested from Discord if not cached?

        Returns:
            Member object if found
        """
        guild_id = to_snowflake(guild_id)
        user_id = to_snowflake(user_id)
        member = self.member_cache.get((guild_id, user_id))
        if request_fallback and member is None:
            data = await self._client.http.get_member(guild_id, user_id)
            member = self.place_member_data(guild_id, data)
        return member

    def place_member_data(self, guild_id: "Snowflake_Type", data: dict) -> Member:
        """
        Take json data representing a User, process it, and cache it
        Args:
            guild_id: The ID of the guild this member belongs to
            data: json representation of the member

        Returns:
            The processed member
        """
        guild_id = to_snowflake(guild_id)
        is_user = "member" in data
        user_id = to_snowflake(data["id"] if is_user else data["user"]["id"])

        member = self.member_cache.get((guild_id, user_id))
        if member is None:
            member_extra = {"guild_id": guild_id}
            member = data["member"] if is_user else data
            member.update(member_extra)

            member = Member.from_dict(data, self._client)
            self.member_cache[(guild_id, user_id)] = member
        else:
            member.update_from_dict(data)

        self.place_user_guild(user_id, guild_id)
        guild = self.guild_cache.get(guild_id)
        if guild:
            # todo: this is slow, find a faster way
            guild._member_ids.add(user_id)  # noqa
        return member

    def place_user_guild(self, user_id: "Snowflake_Type", guild_id: "Snowflake_Type") -> None:
        """
        Add a guild to the list of guilds a user has joined.
        Args:
            user_id: The ID of the user
            guild_id: The ID of the guild to add
        """
        user_id = to_snowflake(user_id)
        guild_id = to_snowflake(guild_id)
        if user_id == self._client.user.id:
            # noinspection PyProtectedMember
            self._client.user._add_guilds({guild_id})
        else:
            guilds = self.user_guilds.get(user_id)
            if guilds:
                guilds.add(guild_id)
            else:
                guilds = {guild_id}
            self.user_guilds[user_id] = guilds

    async def is_user_in_guild(
        self, user_id: "Snowflake_Type", guild_id: "Snowflake_Type", request_fallback: bool = True
    ) -> bool:
        """
        Determine if a user is in a specified guild.
        Args:
            user_id: The ID of the user to check
            guild_id: The ID of the guild
            request_fallback: Should data be requested from Discord if not cached?
        """
        user_id = to_snowflake(user_id)
        guild_id = to_snowflake(guild_id)

        # Try to get guild members list from the cache, without sending requests
        guild = await self.get_guild(guild_id, request_fallback=False)
        if guild and (user_id in guild.members.ids):
            return True
        # If no such guild in cache or member not in guild cache, try to get member directly. May send requests
        try:
            member = await self.get_member(guild_id, user_id, request_fallback)
        except (NotFound, Forbidden):  # there is no such member in the guild (as per request)
            pass
        else:
            if member:
                return True

        return False

    async def get_user_guild_ids(
        self, user_id: "Snowflake_Type", calculation_fallback: bool = True, request_fallback: bool = True
    ) -> List["Snowflake_Type"]:
        """
        Get a list of IDs for the guilds a user has joined
        Args:
            user_id: The ID of the user
            calculation_fallback: Should we use guild caches to determine what guilds the user belongs to
            request_fallback: Should data be requested from Discord if not cached?

        Returns:
            A list of snowflakes for the guilds the client can see the user is within
        """
        user_id = to_snowflake(user_id)
        guild_ids = self.user_guilds.get(user_id)
        if not guild_ids and calculation_fallback:
            guild_ids = [
                guild_id
                for guild_id in self._client.user.guilds.ids
                if await self.is_user_in_guild(user_id, guild_id, request_fallback)
            ]
            self.user_guilds[user_id] = set(guild_ids)
        return guild_ids

    # Message cache methods

    async def get_message(
        self, channel_id: "Snowflake_Type", message_id: "Snowflake_Type", request_fallback: bool = True
    ) -> Optional[Message]:
        """
        Get a message from a channel based on their IDs
        Args:
            channel_id: The ID of the channel the message is in
            message_id: The ID of the message
            request_fallback: Should data be requested from Discord if not cached?

        Returns:
            The message if found
        """
        channel_id = to_snowflake(channel_id)
        message_id = to_snowflake(message_id)
        message = self.message_cache.get((channel_id, message_id))
        if request_fallback and message is None:
            data = await self._client.http.get_message(channel_id, message_id)
            message = self.place_message_data(data)
            if not message.guild and message.channel.guild:
                message._guild_id = message.channel.guild.id
        return message

    def place_message_data(self, data: dict) -> Message:
        """
        Take json data representing a message, process it, and cache it
        Args:
            data: json representation of the message

        Returns:
            The processed message
        """
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

    async def get_channel(
        self, channel_id: "Snowflake_Type", request_fallback: bool = True
    ) -> Optional["TYPE_ALL_CHANNEL"]:
        """
        Get a channel based on it's ID
        Args:
            channel_id: The ID of the channel
            request_fallback: Should data be requested from Discord if not cached?

        Returns:
            The channel if found
        """
        channel_id = to_snowflake(channel_id)
        channel = self.channel_cache.get(channel_id)
        if request_fallback and channel is None:
            data = await self._client.http.get_channel(channel_id)
            channel = self.place_channel_data(data)
        return channel

    def place_channel_data(self, data: dict) -> "TYPE_ALL_CHANNEL":
        """
        Take json data representing a channel, process it, and cache it
        Args:
            data: json representation of the channel

        Returns:
            The processed channel
        """
        channel_id = to_snowflake(data["id"])
        channel = self.channel_cache.get(channel_id)
        if channel is None:
            channel = BaseChannel.from_dict_factory(data, self._client)
            self.channel_cache[channel_id] = channel
            if guild := channel.guild:
                guild._channel_ids.add(channel.id)
        else:
            channel.update_from_dict(data)

        return channel

    def place_dm_channel_id(self, user_id, channel_id) -> None:
        """
        Cache that the bot is active within a DM channel.
        Args:
            user_id: The id of the user this DM channel belongs to
            channel_id: The id of the DM channel
        """
        self.dm_channels[to_snowflake(user_id)] = to_snowflake(channel_id)

    async def get_dm_channel_id(self, user_id) -> "Snowflake_Type":
        """
        Get the DM channel ID for a user
        Args:
            user_id: The ID of the user
        """
        user_id = to_snowflake(user_id)
        channel_id = self.dm_channels.get(user_id)
        if channel_id is None:
            data = await self._client.http.create_dm(user_id)
            channel = self.place_channel_data(data)
            channel_id = channel.id
        return channel_id

    async def get_dm_channel(self, user_id) -> "DM":
        """
        Get the DM channel for a user
        Args:
            user_id: The ID of the user
        """
        user_id = to_snowflake(user_id)
        channel_id = await self.get_dm_channel_id(user_id)
        channel = await self.get_channel(channel_id)
        return channel

    # Guild cache methods

    async def get_guild(self, guild_id: "Snowflake_Type", request_fallback: bool = True) -> Optional[Guild]:
        """
        Get a guild based on it's ID
        Args:
            guild_id: The ID of the guild
            request_fallback: Should data be requested from Discord if not cached?

        Returns:
            The guild if found
        """
        guild_id = to_snowflake(guild_id)
        guild = self.guild_cache.get(guild_id)
        if request_fallback and guild is None:
            data = await self._client.http.get_guild(guild_id)
            guild = self.place_guild_data(data)
        return guild

    def place_guild_data(self, data) -> Guild:
        """
        Take json data representing a guild, process it, and cache it
        Args:
            data: json representation of the guild

        Returns:
            The processed guild
        """
        guild_id = to_snowflake(data["id"])
        guild = self.guild_cache.get(guild_id)
        if guild is None:
            guild = Guild.from_dict(data, self._client)
            self.guild_cache[guild_id] = guild
        else:
            guild.update_from_dict(data)
        return guild

    # Roles cache methods

    async def get_role(
        self, guild_id: "Snowflake_Type", role_id: "Snowflake_Type", request_fallback: bool = True
    ) -> Optional[Role]:
        """
        Get a role based on the guild and its own ID
        Args:
            guild_id: The ID of the guild this role belongs to
            role_id: The ID of the role
            request_fallback: Should data be requested from Discord if not cached?
        """
        guild_id = to_snowflake(guild_id)
        role_id = to_snowflake(role_id)
        role = self.role_cache.get(role_id)
        if request_fallback and role is None:
            data = await self._client.http.get_roles(guild_id)
            try:
                role = self.place_role_data(guild_id, data)[role_id]
            except KeyError:
                return None
        return role

    def place_role_data(
        self, guild_id: "Snowflake_Type", data: List[Dict["Snowflake_Type", Any]]
    ) -> Dict["Snowflake_Type", Role]:
        """
        Take json data representing a role, process it, and cache it
        Can handle multiple roles at once
        Args:
            guild_id: The ID of the guild this role belongs to
            data: json representation of the role

        Returns:
            The processed role
        """
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

    def get_voice_state(self, user_id: "Snowflake_Type") -> Optional[VoiceState]:
        """
        Get a voice state by their guild and user IDs.

        Args:
            user_id: The ID of the user

        Returns:
            VoiceState object if found
        """
        user_id = to_snowflake(user_id)

        return self.voice_state_cache.get(user_id)

    def place_voice_state_data(self, data: dict) -> Optional[VoiceState]:
        """
        Take json data representing a VoiceState, process it, and cache it
        Args:
            data: json representation of the VoiceState

        Returns:
            The processed VoiceState object
        """

        # check if the channel_id is None. If that is the case, the user disconnected, and we can delete them from the cache
        if not data["channel_id"]:
            user_id = to_snowflake(data["user_id"])

            if user_id in self.voice_state_cache:
                self.voice_state_cache.pop(user_id)
            voice_state = None

        else:
            voice_state = VoiceState.from_dict(data, self._client)
            self.voice_state_cache[voice_state.user_id] = voice_state

        return voice_state
