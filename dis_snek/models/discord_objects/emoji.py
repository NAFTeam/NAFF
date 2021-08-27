from typing import Any, Dict, List, Optional

import attr

from dis_snek.models.discord_objects.user import User
from dis_snek.models.route import Route
from dis_snek.models.snowflake import Snowflake, Snowflake_Type
from dis_snek.utils.attr_utils import DictSerializationMixin


@attr.s(slots=True)
class PartialEmoji(Snowflake):
    id: Optional[Snowflake_Type] = attr.ib(default=None)  # can be None for Standard Emoji
    name: Optional[str] = attr.ib(default=None)
    animated: bool = attr.ib(default=False)

    def __str__(self) -> str:
        return f"<{'a:' if self.animated else ''}{self.name}:{self.id}>"  # <:thinksmart:623335224318754826>

    @property
    def req_format(self) -> str:
        """
        Format used for web request
        """
        if self.id:
            return f"{self.name}:{self.id}"
        else:
            return self.name

    def to_dict(self) -> dict:
        return attr.asdict(self, filter=lambda key, value: isinstance(value, bool) or value)


@attr.s(slots=True, kw_only=True)
class Emoji(PartialEmoji, DictSerializationMixin):
    _client: Any = attr.ib()
    roles: List[Snowflake] = attr.ib(factory=list)
    creator: Optional[User] = attr.ib(default=None)

    require_colons: bool = attr.ib(default=False)
    managed: bool = attr.ib(default=False)

    available: bool = attr.ib(default=False)
    guild_id: Optional[Snowflake_Type] = attr.ib(default=None)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], client: Any) -> "Emoji":
        creator_dict = data.pop("user", default=None)
        creator = User.from_dict(creator_dict, client) if creator_dict else None
        return cls(client=client, creator=creator, **cls._filter_kwargs(data))

    @property
    def is_usable(self) -> bool:
        """
        Determines if this emoji is usable by the current user
        """
        if not self.available:
            return False
        # todo: check roles
        return True

    async def delete(self, reason: Optional[str] = None) -> None:
        if self.guild_id:
            await self._client.http.request(Route("DELETE", f"/guilds/{self.guild_id}/emojis/{self.id}"), reason=reason)
        raise ValueError("Cannot delete emoji, no guild_id set")
