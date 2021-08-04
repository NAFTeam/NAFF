from typing import Any
from typing import List
from typing import Optional

import attr
from attr.converters import optional as optional_c

from dis_snek.models.enums import PremiumTypes
from dis_snek.models.enums import UserFlags
from dis_snek.models.snowflake import Snowflake
from dis_snek.models.snowflake import Snowflake_Type
from dis_snek.models.timestamp import Timestamp
from dis_snek.utils.attr_utils import DictSerializationMixin
from dis_snek.utils.attr_utils import default_kwargs


@attr.define(str=False, **default_kwargs)
class BaseUser(Snowflake, DictSerializationMixin):
    """Base class for User, essentially partial user discord model"""

    _client: Any = attr.field(repr=False)
    username: str = attr.field()
    discriminator: int = attr.field()
    _avatar: str = attr.field()  # todo convert to asset

    def __str__(self):
        return f"{self.username}#{self.discriminator}"

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

    banner: Any = attr.ib(default=None)  # todo convert to asset
    banner_color: Any = attr.ib(default=None)  # todo convert to color objects
    accent_color: Any = attr.ib(default=None)
    bio: Any = attr.ib(default=None)


@attr.s(slots=True, kw_only=True)
class SnakeBotUser(User):
    verified: bool = attr.ib()
    mfa_enabled: bool = attr.ib(default=False)
    email: Optional[str] = attr.ib(default=None)
    locale: Optional[str] = attr.ib(default=None)
    flags: UserFlags = attr.ib(default=0, converter=UserFlags)


@attr.s(slots=True, kw_only=True)
class Member(User):
    nickname: str = attr.ib(default="")
    deafened: bool = attr.ib(default=False)
    muted: bool = attr.ib(default=False)
    roles: List[Snowflake_Type] = attr.ib(default="")
    joined_at: Timestamp = attr.ib(converter=Timestamp.fromisoformat)
    premium_since: Optional[Timestamp] = attr.ib(default=None, converter=optional_c(Timestamp.fromisoformat))
    pending: Optional[bool] = attr.ib(default=None)
    permissions: Optional[str] = attr.ib(default=None)  # todo convert to permission object

    @property
    def display_name(self) -> str:
        return self.nickname or self.username

    @property
    def premium(self) -> bool:
        return self.premium_since is not None
