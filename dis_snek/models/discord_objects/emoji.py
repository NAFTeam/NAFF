from attr.converters import optional

from dis_snek.models.base_object import SnowflakeObject
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import attr
from dis_snek.mixins.serialization import DictSerializationMixin
from dis_snek.models.snowflake import to_snowflake
from dis_snek.utils.attr_utils import define, field
from dis_snek.utils.serializer import dict_filter_none

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.user import User
    from dis_snek.models.discord_objects.role import Role
    from dis_snek.models.snowflake import Snowflake_Type


@define()
class Emoji(SnowflakeObject):
    """
    Represent a basic emoji used in discord.

    :param id: The custom emoji id. Leave empty if you are using standard unicode emoji
    :param name: The custom emoji name. Or standard unicode emoji in string.
    :param animated: Whether this emoji is animated.
    """

    id: Optional["Snowflake_Type"] = attr.ib(default=None, converter=to_snowflake)  # can be None for Standard Emoji
    name: Optional[str] = attr.ib(default=None)
    animated: bool = attr.ib(default=False)

    def __str__(self) -> str:
        return f"<{'a:' if self.animated else ''}{self.name}:{self.id}>"  # <:thinksmart:623335224318754826>

    @property
    def req_format(self) -> str:
        """
        Format used for web request.
        """
        if self.id:
            return f"{self.name}:{self.id}"
        else:
            return self.name


@define()
class CustomEmoji(Emoji, DictSerializationMixin):
    """
    Represent a custom emoji in a guild with all its properties.

    :param roles: Roles allowed to use this emoji
    :param creator: User that made this emoji.
    :param require_colons: Whether this emoji must be wrapped in colons
    :param managed: Whether this emoji is managed.
    :param available: Whether this emoji can be used, may be false due to loss of Server Boosts.
    :param guild_id: The guild that this custom emoji is created in.
    """

    _client: "Snake" = field()

    roles: List["Snowflake_Type"] = attr.ib(factory=list)
    creator: Optional["User"] = attr.ib(default=None)  # TODO Dont store this.
    require_colons: bool = attr.ib(default=False)
    managed: bool = attr.ib(default=False)
    available: bool = attr.ib(default=False)
    guild_id: Optional["Snowflake_Type"] = attr.ib(default=None, converter=optional(to_snowflake))

    @classmethod
    def process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        creator_dict = data.pop("user", None)
        data["creator"] = client.cache.place_user_data(creator_dict) if creator_dict else None
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any], client: "Snake") -> "CustomEmoji":
        data = cls.process_dict(data, client)
        return cls(client=client, **cls._filter_kwargs(data, cls._get_init_keys()))

    @property
    def is_usable(self) -> bool:
        """
        Determines if this emoji is usable by the current user.
        """
        if not self.available:
            return False
        # todo: check roles
        return True

    async def modify(
        self,
        name: Optional[str] = None,
        roles: Optional[List[Union["Snowflake_Type", "Role"]]] = None,
        reason: Optional[str] = None,
    ) -> "CustomEmoji":
        """
        Modify the custom emoji information.

        :param name: The name of the emoji.
        :param roles: The roles allowed to use this emoji.
        :param reason: Attach a reason to this action, used for audit logs.

        :return: The newly modified custom emoji.
        """
        data_payload = dict_filter_none(
            dict(
                name=name,
                roles=roles,
            )
        )

        updated_data = await self._client.http.modify_guild_emoji(data_payload, self.guild_id, self.id, reason=reason)
        self.update_from_dict(updated_data)
        return self

    async def delete(self, reason: Optional[str] = None) -> None:
        """
        Deletes the custom emoji from the guild.

        :param reason: Attach a reason to this action, used for audit logs.
        """
        if not self.guild_id:
            raise ValueError("Cannot delete emoji, no guild id set.")

        await self._client.http.delete_guild_emoji(self.guild_id, self.id, reason=reason)
