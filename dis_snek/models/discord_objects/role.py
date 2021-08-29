from typing import TYPE_CHECKING, Optional, Dict, Any, Union, Awaitable
from functools import partial

import attr

from dis_snek.models.snowflake import Snowflake_Type
from dis_snek.models.base_object import DiscordObject
from dis_snek.utils.attr_utils import define, field
from dis_snek.utils.cache import CacheProxy
from dis_snek.models.color import Color
from dis_snek.models.enums import Permissions

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.user import Member
    from dis_snek.models.discord_objects.guild import Guild


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

    _guild_id: "Snowflake_Type" = field()
    _bot_id: Optional["Snowflake_Type"] = field(default=None)
    integration_id: Optional["Snowflake_Type"] = field(default=None)  # todo integration object?

    @classmethod
    def process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        data.update(data.pop("tags", {}))
        return data

    @property
    def guild(self) -> Union[CacheProxy, Awaitable["Guild"], "Guild"]:
        return CacheProxy(id=self._guild_id, method=self._client.cache.get_guild)

    @property
    def bot(self) -> Optional[Union[CacheProxy, Awaitable["Member"], "Member"]]:
        if self._bot_id is None:
            return None
        return CacheProxy(id=self._bot_id, method=partial(self._client.cache.get_member, self._guild_id))

    @property
    def default(self) -> bool:
        return self.id == self._guild_id

    @property
    def bot_managed(self) -> bool:
        return self.bot_id is not None

    @property
    def integration(self) -> bool:
        return self.tags.integration_id is not None
