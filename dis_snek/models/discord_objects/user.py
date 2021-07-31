from typing import List
from typing import Optional
from typing import Dict
from typing import Any
from typing import TYPE_CHECKING

from dis_snek.models.enums import PremiumTypes
from dis_snek.models.enums import UserFlags
from dis_snek.models.snowflake import Snowflake
from dis_snek.models.snowflake import Snowflake_Type
from dis_snek.models.timestamp import Timestamp

if TYPE_CHECKING:
    from dis_snek.client import Snake


class BaseUser(Snowflake):
    """Base class for User, essentially partial user discord model"""

    __slots__ = "_client", "id", "username", "discriminator", "avatar"

    id: Snowflake_Type
    username: str
    discriminator: int
    # avatar:

    def __init__(self, data: Dict[str, Any], client: Snake):
        self._client = client
        self.id = data["id"]
        self.username = data["username"]
        self.discriminator = data["discriminator"]
        self.avatar = data["avatar"]  # todo convert to asset

    def __str__(self):
        return f"{self.username}#{self.discriminator}"

    @property
    def mention(self) -> str:
        return f"<@{self.id}>"

    @property
    def display_name(self) -> str:
        return self.username


class User(BaseUser):
    __slots__ = (
        "is_bot",
        "is_system",
        "premium_type",
        "public_flags",
        # "banner",
        # "banner_color",
        # "accent_color",
    )

    is_bot: bool
    is_system: bool
    public_flags: UserFlags
    premium_type: PremiumTypes

    def __init__(self, data: Dict[str, Any], client: Snake):
        super().__init__(data, client)
        self.is_bot = data.get("bot", False)
        self.is_system = data.get("system", False)
        self.public_flags = UserFlags(data.get("public_flags", 0))
        self.premium_type = PremiumTypes(data.get("premium_type", 0))

        # self.banner = data.get("banner")  # todo convert to asset
        # self.banner_color = data.get("banner_color")  # todo convert to color objects
        # self.accent_color = data.get("accent_color")


class SnakeBotUser(User):
    __slots__ = (
        "mfa_enabled",
        "locale",
        "verified",
        "email",
        "flags",
    )
    verified: bool
    mfa_enabled: bool
    email: Optional[str]
    locale: Optional[str]
    flags: UserFlags

    def __init__(self, data: Dict[str, Any], client: Snake):
        super().__init__(data, client)
        self.verified = data.get("verified", False)
        self.mfa_enabled = data.get("mfa_enabled", False)
        self.email = data.get("email")
        self.locale = data.get("locale")
        self.flags = UserFlags(data.get("flags", 0))


class Member(User):
    __slots__ = ("nickname", "roles", "joined_at", "premium_since", "deafened", "muted", "pending", "permissions")
    nickname: str
    roles: List[Snowflake_Type]
    joined_at: Timestamp
    premium_since: Optional[Timestamp]
    deafened: bool
    muted: bool
    pending: Optional[bool]
    permissions: Optional[str]

    def __init__(self, data: Dict[str, Any], client: Snake, user_data: Optional[dict] = None):
        if user_data:
            super().__init__(user_data, client)
        else:
            super().__init__(data["user"], client)

        self.nickname = data.get("nick")
        self.roles = data["roles"]  # List of IDs
        self.joined_at = Timestamp.fromisoformat(data["joined_at"])

        if timestamp := data.get("premium_since"):
            self.premium_since = Timestamp.fromisoformat(timestamp)
        else:
            self.premium_since = None

        self.deafened = data["deaf"]
        self.muted = data["mute"]
        self.pending = data.get("pending")
        self.permissions = data.get("permissions")  # todo convert to permission object

    @property
    def display_name(self) -> str:
        return self.nickname or self.username

    @property
    def premium(self) -> bool:
        return self.premium_since is not None
