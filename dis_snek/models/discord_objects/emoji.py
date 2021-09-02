from attr.converters import optional

from dis_snek.models.base_object import SnowflakeObject
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import attr
from dis_snek.mixins.serialization import DictSerializationMixin
from dis_snek.models.route import Route
from dis_snek.models.snowflake import to_snowflake
from dis_snek.utils.attr_utils import define, field

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.user import User
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

    async def delete(self, reason: Optional[str] = None) -> None:
        """
        Deletes the custom emoji from the guild.
        """
        if self.guild_id:
            # TODO why is this not in HTTP package.
            await self._client.http.request(Route("DELETE", f"/guilds/{self.guild_id}/emojis/{self.id}"), reason=reason)
        raise ValueError("Cannot delete emoji, no guild_id set")
