from functools import partial
from io import IOBase
from typing import TYPE_CHECKING, AsyncIterator, Awaitable, Dict, List, Optional, Union

import attr
from aiohttp import FormData
from attr.converters import optional

from dis_snek.const import MISSING
from dis_snek.models.discord import DiscordObject
from dis_snek.models.discord_objects.channel import BaseChannel, GuildText, GuildVoice, \
    GuildStageVoice, PermissionOverwrite
from dis_snek.models.discord_objects.emoji import CustomEmoji
from dis_snek.models.discord_objects.sticker import Sticker
from dis_snek.models.enums import (
    NSFWLevels,
    SystemChannelFlags,
    VerificationLevels,
    DefaultNotificationLevels,
    ExplicitContentFilterLevels,
    MFALevels,
    ChannelTypes,
)
from dis_snek.models.snowflake import to_snowflake
from dis_snek.utils.attr_utils import define
from dis_snek.utils.converters import timestamp_converter
from dis_snek.utils.proxy import CacheView, CacheProxy
from dis_snek.utils.serializer import to_image_data, dict_filter_none

if TYPE_CHECKING:
    from pathlib import Path

    from dis_snek.models.discord_objects.channel import TYPE_GUILD_CHANNEL, Thread, GuildCategory
    from dis_snek.models.discord_objects.role import Role
    from dis_snek.models.discord_objects.user import Member
    from dis_snek.models.snowflake import Snowflake_Type


