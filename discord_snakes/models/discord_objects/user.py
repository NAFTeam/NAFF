from typing import Optional, Literal

from discord_snakes.models.snowflake import Snowflake
from discord_snakes.models.enums import UserFlags, PremiumTypes


class BaseUser:
    __slots__ = "id", "username", "discriminator", "avatar"

    def __init__(self, data: dict):
        self.id = data["id"]
        self.username = data["username"]
        self.discriminator = data["discriminator"]
        self.avatar = data["avatar"]  # todo convert to asset

    def __str__(self):
        return f"{self.username}#{self.discriminator}"

    @property
    def mention(self):
        return f"<@{self.id}>"


class User(BaseUser):
    __slots__ = (
        "bot",
        "system",
        "mfa_enabled",
        "locale",
        "verified",
        "email",
        "flags",
        "premium_type",
        "public_flags",
        "banner",
        "banner_color",
        "accent_color",
    )

    def __init__(self, data: dict):
        super().__init__(data)
        self.bot = data.get("bot", False)
        self.system = data.get("system", False)
        self.mfa_enabled = data.get("mfa_enabled", False)
        self.locale = (data.get("locale", None),)
        self.verified = data.get("verified", False)
        self.email = data.get("email", None)
        self.flags = UserFlags(data.get("flags", 0))
        self.premium_type = PremiumTypes(data.get("premium_type", 0))
        self.public_flags = UserFlags(data.get("public_flags", 0))
        self.banner = data.get("banner")  # todo convert to asset
        self.banner_color = data.get("banner_color")  # todo convert to color objects
        self.accent_color = data.get("accent_color")
