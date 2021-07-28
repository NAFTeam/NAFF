from typing import Optional, Literal

from discord_snakes.models.snowflake import Snowflake


class BaseUser:
    __slots__ = "id", "username", "discriminator", "avatar"

    def _update(self, data: dict):
        self.id = data["id"]
        self.username = data["username"]
        self.discriminator = data["discriminator"]
        self.avatar = data["avatar"]


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

    def __init__(self, data):
        self._update(data)

    def _update(self, data: dict):
        super()._update(data)
        self.bot = data.get("bot", False)
        self.system = data.get("system", False)
        self.mfa_enabled = data.get("mfa_enabled", False)
        self.locale = (data.get("locale", None),)
        self.verified = data.get("verified", False)
        self.email = data.get("email", None)
        self.flags = data.get("flags", 0)
        self.premium_type = data.get("premium_type", 0)
        self.public_flags = data.get("public_flags", 0)
        self.banner = data.get("banner")
        self.banner_color = data.get("banner_color")
        self.accent_color = data.get("accent_color")
