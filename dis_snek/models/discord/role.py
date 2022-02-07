from functools import partial, total_ordering
from typing import TYPE_CHECKING, Any, Dict, Optional, Union, TypeVar

import attr

from dis_snek.client.const import MISSING, Absent
from dis_snek.client.utils.attr_utils import define, field
from dis_snek.client.utils.serializer import dict_filter_missing
from dis_snek.models.discord.color import Color
from dis_snek.models.discord.enums import Permissions
from .base import DiscordObject

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models.discord.guild import Guild
    from dis_snek.models.discord.user import Member
    from dis_snek.models.discord.snowflake import Snowflake_Type

__all__ = ["Role"]

T = TypeVar("T")


def sentinel_converter(value: Optional[bool | T], sentinel: T = attr.NOTHING) -> bool:
    if value is sentinel:
        return False
    elif value is None:
        return True
    return value


@define()
@total_ordering
class Role(DiscordObject):
    _sentinel = object()

    name: str = field(repr=True)
    color: "Color" = field(converter=Color)
    hoist: bool = field(default=False)
    position: int = field(repr=True)
    permissions: "Permissions" = field(converter=Permissions)
    managed: bool = field(default=False)
    mentionable: bool = field(default=True)
    premium_subscriber: bool = field(default=_sentinel, converter=partial(sentinel_converter, sentinel=_sentinel))

    _guild_id: "Snowflake_Type" = field()
    _bot_id: Optional["Snowflake_Type"] = field(default=None)
    _integration_id: Optional["Snowflake_Type"] = field(default=None)  # todo integration object?

    def __lt__(self: "Role", other: "Role") -> bool:
        if not isinstance(self, Role) or not isinstance(other, Role):
            return NotImplemented

        if self._guild_id != other._guild_id:
            raise RuntimeError("Unable to compare Roles from different guilds.")

        return self.position < other.position

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        data.update(data.pop("tags", {}))
        return data

    async def get_bot(self) -> Optional["Member"]:
        """
        Get the bot associated with this role if any.

        Returns:
            Member object if any

        """
        if self._bot_id is None:
            return None
        return await self._client.cache.get_member(self._guild_id, self._bot_id)

    @property
    def guild(self) -> "Guild":
        """The guild object this role is from."""
        return self._client.cache.guild_cache.get(self._guild_id)

    @property
    def default(self) -> bool:
        """Is this the `@everyone` role."""
        return self.id == self._guild_id

    @property
    def bot_managed(self) -> bool:
        """Is this role owned/managed by a bot."""
        return self._bot_id is not None

    @property
    def mention(self) -> str:
        """Returns a string that would mention the role."""
        return f"<@&{self.id}>" if self.id != self._guild_id else "@everyone"

    @property
    def integration(self) -> bool:
        """Is this role owned/managed by an integration."""
        return self._integration_id is not None

    @property
    def members(self) -> list["Member"]:
        """List of members with this role"""
        return [member for member in self.guild.members if member.has_role(self)]

    @property
    def is_assignable(self) -> bool:
        """
        Can this role be assigned or removed by this bot?

        Note:
            This does not account for permissions, only the role hierarchy

        """
        return (self.default or self.guild.me.top_role > self) and not self.managed

    async def delete(self, reason: str = None) -> None:
        """
        Delete this role.

        Args:
            reason: An optional reason for this deletion

        """
        await self._client.http.delete_guild_role(self._guild_id, self.id, reason)

    async def edit(
        self,
        name: Absent[str] = MISSING,
        permissions: Absent[str] = MISSING,
        color: Absent[Union[int, Color]] = MISSING,
        hoist: Absent[bool] = MISSING,
        mentionable: Absent[bool] = MISSING,
    ) -> "Role":
        """
        Edit this role, all arguments are optional.

        Args:
            name: name of the role
            permissions: New permissions to use
            color: The color of the role
            hoist: whether the role should be displayed separately in the sidebar
            mentionable: whether the role should be mentionable

        Returns:
            Role with updated information

        """
        if isinstance(color, Color):
            color = color.value

        payload = dict_filter_missing(
            {"name": name, "permissions": permissions, "color": color, "hoist": hoist, "mentionable": mentionable}
        )

        r_data = await self._client.http.modify_guild_role(self._guild_id, self.id, payload)
        r_data["guild_id"] = self._guild_id
        return self.from_dict(r_data, self._client)
