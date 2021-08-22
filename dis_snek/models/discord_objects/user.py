from typing import TYPE_CHECKING, Any, Awaitable, List, Optional, Union

import attr
from attr.converters import optional as optional_c

from dis_snek.models.discord_objects.asset import Asset
from dis_snek.models.enums import PremiumTypes, UserFlags
from dis_snek.models.snowflake import Snowflake, Snowflake_Type
from dis_snek.models.timestamp import Timestamp
from dis_snek.models.color import Color
from dis_snek.utils.attr_utils import DictSerializationMixin, default_kwargs
from dis_snek.utils.cache import CacheProxy

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.channel import DM
    from dis_snek.models.discord_objects.guild import Guild


@attr.define(str=False, **default_kwargs)
class BaseUser(Snowflake, DictSerializationMixin):
    """Base class for User, essentially partial user discord model"""

    _client: "Snake" = attr.field(repr=False)
    username: str = attr.field()
    discriminator: int = attr.field()
    _avatar: str = attr.field()

    def __str__(self):
        return f"{self.username}#{self.discriminator}"

    @property
    def avatar(self) -> "Asset":
        return Asset.from_path_hash(self._client, f"avatars/{self.id}/{{}}", self._avatar)

    @property
    def mention(self) -> str:
        return f"<@{self.id}>"

    @property
    def display_name(self) -> str:
        return self.username


@attr.s(slots=True, kw_only=True)
class User(BaseUser):
    bot: bool = attr.ib(default=False)
    system: bool = attr.ib(default=False)
    public_flags: UserFlags = attr.ib(default=0, converter=UserFlags)
    premium_type: PremiumTypes = attr.ib(default=0, converter=PremiumTypes)

    _banner: Optional[str] = attr.ib(default=None)
    # _banner_color: Any = attr.ib(default=None)  # probably deprecated in api?
    _accent_color: Optional[int] = attr.ib(default=None)

    @property
    def dm(self) -> Union[CacheProxy, Awaitable["DM"], "DM"]:
        return CacheProxy(id=self.id, method=self._client.cache.get_dm_channel)

    @property
    def banner(self) -> "Asset":
        return Asset.from_path_hash(self._client, f"banners/{self.id}/{{}}", self._banner)

    @property
    def accent_color(self) -> Optional["Color"]:
        if self._accent_color is None:
            return None
        return Color(self._accent_color)


@attr.s(slots=True, kw_only=True)
class SnakeBotUser(User):
    verified: bool = attr.ib()
    mfa_enabled: bool = attr.ib(default=False)
    email: Optional[str] = attr.ib(default=None)
    locale: Optional[str] = attr.ib(default=None)
    flags: UserFlags = attr.ib(default=0, converter=UserFlags)
    bio: str = attr.ib(default="")


@attr.s(slots=True, kw_only=True)
class Member(Snowflake, DictSerializationMixin):
    _client: "Snake" = attr.field(repr=False)
    guild_id: Snowflake = attr.field()
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
        else:
            member_data = data.pop("member")
            client.cache.place_user_data(data["id"], data)
            data.update(member_data)

        return data  # TODO Why this isn't returning the class object...?

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
