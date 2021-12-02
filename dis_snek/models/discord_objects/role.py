from functools import partial
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

import attr

from dis_snek.const import MISSING
from dis_snek.models.color import Color
from dis_snek.models.discord import DiscordObject
from dis_snek.models.enums import Permissions
from dis_snek.utils.attr_utils import define, field
from dis_snek.utils.serializer import dict_filter_missing

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.guild import Guild
    from dis_snek.models.discord_objects.user import Member
    from dis_snek.models.snowflake import Snowflake_Type


def sentinel_converter(value, sentinel=attr.NOTHING):
    if value is sentinel:
        return False
    elif value is None:
        return True
    return value


@define()
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
    guild: "Guild" = field(default=None)

    _guild_id: "Snowflake_Type" = field()
    _bot_id: Optional["Snowflake_Type"] = field(default=None)
    integration_id: Optional["Snowflake_Type"] = field(default=None)  # todo integration object?

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
    def default(self) -> bool:
        """Is this the `@everyone` role"""
        return self.id == self._guild_id

    @property
    def bot_managed(self) -> bool:
        """Is this role owned/managed by a bot"""
        return self.bot_id is not None

    @property
    def mention(self) -> str:
        """Returns a string that would mention the role"""
        return f"<@&{self.id}>"

    @property
    def integration(self) -> bool:
        """Is this role owned/managed by a integration"""
        return self.tags.integration_id is not None

    @property
    def members(self) -> list["Member"]:
        return [member for member in self.guild.members if member.has_role(self)]

    async def is_assignable(self) -> bool:
        """Can this role be assigned or removed by this bot?
        !!! note:
            This does not account for permissions, only the role hierarchy"""
        me = await self.guild.me

        if (self.default or await me.top_role.position > self.position) and not self.managed:
            return True
        return False

    async def delete(self, reason: str = None) -> None:
        """
        Delete this role

        Args:
            reason: An optional reason for this deletion
        """
        await self._client.http.delete_guild_role(self._guild_id, self.id, reason)

    async def edit(
        self,
        name: str = MISSING,
        permissions: str = MISSING,
        color: Union[int, Color] = MISSING,
        hoist: bool = MISSING,
        mentionable: bool = MISSING,
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
            dict(name=name, permissions=permissions, color=color, hoist=hoist, mentionable=mentionable)
        )

        r_data = await self._client.http.modify_guild_role(self._guild_id, self.id, payload)
        r_data["guild_id"] = self._guild_id
        return self.from_dict(r_data, self._client)
