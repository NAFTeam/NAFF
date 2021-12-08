import logging
from typing import TYPE_CHECKING, Any, Set, Dict, List, Optional, Union

import attr
from attr.converters import optional as optional_c

from dis_snek.const import MISSING, logger_name
from dis_snek.errors import HTTPException, TooManyChanges
from dis_snek.mixins.send import SendMixin
from dis_snek.models.color import Color
from dis_snek.models.discord import DiscordObject
from dis_snek.models.discord_objects.asset import Asset
from dis_snek.models.discord_objects.guild import Guild
from dis_snek.models.discord_objects.role import Role
from dis_snek.models.enums import Permissions, PremiumTypes, UserFlags
from dis_snek.models.snowflake import Snowflake_Type
from dis_snek.models.snowflake import to_snowflake
from dis_snek.models.timestamp import Timestamp
from dis_snek.utils.attr_utils import define, field, class_defaults, docs
from dis_snek.utils.converters import list_converter
from dis_snek.utils.converters import timestamp_converter
from dis_snek.utils.input_utils import _bytes_to_base64_data

if TYPE_CHECKING:
    from aiohttp import FormData

    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.channel import TYPE_GUILD_CHANNEL, DM

log = logging.getLogger(logger_name)


class _SendDMMixin(SendMixin):
    id: "Snowflake_Type"

    async def _send_http_request(self, message_payload: Union[dict, "FormData"]) -> dict:
        dm_id = await self._client.cache.get_dm_channel_id(self.id)
        return await self._client.http.create_message(message_payload, dm_id)


@define()
class BaseUser(DiscordObject, _SendDMMixin):
    """Base class for User, essentially partial user discord model"""

    username: str = field(repr=True, metadata=docs("The user's username, not unique across the platform"))
    discriminator: int = field(repr=True, metadata=docs("The user's 4-digit discord-tag"))
    avatar: "Asset" = field(metadata=docs("The user's default avatar"))

    def __str__(self):
        return self.tag

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        if not isinstance(data["avatar"], Asset):
            if data["avatar"]:
                data["avatar"] = Asset.from_path_hash(client, f"avatars/{data['id']}/{{}}", data["avatar"])
            else:
                data["avatar"] = Asset(client, f"{Asset.BASE}/embed/avatars/{int(data['discriminator']) % 5}.png")
        return data

    @property
    def tag(self) -> str:
        """Returns the user's Discord tag"""
        return f"{self.username}#{self.discriminator}"

    @property
    def mention(self) -> str:
        """Returns a string that would mention the user"""
        return f"<@{self.id}>"

    @property
    def display_name(self) -> str:
        """The users display name, will return nickname if one is set, otherwise will return username"""
        return self.username  # for duck-typing compatibility with Member

    async def get_dm(self) -> "DM":
        """Get the DM channel associated with this user."""
        return await self._client.cache.get_channel(self.id)  # noqa

    @property
    def mutual_guilds(self) -> List["Guild"]:
        """Get a list of mutual guilds shared between this user and the client."""

        # should user_guilds be its own property?
        return [g for g in self._client.guilds if g.id in self.user_guilds]


@define()
class User(BaseUser):
    bot: bool = field(repr=True, default=False, metadata=docs("Is this user a bot?"))
    system: bool = field(
        default=False,
        metadata=docs("whether the user is an Official Discord System user (part of the urgent message system)"),
    )
    public_flags: "UserFlags" = field(
        repr=True, default=0, converter=UserFlags, metadata=docs("The flags associated with this user")
    )
    premium_type: "PremiumTypes" = field(
        default=0, converter=PremiumTypes, metadata=docs("The type of nitro subscription on a user's account")
    )

    banner: Optional["Asset"] = field(default=None, metadata=docs("The user's banner"))
    accent_color: Optional["Color"] = field(
        default=None,
        converter=optional_c(Color),
        metadata=docs("The user's banner color"),
    )

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        data = super()._process_dict(data, client)
        if "banner" in data:
            data["banner"] = Asset.from_path_hash(client, f"banners/{data['id']}/{{}}", data["banner"])

        return data


