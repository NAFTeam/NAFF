from typing import List
from typing import Optional
from typing import TYPE_CHECKING
from typing import Any
from typing import Dict

import attr

from dis_snek.models.discord_objects.user import User
from dis_snek.models.route import Route
from dis_snek.models.snowflake import Snowflake
from dis_snek.models.snowflake import Snowflake_Type
from dis_snek.utils.attr_utils import DictSerializationMixin


@attr.s(slots=True, kw_only=True)
class Emoji(Snowflake, DictSerializationMixin):
    id: Optional[Snowflake_Type] = attr.ib(default=None)  # can be None for Standard Emoji
    _client: Any = attr.ib()

    name: Optional[str] = attr.ib(default=None)
    roles: List[Snowflake] = attr.ib(factory=list)
    creator: Optional[User] = attr.ib(default=None)

    require_colons: bool = attr.ib(default=False)
    managed: bool = attr.ib(default=False)
    animated: bool = attr.ib(default=False)
    available: bool = attr.ib(default=False)

    guild_id: Optional[Snowflake_Type] = attr.ib(default=None)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], client: Any):
        creator_dict = data.pop("user", default=None)
        creator = User.from_dict(creator_dict, client) if creator_dict else None
        return cls(client=client, creator=creator, **cls._filter_kwargs(data))

    def to_dict(self):
        data = {
            "id": self.id,
            "name": self.name,
        }
        return data

    def __str__(self):
        return f"<{'a:' if self.animated else ''}{self.name}:{self.id}>"

    @property
    def req_format(self):
        return f"{self.name}:{self.id}"

    @property
    def is_usable(self) -> bool:
        """
        Determines if this emoji is usable by the current user
        """
        if not self.available:
            return False
        # todo: check roles
        return True

    async def delete(self, reason: Optional[str] = None):
        if self.guild_id:
            await self._client.http.request(Route("DELETE", f"/guilds/{self.guild_id}/emojis/{self.id}"), reason=reason)
        raise ValueError("Cannot delete emoji, no guild_id set")
