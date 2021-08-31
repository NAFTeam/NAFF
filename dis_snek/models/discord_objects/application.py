from typing import TYPE_CHECKING, List, Optional

import attr
from dis_snek.models.base_object import DiscordObject

if TYPE_CHECKING:
    from dis_snek.models.discord_objects.team import Team
    from dis_snek.models.discord_objects.user import User
    from dis_snek.models.enums import ApplicationFlags
    from dis_snek.models.snowflake import Snowflake_Type


@attr.s(slots=True, kw_only=True)
class Application(DiscordObject):
    name: str = attr.ib()
    icon: Optional[str] = attr.ib(default=None)
    description: Optional[str] = attr.ib()
    rpc_origins: Optional[List[str]] = attr.ib(default=None)
    bot_public: bool = attr.ib(default=True)
    bot_require_code_grant: bool = attr.ib(default=False)
    terms_of_service_url: Optional[str] = attr.ib(default=None)
    privacy_policy_url: Optional[str] = attr.ib(default=None)
    owner: Optional["User"] = attr.ib(default=None)
    summary: str = attr.ib()
    verify_key: str = attr.ib()
    team: Optional["Team"] = attr.ib(default=None)
    guild_id: Optional["Snowflake_Type"] = attr.ib(default=None)
    primary_sku_id: Optional["Snowflake_Type"] = attr.ib(default=None)
    slug: Optional[str] = attr.ib(default=None)
    cover_image: Optional[str] = attr.ib(default=None)
    flags: Optional["ApplicationFlags"] = attr.ib(default=None, converter=ApplicationFlags)
