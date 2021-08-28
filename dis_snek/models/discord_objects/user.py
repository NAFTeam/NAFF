from typing import TYPE_CHECKING, Any, Awaitable, List, Dict, Optional, Union

import attr
from attr.converters import optional as optional_c

from dis_snek.models.discord_objects.asset import Asset
from dis_snek.models.enums import PremiumTypes, UserFlags
from dis_snek.models.snowflake import Snowflake_Type
from dis_snek.models.timestamp import Timestamp
from dis_snek.models.color import Color
from dis_snek.models.base_object import DiscordObject
from dis_snek.utils.attr_utils import define, field
from dis_snek.utils.cache import CacheProxy

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.channel import DM
    from dis_snek.models.discord_objects.guild import Guild


@define()
class BaseUser(DiscordObject):
    """Base class for User, essentially partial user discord model"""
    username: str = field(repr=True)
    discriminator: int = field(repr=True)
    avatar: "Asset" = field()

    def __str__(self):
        return f"{self.username}#{self.discriminator}"

    @classmethod
    def process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        data["avatar"] = Asset.from_path_hash(client, f"avatars/{data['id']}/{{}}", data["avatar"])
        return data

    @property
    def mention(self) -> str:
        return f"<@{self.id}>"

    @property
    def display_name(self) -> str:
        return self.username  # for duck-typing compatibility with Member

    @property
    def dm(self) -> Union[CacheProxy, Awaitable["DM"], "DM"]:
        return CacheProxy(id=self.id, method=self._client.cache.get_dm_channel)


@define()
class User(BaseUser):
    bot: bool = field(default=False)
    system: bool = field(default=False)
    public_flags: "UserFlags" = field(default=0, converter=UserFlags)
    premium_type: "PremiumTypes" = field(default=0, converter=PremiumTypes)

    banner: Optional["Asset"] = field(default=None)
    # _banner_color: Any = attr.ib(default=None)  # probably deprecated in api?
    accent_color: Optional["Color"] = field(default=None, converter=optional_c(Color))

    @classmethod
    def process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        data["banner"] = Asset.from_path_hash(client, f"banners/{data['id']}/{{}}", data["banner"])
        return data


@define()
class SnakeBotUser(User):
    verified: bool = field()
    mfa_enabled: bool = field(default=False)
    email: Optional[str] = field(default=None)  # needs special permissions?
    locale: Optional[str] = field(default=None)
    bio: Optional[str] = field(default=None)
    flags: "UserFlags" = field(default=0, converter=UserFlags)


@define()
class Member(DiscordObject):
    _client: "Snake" = attr.field(repr=False)
    guild_id: "Snowflake_Type" = attr.field()
    nickname: Optional[str] = attr.ib(default=None)
    deafened: bool = attr.ib(default=False)
    muted: bool = attr.ib(default=False)
    roles: List[Snowflake_Type] = attr.ib(factory=list)
    joined_at: Timestamp = attr.ib(converter=Timestamp.fromisoformat)
    premium_since: Optional[Timestamp] = attr.ib(default=None, converter=optional_c(Timestamp.fromisoformat))
    pending: Optional[bool] = attr.ib(default=None)
    permissions: Optional[str] = attr.ib(default=None)  # todo convert to permission object

    @classmethod
    def process_dict(cls, data, client: "Snake"):
        if "user" in data:
            user_data = data.pop("user")
            client.cache.place_user_data(user_data["id"], user_data)
            data.update(user_data)
        elif "member" in data:
            member_data = data.pop("member")
            client.cache.place_user_data(data["id"], data)
            data.update(member_data)
        return data

    @property
    def user(self) -> Union[CacheProxy, Awaitable["User"], "User"]:
        return CacheProxy(id=self.id, method=self._client.cache.get_user)

    @property
    def guild(self) -> Union[CacheProxy, Awaitable["Guild"], "Guild"]:
        return CacheProxy(id=self.guild_id, method=self._client.cache.get_guild)

    @property
    async def display_name(self) -> str:
        return self.nickname  # or self.username  # todo

    @property
    def premium(self) -> bool:
        return self.premium_since is not None