@define()
class SnakeBotUser(User):
    verified: bool = field(repr=True, metadata={"docs": ""})
    mfa_enabled: bool = field(default=False, metadata={"docs": ""})
    email: Optional[str] = field(default=None, metadata={"docs": ""})  # needs special permissions?
    locale: Optional[str] = field(default=None, metadata={"docs": ""})
    bio: Optional[str] = field(default=None, metadata={"docs": ""})
    flags: "UserFlags" = field(default=0, converter=UserFlags, metadata={"docs": ""})

    _guild_ids: Set[str] = field(factory=set, metadata={"docs": ""})

    def _add_guilds(self, guild_ids: Set["Snowflake_Type"]):
        self._guild_ids |= guild_ids

    @property
    def guilds(self) -> List["Guild"]:
        return [self._client.cache.guild_cache.get(g_id) for g_id in self._guild_ids]

    async def edit(self, username: Optional[str] = None, avatar: Optional[bytes] = MISSING):
        """
        Edit the client's user.

        You can either change the username, or avatar, or both at once.
        `avatar` may be set to `None` to remove your bot's avatar

        ??? Hint "Example Usage:"
            ```python
            f = open("path_to_file", "rb")
            await self.user.edit(avatar=f.read())
            ```
            or
            ```python
            await self.user.edit(username="hello world")
            ```

        Args:
            username: The username you want to use
            avatar: The avatar to use, must be `bytes` (see example)

        Raises:
            TooManyChanges: If you change the profile too many times
        """
        payload = {}
        if username:
            payload["username"] = username
        if avatar:
            payload["avatar"] = _bytes_to_base64_data(avatar)  # noqa
        elif avatar is None:
            payload["avatar"] = None

        try:
            resp = await self._client.http.modify_client_user(payload)
        except HTTPException:
            raise TooManyChanges(
                "You have changed your profile too frequently, you need to wait a while before trying again."
            ) from None
        if resp:
            self._client.cache.place_user_data(resp)


