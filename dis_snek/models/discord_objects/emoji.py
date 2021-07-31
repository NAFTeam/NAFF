from typing import Optional, List, TYPE_CHECKING

from dis_snek.models.discord_objects.user import User
from dis_snek.models.route import Route
from dis_snek.models.snowflake import Snowflake, Snowflake_Type

if TYPE_CHECKING:
    from dis_snek.client import Snake


class Emoji(Snowflake):
    __slots__ = (
        "_client",
        "id",
        "name",
        "roles",
        "creator",
        "require_colons",
        "managed",
        "animated",
        "available",
        "guild_id",
    )

    def __init__(self, data: dict, client, guild_id: Optional[Snowflake_Type] = None):
        self.id = data["id"]  # this is the only data guaranteed to be given
        self._client: Snake = client

        self.name: Optional[str] = data.get("name")
        self.roles: Optional[List[Snowflake]] = data.get("roles")
        self.creator: Optional[User] = User(data.get("user")) if data.get("user") else None

        self.require_colons: bool = data.get("require_colons", False)
        self.managed: bool = data.get("managed", False)
        self.animated: bool = data.get("animated", False)
        self.available: bool = data.get("available", False)

        self.guild_id: Optional[Snowflake_Type] = None

    def to_dict(self):
        data = {
            "id": self.id,
            "name": self.name,
        }
        return data

    def __str__(self):
        return f"<{'a:' if self.animated else ''}{self.name}:{self.id}>"

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