@define()
class Guild(DiscordObject):
    """Guilds in Discord represent an isolated collection of users and channels, and are often referred to as "servers" in the UI."""

    unavailable: bool = attr.ib(default=False)
    """True if this guild is unavailable due to an outage."""
    name: str = attr.ib()
    """Name of guild. (2-100 characters, excluding trailing and leading whitespace)"""
    splash: Optional[str] = attr.ib(default=None)
    """Hash for splash image."""
    discovery_splash: Optional[str] = attr.ib(default=None)
    """Hash for discovery splash image. Only present for guilds with the "DISCOVERABLE" feature."""
    # owner: bool = attr.ib(default=False)  # we get this from api but it's kinda useless to store
    permissions: Optional[str] = attr.ib(default=None)  # todo convert to permissions obj
    """Total permissions for the user in the guild. (excludes overwrites)"""
    afk_channel_id: Optional["Snowflake_Type"] = attr.ib(default=None)
    """The channel id for afk."""
    afk_timeout: Optional[int] = attr.ib(default=None)
    """afk timeout in seconds."""
    widget_enabled: bool = attr.ib(default=False)
    """True if the server widget is enabled."""
    widget_channel_id: Optional["Snowflake_Type"] = attr.ib(default=None)
    """The channel id that the widget will generate an invite to, or None if set to no invite."""
    verification_level: Union[VerificationLevels, int] = attr.ib(default=VerificationLevels.NONE)
    """The verification level required for the guild."""
    default_message_notifications: Union[DefaultNotificationLevels, int] = attr.ib(
        default=DefaultNotificationLevels.ALL_MESSAGES
    )
    """The default message notifications level."""
    explicit_content_filter: Union[ExplicitContentFilterLevels, int] = attr.ib(
        default=ExplicitContentFilterLevels.DISABLED
    )
    """The explicit content filter level."""
    mfa_level: Union[MFALevels, int] = attr.ib(default=MFALevels.NONE)
    """The required MFA (Multi Factor Authentication) level for the guild."""
    system_channel_id: Optional["Snowflake_Type"] = attr.ib(default=None)
    """The id of the channel where guild notices such as welcome messages and boost events are posted."""
    system_channel_flags: Union[SystemChannelFlags, int] = attr.ib(default=SystemChannelFlags.NONE)
    """The system channel flags."""
    rules_channel_id: Optional["Snowflake_Type"] = attr.ib(default=None)
    """The id of the channel where Community guilds can display rules and/or guidelines."""
    joined_at: str = attr.ib(default=None, converter=optional(timestamp_converter))
    """When this guild was joined at."""
    large: bool = attr.ib(default=False)
    """True if this is considered a large guild."""
    member_count: int = attr.ib(default=0)
    """The total number of members in this guild."""
    voice_states: List[dict] = attr.ib(factory=list)
    """The states of members currently in voice channels. Lacks the guild_id key."""
    presences: List[dict] = attr.ib(factory=list)
    """The presences of the members in the guild, will only include non-offline members if the size is greater than large threshold."""
    max_presences: Optional[int] = attr.ib(default=None)
    """The maximum number of presences for the guild. (None is always returned, apart from the largest of guilds)"""
    max_members: Optional[int] = attr.ib(default=None)
    """The maximum number of members for the guild."""
    vanity_url_code: Optional[str] = attr.ib(default=None)
    """The vanity url code for the guild."""
    description: Optional[str] = attr.ib(default=None)
    """The description of a Community guild."""
    banner: Optional[str] = attr.ib(default=None)
    """Hash for banner image."""
    premium_tier: Optional[str] = attr.ib(default=None)
    """The premium tier level. (Server Boost level)"""
    premium_subscription_count: int = attr.ib(default=0)
    """The number of boosts this guild currently has."""
    preferred_locale: str = attr.ib()
    """The preferred locale of a Community guild. Used in server discovery and notices from Discord. Defaults to \"en-US\""""
    public_updates_channel_id: Optional["Snowflake_Type"] = attr.ib(default=None)
    """The id of the channel where admins and moderators of Community guilds receive notices from Discord."""
    max_video_channel_users: int = attr.ib(default=0)
    """The maximum amount of users in a video channel."""
    welcome_screen: Optional[dict] = attr.ib(factory=list)  # TODO 	welcome screen object.
    """The welcome screen of a Community guild, shown to new members, returned in an Invite's guild object."""
    nsfw_level: Union[NSFWLevels, int] = attr.ib(default=NSFWLevels.DEFAULT)
    """The guild NSFW level."""
    stage_instances: List[dict] = attr.ib(factory=list)  # TODO stage instance objects
    """Stage instances in the guild."""

    _owner_id: "Snowflake_Type" = attr.ib()
    _channel_ids: List["Snowflake_Type"] = attr.ib(factory=list)
    _thread_ids: List["Snowflake_Type"] = attr.ib(factory=list)
    _member_ids: List["Snowflake_Type"] = attr.ib(factory=list)
    _role_ids: List["Snowflake_Type"] = attr.ib(factory=list)
    _features: List[str] = attr.ib(factory=list)
    _icon: Optional[str] = attr.ib(default=None)  # todo merge, convert to asset
    _icon_hash: Optional[str] = attr.ib(default=None)

    # TODO Not storing these for now, get accurate data from api when needed instead.
    # _emojis: List[dict] = attr.ib(factory=list)
    # _stickers: List[Sticker] = attr.ib(factory=list)

    @classmethod
    def _process_dict(cls, data, client):
        guild_id = data["id"]

        channels_data = data.pop("channels", [])
        data["channel_ids"] = [client.cache.place_channel_data(channel_data).id for channel_data in channels_data]

        threads_data = data.pop("threads", [])
        data["thread_ids"] = [client.cache.place_channel_data(thread_data).id for thread_data in threads_data]

        members_data = data.pop("members", [])
        data["member_ids"] = [client.cache.place_member_data(guild_id, member_data).id for member_data in members_data]

        roles_data = data.pop("roles", [])
        data["role_ids"] = list(client.cache.place_role_data(guild_id, roles_data).keys())

        return data

    @property
    def channels(
        self,
    ) -> Union[CacheView, Awaitable[Dict["Snowflake_Type", "TYPE_GUILD_CHANNEL"]], AsyncIterator["TYPE_GUILD_CHANNEL"]]:
        return CacheView(ids=self._channel_ids, method=self._client.cache.get_channel)

    @property
    def threads(self) -> Union[CacheView, Awaitable[Dict["Snowflake_Type", "Thread"]], AsyncIterator["Thread"]]:
        return CacheView(ids=self._thread_ids, method=self._client.cache.get_channel)

    @property
    def members(self) -> Union[CacheView, Awaitable[Dict["Snowflake_Type", "Member"]], AsyncIterator["Member"]]:
        return CacheView(ids=self._member_ids, method=partial(self._client.cache.get_member, self.id))

    @property
    def roles(self) -> Union[CacheView, Awaitable[Dict["Snowflake_Type", "Role"]], AsyncIterator["Role"]]:
        return CacheView(ids=self._role_ids, method=partial(self._client.cache.get_role, self.id))

    @property
    def me(self) -> Union[CacheProxy, Awaitable["Member"], "Member"]:
        return CacheProxy(id=self._client.user.id, method=partial(self._client.cache.get_member, self.id))

    @property
    def owner(self) -> Union[CacheProxy, Awaitable["Member"], "Member"]:
        return CacheProxy(id=self._owner_id, method=partial(self._client.cache.get_member, self.id))

    def is_owner(self, member: "Member") -> bool:
        return self._owner_id == member.id

    # TODO What is this commented code for?
    # @property
    # def
    # if not self.member_count and "approximate_member_count" in data:
    #     self.member_count = data.get("approximate_member_count", 0)

    async def create_custom_emoji(
        self,
        name: str,
        imagefile: Union[str, "Path", "IOBase"],
        roles: Optional[List[Union["Snowflake_Type", "Role"]]] = None,
        reason: Optional[str] = MISSING,
    ) -> "CustomEmoji":
        """
        Create a new custom emoji for the guild.

        parameters:
            name: Name of the emoji
            imagefile: The emoji image. (Supports PNG, JPEG, WebP, GIF)
            roles: Roles allowed to use this emoji.
            reason: An optional reason for the audit log.

        returns:
            The new custom emoji created.
        """
        data_payload = dict_filter_none(
            dict(
                name=name,
                image=to_image_data(imagefile),
                roles=roles,
            )
        )

        emoji_data = await self._client.http.create_guild_emoji(data_payload, self.id, reason=reason)
        emoji_data["guild_id"] = self.id
        return CustomEmoji.from_dict(emoji_data, self._client)  # TODO Probably cache it

    async def get_all_custom_emojis(self) -> List[CustomEmoji]:
        """
        Gets all the custom emoji present for this guild.

        returns:
            A list of custom emoji objects.
        """
        emojis_data = await self._client.http.get_all_guild_emoji(self.id)
        return [CustomEmoji.from_dict(emoji_data, self._client) for emoji_data in emojis_data]

    async def get_custom_emoji(self, emoji_id: "Snowflake_Type") -> CustomEmoji:
        """
        Gets the custom emoji present for this guild, based on the emoji id.

        parameters:
            emoji_id: The target emoji to get data of.

        returns:
            The custom emoji object.
        """
        emoji_data = await self._client.http.get_guild_emoji(self.id, emoji_id)
        return CustomEmoji.from_dict(emoji_data, self._client)

    async def create_channel(
        self,
        channel_type: Union[ChannelTypes, int],
        name: str,
        topic: Optional[str] = MISSING,
        position: int = 0,
        permission_overwrites: Optional[Union["PermissionOverwrite", dict]] = MISSING,
        category: Union["Snowflake_Type", "GuildCategory"] = None,
        nsfw: bool = False,
        bitrate: int = 64000,
        user_limit: int = 0,
        slowmode_delay: int = 0,
        reason: Optional[str] = MISSING,
    ) -> "TYPE_GUILD_CHANNEL":
        """
        Create a guild channel, allows for explicit channel type setting.

        parameters:
            channel_type: The type of channel to create
            name: The name of the channel
            topic: The topic of the channel
            position: The position of the channel in the channel list
            permission_overwrites: Permission overwrites to apply to the channel
            category: The category this channel should be within
            nsfw: Should this channel be marked nsfw
            bitrate: The bitrate of this channel, only for voice
            user_limit: The max users that can be in this channel, only for voice
            slowmode_delay: The time users must wait between sending messages
            reason: The reason for creating this channel

        returns:
            The newly created channel.
        """
        if category:
            category = to_snowflake(category)

        channel_data = await self._client.http.create_guild_channel(
            self.id,
            name,
            channel_type,
            topic,
            position,
            permission_overwrites,
            category,
            nsfw,
            bitrate,
            user_limit,
            slowmode_delay,
            reason,
        )
        return BaseChannel.from_dict_factory(channel_data, self._client)

    async def create_text_channel(
        self,
        name: str,
        topic: Optional[str] = MISSING,
        position: int = 0,
        permission_overwrites: Optional[Union["PermissionOverwrite", dict]] = MISSING,
        category: Union["Snowflake_Type", "GuildCategory"] = None,
        nsfw: bool = False,
        slowmode_delay: int = 0,
        reason: Optional[str] = MISSING,
    ) -> "GuildText":
        """
        Create a text channel in this guild.

        parameters:
            name: The name of the channel
            topic: The topic of the channel
            position: The position of the channel in the channel list
            permission_overwrites: Permission overwrites to apply to the channel
            category: The category this channel should be within
            nsfw: Should this channel be marked nsfw
            slowmode_delay: The time users must wait between sending messages
            reason: The reason for creating this channel

        returns:
           The newly created text channel.
        """
        return await self.create_channel(
            channel_type=ChannelTypes.GUILD_TEXT,
            name=name,
            topic=topic,
            position=position,
            permission_overwrites=permission_overwrites,
            category=category,
            nsfw=nsfw,
            slowmode_delay=slowmode_delay,
            reason=reason,
        )

    async def create_voice_channel(
        self,
        name: str,
        topic: Optional[str] = MISSING,
        position: int = 0,
        permission_overwrites: Optional[Union["PermissionOverwrite", dict]] = MISSING,
        category: Union["Snowflake_Type", "GuildCategory"] = None,
        nsfw: bool = False,
        bitrate: int = 64000,
        user_limit: int = 0,
        reason: Optional[str] = MISSING,
    ) -> "GuildVoice":
        """
        Create a guild voice channel.

        parameters:
            name: The name of the channel
            topic: The topic of the channel
            position: The position of the channel in the channel list
            permission_overwrites: Permission overwrites to apply to the channel
            category: The category this channel should be within
            nsfw: Should this channel be marked nsfw
            bitrate: The bitrate of this channel, only for voice
            user_limit: The max users that can be in this channel, only for voice
            reason: The reason for creating this channel

        returns:
           The newly created voice channel.
        """
        return await self.create_channel(
            channel_type=ChannelTypes.GUILD_VOICE,
            name=name,
            topic=topic,
            position=position,
            permission_overwrites=permission_overwrites,
            category=category,
            nsfw=nsfw,
            bitrate=bitrate,
            user_limit=user_limit,
            reason=reason,
        )

    async def create_stage_channel(
        self,
        name: str,
        topic: Optional[str] = MISSING,
        position: int = 0,
        permission_overwrites: Optional[Union["PermissionOverwrite", dict]] = MISSING,
        category: Union["Snowflake_Type", "GuildCategory"] = MISSING,
        bitrate: int = 64000,
        user_limit: int = 0,
        reason: Optional[str] = MISSING,
    ) -> "GuildStageVoice":
        """
        Create a guild stage channel.

        parameters:
            name: The name of the channel
            topic: The topic of the channel
            position: The position of the channel in the channel list
            permission_overwrites: Permission overwrites to apply to the channel
            category: The category this channel should be within
            bitrate: The bitrate of this channel, only for voice
            user_limit: The max users that can be in this channel, only for voice
            reason: The reason for creating this channel

        returns:
            The newly created stage channel.
        """
        return await self.create_channel(
            channel_type=ChannelTypes.GUILD_STAGE_VOICE,
            name=name,
            topic=topic,
            position=position,
            permission_overwrites=permission_overwrites,
            category=category,
            bitrate=bitrate,
            user_limit=user_limit,
            reason=reason,
        )

    async def create_category(
        self,
        name: str,
        position: int = 0,
        permission_overwrites: Optional[Union["PermissionOverwrite", dict]] = MISSING,
        reason: Optional[str] = MISSING,
    ) -> "GuildCategory":
        """
        Create a category within this guild.

        parameters:
            name: The name of the channel
            position: The position of the channel in the channel list
            permission_overwrites: Permission overwrites to apply to the channel
            reason: The reason for creating this channel

        returns:
            The newly created category.
        """
        return await self.create_channel(
            channel_type=ChannelTypes.GUILD_CATEGORY,
            name=name,
            position=position,
            permission_overwrites=permission_overwrites,
            reason=reason,
        )

    async def create_custom_sticker(
        self,
        name: str,
        imagefile: Union[str, "Path", "IOBase"],
        description: Optional[str] = MISSING,
        tags: Optional[str] = MISSING,
        reason: Optional[str] = MISSING,
    ):
        """
        # TODO
        """
        payload = FormData()
        payload.add_field("name", name)

        # TODO Validate image type?
        if isinstance(imagefile, IOBase):
            payload.add_field("file", name)
        else:
            payload.add_field("file", open(str(imagefile)))

        if description:
            payload.add_field("description", description)

        if tags:
            payload.add_field("tags", tags)

        sticker_data = await self._client.http.create_guild_sticker(payload, self.id, reason)
        return Sticker.from_dict(sticker_data, self._client)

    async def get_all_custom_stickers(self) -> List[Sticker]:
        """
        # TODO
        """
        stickers_data = await self._client.http.list_guild_stickers(self.id)
        return Sticker.from_list(stickers_data, self._client)

    async def get_custom_sticker(self, sticker_id: "Snowflake_Type"):
        """
        # TODO
        """
        sticker_data = await self._client.http.get_guild_sticker(self.id, to_snowflake(sticker_id))
        return Sticker.from_dict(sticker_data, self._client)