@attr.s(**{k: v for k, v in class_defaults.items() if k != "on_setattr"})
class Member(DiscordObject, _SendDMMixin):
    bot: bool = field(repr=True, default=False, metadata=docs("Is this user a bot?"))
    nick: Optional[str] = field(repr=True, default=None, metadata=docs("The user's nickname in this guild'"))
    deaf: bool = field(default=False, metadata=docs("Has this user been deafened in voice channels?"))
    mute: bool = field(default=False, metadata=docs("Has this user been muted in voice channels?"))
    joined_at: "Timestamp" = field(converter=timestamp_converter, metadata=docs("When the user joined this guild"))
    premium_since: Optional["Timestamp"] = field(
        default=None,
        converter=optional_c(timestamp_converter),
        metadata=docs("When the user started boosting the guild"),
    )
    pending: Optional[bool] = field(
        default=None, metadata=docs("Whether the user has **not** passed guild's membership screening requirements")
    )
    guild_avatar: "Asset" = field(default=None, metadata=docs("The user's guild avatar"))

    _guild_id: "Snowflake_Type" = field(repr=True, metadata=docs("The ID of the guild"))
    _role_ids: List["Snowflake_Type"] = field(
        factory=list, converter=list_converter(to_snowflake), metadata=docs("The roles IDs this user has")
    )

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        if "user" in data:
            user_data = data.pop("user")
            client.cache.place_user_data(user_data)
            data["id"] = user_data["id"]
            data["bot"] = user_data.get("bot", False)
        elif "member" in data:
            member_data = data.pop("member")
            client.cache.place_user_data(data)
            member_data["id"] = data["id"]
            member_data["bot"] = data.get("bot", False)
            if "guild_id" not in member_data:
                member_data["guild_id"] = data.get("guild_id")
            data = member_data
        if data.get("avatar"):
            try:
                data["guild_avatar"] = Asset.from_path_hash(
                    client, f"guilds/{data['guild_id']}/users/{data['id']}/avatars/{{}}", data.pop("avatar", None)
                )
            except Exception as e:
                log.warning(f"[DEBUG NEEDED - REPORT THIS] Incomplete dictionary has been passed to member object: {e}")
                raise

        data["role_ids"] = data.pop("roles", [])

        return data

    def update_from_dict(self, data):
        if "guild_id" not in data:
            data["guild_id"] = self._guild_id
        data["_role_ids"] = data.pop("roles", [])
        return super().update_from_dict(data)

    @property
    def user(self) -> "User":
        """Returns this member's user object"""
        return self._client.cache.user_cache.get(self.id)

    def __str__(self):
        return self.user.tag

    def __getattr__(self, name):
        # this allows for transparent access to user attributes
        try:
            return getattr(self.user, name)
        except AttributeError:
            raise AttributeError(f"Neither `User` or `Member` have attribute {name}")

    def __setattr__(self, key, value):
        # this allows for transparent access to user attributes
        if attrib := getattr(self.__attrs_attrs__, key):
            value = attr.setters.convert(self, attrib, value)
            value = attr.setters.validate(self, attrib, value)
        super(Member, self).__setattr__(key, value)

    @property
    def nickname(self) -> str:
        """alias for nick"""
        return self.nick

    @nickname.setter
    def nickname(self, nickname):
        self.nick = nickname

    @property
    def guild(self) -> "Guild":
        return self._client.cache.guild_cache.get(self._guild_id)

    @property
    def roles(self) -> List["Role"]:
        return [r for r in self.guild.roles if r.id in self._role_ids]

    @property
    def top_role(self) -> "Role":
        return self._client.cache.role_cache.get(self._role_ids[-1])

    @property
    def display_name(self) -> str:
        """The users display name, will return nickname if one is set, otherwise will return username"""
        return self.nickname or self.username

    @property
    def display_avatar(self) -> "Asset":
        """The users displayed avatar, will return `guild_avatar` if one is set, otherwise will return user avatar"""
        return self.guild_avatar or self.user.avatar

    @property
    def premium(self) -> bool:
        """Is this member a server booster?"""
        return self.premium_since is not None

    def guild_permissions(self) -> Permissions:
        """
        Returns the permissions this member has in the guild

        Returns:
            Permission data
        """
        guild = self.guild
        if guild.is_owner(self):
            return Permissions.ALL

        role_everyone = guild.default_role  # get @everyone role
        permissions = role_everyone.permissions

        for role in self.roles:
            permissions |= role.permissions

        if Permissions.ADMINISTRATOR in permissions:
            return Permissions.ALL

        return permissions

    def has_permission(self, *permissions: Permissions) -> bool:
        """
        Checks if the member has all the given permission(s).

        ??? Hint "Example Usage:"
            Two different styles can be used to call this method.

            ```python
            await member.has_permission(Permissions.KICK_MEMBERS, Permissions.BAN_MEMBERS)
            ```
            ```python
            await member.has_permission(Permissions.KICK_MEMBERS | Permissions.BAN_MEMBERS)
            ```

            If `member` has both permissions, `True` gets returned.

        Args:
            permissions: The permission(s) to check whether the user has it.
        """

        # Get the user's permissions
        guild_permissions = self.guild_permissions()

        # Check all permissions separately
        for permission in permissions:
            if permission not in guild_permissions:
                return False
        return True

    def channel_permissions(self, channel: "TYPE_GUILD_CHANNEL") -> Permissions:
        """
        Returns the permissions this member has in a channel.

        Args:
            channel: The channel in question

        Returns:
            Permissions data
        """
        permissions = self.guild_permissions()
        if Permissions.ADMINISTRATOR in permissions:
            return Permissions.ALL

        # Find (@everyone) role overwrite and apply it.
        overwrites = channel._permission_overwrites
        if overwrite_everyone := overwrites.get(channel._guild_id):
            permissions &= ~overwrite_everyone.deny
            permissions |= overwrite_everyone.allow

        # Apply role specific overwrites.
        allow = Permissions.NONE
        deny = Permissions.NONE
        for role_id in self._role_ids:
            if overwrite_role := overwrites.get(role_id):
                allow |= overwrite_role.allow
                deny |= overwrite_role.deny

        permissions &= ~deny
        permissions |= allow

        # Apply member specific overwrite if it exist.
        if overwrite_member := overwrites.get(self.id):
            permissions &= ~overwrite_member.deny
            permissions |= overwrite_member.allow

        return permissions

    async def edit_nickname(self, new_nickname: str):
        """
        Change the user's nickname.

        Args:
            new_nickname: The new nickname to apply.
        """
        return await self._client.http.modify_guild_member(self._guild_id, self.id, nickname=new_nickname)

    async def add_role(self, role: Union[Snowflake_Type, Role], reason: str = MISSING):
        """
        Add a role to this member.

        Args:
            role: The role to add
            reason: The reason for adding this role
        """
        role = to_snowflake(role)
        return await self._client.http.add_guild_member_role(self._guild_id, self.id, role, reason=reason)

    async def remove_role(self, role: Union[Snowflake_Type, Role], reason: str = MISSING):
        """
        Remove a role from this user.

        Args:
            role: The role to remove
            reason: The reason for this removal
        """
        if isinstance(role, Role):
            role = role.id
        return await self._client.http.remove_guild_member_role(self._guild_id, self.id, role, reason=reason)

    def has_role(self, *roles: Union[Snowflake_Type, Role]) -> bool:
        """
        Checks if the user has the given role(s)

        Args:
            roles: The role(s) to check whether the user has it.
        """
        for role in roles:
            role_id = to_snowflake(role)
            if role_id not in self._role_ids:
                return False
        return True

    async def kick(self, reason: str = MISSING):
        """
        Remove a member from the guild.

        Args:
            reason: The reason for this removal
        """
        return await self._client.http.remove_guild_member(self._guild_id, self.id)

    async def ban(self, delete_message_days=0, reason: str = MISSING):
        """
        Ban a member from the guild.

        Args:
            delete_message_days: The number of days of messages to delete
            reason: The reason for this ban
        """
        return await self._client.http.create_guild_ban(self._guild_id, self.id, delete_message_days, reason=reason)
